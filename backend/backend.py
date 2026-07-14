import os
import sys
import asyncio
import json
import sqlite3
import traceback
import requests
import random
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from operator import itemgetter

import uvicorn
import fastapi
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import numpy as np
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, MT5ForConditionalGeneration
import sqlite_vec
from sqlite_vec import serialize_float32
from playwright.async_api import async_playwright

from langchain.agents import create_agent
from langchain.tools import tool
from langchain.messages import AIMessageChunk, AIMessage, ToolMessage
from ddgs import DDGS

# ======================= OS Policy & Env Configuration ========================

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load environment variables (supports .env fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "lm-studio")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
LOCAL_AGENT_MODEL = os.getenv("LOCAL_AGENT_MODEL", "openai:google/gemma-4-e4b")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL

# Paths configuration relative to the script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "icons_lucide.db")
SLP_PATH = os.path.join(BASE_DIR, "slp_bgem3_best.pt")
LABEL_MAP_PATH = os.path.join(BASE_DIR, "label_map.json")
MT5_MODEL_PATH = os.path.join(BASE_DIR, "mt5_fakcogni_model")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "static")

# ======================= SLP Classifier Setup (Module 3) ========================

class SLPClassifier(nn.Module):
    def __init__(self, input_dim=1024, num_classes=5):
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        return self.linear(x)

# ======================= LangChain Agent Class ========================

class AgentOrchestrator:
    def __init__(self, model_name=LOCAL_AGENT_MODEL):
        self.tools = [search, get_page_content, get_city_weather]
        self.agent = create_agent(
            model=model_name,
            tools=self.tools,
            system_prompt=(
                "Tu es un assistant intelligent qui aide les utilisateurs à obtenir des informations "
                "factuelles et actualisées. Tu peux effectuer des recherches sur le web et extraire le "
                "contenu de pages web pour répondre aux questions des utilisateurs. Réponds de manière "
                "concise et précise, en utilisant les outils disponibles lorsque nécessaire."
            )
        )
        self.conversation_history = []

    async def run_agent_streaming(self, websocket):
        first_chunk = True
        textes = []
        async for chunk in self.agent.astream(
            {"messages": self.conversation_history},
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]
                if isinstance(token, AIMessageChunk):
                    if token.text:
                        if first_chunk:
                            print("\nL'agent répond :\n")
                            first_chunk = False
                        texte = token.text
                        textes.append(texte)
                        await websocket.send_text(json.dumps({
                            "type": "LLM/rep/chunk", 
                            "payload": {"chunk": texte}
                        }))

            elif chunk["type"] == "updates":
                for node_name, update in chunk["data"].items(): 
                    last_msg = update["messages"][-1]

                    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            desc = ""
                            match tc['name']:
                                case "search":
                                    desc = f"j'appelle l'outil {tc['name']} pour trouver des infos sur {tc['args'].get('query')}"
                                case "get_page_content":
                                    desc = f"j'appelle l'outil {tc['name']} pour récupérer le contenu de la page {tc['args'].get('url')}"
                                case "get_city_weather":
                                    desc = f"j'appelle l'outil {tc['name']} pour récupérer la météo de la ville {tc['args'].get('city_name')}"
                            
                            await websocket.send_text(json.dumps({
                                "type": "LLM/rep/tool_call",
                                "payload": {
                                    "status": "start",
                                    "name": tc['name'],
                                    "info_sentence": desc
                                }
                            }))

                    if isinstance(last_msg, ToolMessage):
                        await websocket.send_text(json.dumps({
                            "type": "LLM/rep/tool_call",
                            "payload": {
                                "status": "end",
                                "name": last_msg.name,
                                "info_sentence": f"l'outil {last_msg.name} a fini de s'exécuter"
                            }
                        }))
                        
        self.conversation_history.append({"role": "assistant", "content": "".join(textes)})

# ======================= LangChain Tools ========================

@tool
async def get_page_content(url: str) -> str:
    """
    Fetch the content of a web page given its URL.
    
    Args:
        url (str): The URL of the web page to fetch.
        
    Returns:
        str: The content of the web page, or an error message if the fetch fails.
    """
    browser = app.state.browser
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        content = await page.locator("body").inner_text()
        return content
    except Exception as e:
        return f"Erreur lors du chargement de la page : {str(e)}"
    finally:
        await page.close()

@tool
async def search(query: str) -> str:
    """
    Exécute une recherche sur le web pour obtenir des informations factuelles et actualisées.
    
    Args:
        query (str): La requête de recherche textuelle. Doit être concise, 
                    composée de mots-clés pertinents. Éviter les phrases naturelles longues.
                    
    Returns:
        str: Un résumé textuel des résultats de recherche pertinents extraits du web.
    """
    print(f"Searching for: {query}...")
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=5)]
        return str(results).replace("href", "url")

@tool
async def get_city_weather(city_name: str) -> str:
    """
    Get the current weather for a given city.
    
    Args:
        city_name (str): The name of the city only (e.g. "Paris", not "Paris France").
    """
    print(f"Fetching weather for {city_name}...")
    api_key = "0bc328c650091468c9a37a5b380ea3d7"  # OpenWeather API Key
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric&lang=fr"
    response = requests.get(url)
    return await format_weather(response.json())

async def format_weather(data: dict) -> str:
    if data.get("cod") != 200:
        return f"Erreur météo: {data.get('message', 'Impossible de récupérer la météo')}"
    
    ville = data.get("name", "Lieu inconnu")
    pays = data.get("sys", {}).get("country", "")
    main = data.get("main", {})
    temp = round(main.get("temp", 0))
    ressenti = round(main.get("feels_like", 0))
    humidite = main.get("humidity")
    weather = data.get("weather", [{}])[0]
    description = weather.get("description", "").capitalize()
    vent = data.get("wind", {}).get("speed")
    
    tz_offset = data.get("timezone", 0)
    tz = timezone(timedelta(seconds=tz_offset))
    lever = datetime.fromtimestamp(data["sys"]["sunrise"], tz).strftime("%H:%M")
    coucher = datetime.fromtimestamp(data["sys"]["sunset"], tz).strftime("%H:%M")

    return (
        f"Météo à {ville}, {pays}:\n"
        f"- {description}, {temp}°C (ressenti {ressenti}°C)\n"
        f"- Humidité : {humidite}%\n"
        f"- Vent : {vent} m/s\n"
        f"- Lever du soleil : {lever} | Coucher : {coucher}"
    )

# ========================== API CORE FUNCTIONALITIES ==========================

async def get_icon(user_input, k=3):
    """Module 1 — Semantic Icon Similarity matching"""
    user_embed = app.state.embedding
    user_embed_serialized = serialize_float32(user_embed.tolist())

    cursor = app.state.db_conn.cursor()
    cursor.execute(
        """SELECT
            i.title,
            i.svg_code,
            v.distance
        FROM (
            SELECT rowid, distance
            FROM icons_vec
            WHERE embedding MATCH ?
              AND k = ?
        ) v
        JOIN icons i ON i.id = v.rowid
        ORDER BY v.distance;""",
        (user_embed_serialized, k),
    )

    resultats = cursor.fetchall()
    resultats.sort(key=itemgetter(2), reverse=True)
    return resultats

async def gen_sentence(lang, icon, query, tokenizer, model_sent):
    """Module 2 — mT5 Mind Phrase Generator (with mock fallback if model is missing)"""
    if tokenizer is None or model_sent is None:
        # Graceful fallback mock sentences contextualizing the action
        fallbacks = {
            "fr": [
                f"Analyse de la demande utilisateur à travers l'élément visuel {icon}.",
                f"Je me concentre sur la structuration des informations relatives à {icon}.",
                f"Recherche et indexation de données associées au contexte de {icon}.",
                f"Formalisation du processus de génération en rapport avec {icon}."
            ],
            "en": [
                f"Analyzing user query context through the visual metaphor of {icon}.",
                f"Focusing on structuring the information related to {icon}.",
                f"Searching and indexing data associated with the context of {icon}.",
                f"Formatting the reasoning process in relation to {icon}."
            ]
        }
        phrases = fallbacks.get(lang, fallbacks["fr"])
        return random.choice(phrases)

    # Clean query down to first 12 words to avoid translation overhead
    words = query.split(" ")
    clean_query = " ".join(words[:12])
    prompt = f"<{lang}> Formalize UI: {icon}. User query: {clean_query}"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model_sent.generate(**inputs, max_length=32)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return text

async def predict_format(websocket):
    """Module 3 — Mind Skeleton Format Prediction"""
    with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
        id2label = json.load(f)
        id2label = {int(k): v for k, v in id2label.items()}

    device = "cpu"
    embedding = app.state.embedding
    result_id = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = app.state.model_predict_format(result_id)
        probs = torch.softmax(logits, dim=-1).squeeze(0)
        pred_id = torch.argmax(probs).item()

    code = id2label[pred_id]
    # Send layout design pattern prediction to frontend
    await websocket.send_text(json.dumps({
        "type": "wait/squel", 
        "t_squel": 10, 
        "squel_code": code
    }))
    return code

# ========================== APP LIFECYCLE MANAGEMENT ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Setup
    print("Initialisation des bases de données et des modèles...")
    
    # 1. Database connection loading SQLite-vec
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    app.state.db_conn = conn
    
    # 2. BGE-M3 Embedder Loading
    app.state.embedding_model = SentenceTransformer("BAAI/bge-m3")
    app.state.embedding = None
    
    # 3. Format Classifier Loading
    device = "cpu"
    num_classes = 5
    model_predict_format = SLPClassifier(input_dim=1024, num_classes=num_classes).to(device)
    model_predict_format.load_state_dict(torch.load(SLP_PATH, map_location=device))
    model_predict_format.eval()
    app.state.model_predict_format = model_predict_format

    # 4. mT5 Fine-Tuned Model Loader with Fallback
    if os.path.exists(MT5_MODEL_PATH):
        try:
            print(f"Chargement du modèle mT5 fine-tuné depuis {MT5_MODEL_PATH}...")
            app.state.tokenizer = AutoTokenizer.from_pretrained(MT5_MODEL_PATH)
            app.state.model_sent = MT5ForConditionalGeneration.from_pretrained(MT5_MODEL_PATH)
            print("Modèle mT5 chargé avec succès.")
        except Exception as e:
            print(f"Erreur de chargement de mT5: {e}. Activation du fallback.")
            app.state.tokenizer = None
            app.state.model_sent = None
    else:
        print(f"Dossier du modèle mT5 non trouvé à '{MT5_MODEL_PATH}'. Activation du fallback.")
        app.state.tokenizer = None
        app.state.model_sent = None

    # 5. Playwright Browser setup
    app.state.playwright = await async_playwright().start()
    app.state.browser = await app.state.playwright.chromium.launch(headless=True)
    print("Initialisation terminée avec succès.")

    yield  

    # Shutdown Setup
    print("Fermeture des ressources...")
    conn.close()
    await app.state.browser.close()
    await app.state.playwright.stop()

# ========================== APP ROUTING & SOCKETS ==========================

app = FastAPI(lifespan=lifespan)
assistant = AgentOrchestrator()

@app.websocket("/ws")
async def websocket_endpoint(websocket: fastapi.WebSocket):
    print("Nouveau client WAIT connecté au WebSocket")
    try:
        await websocket.accept()
        while True:
            json_data = await websocket.receive_json()
            if json_data.get("type") == "user/ask":
                user_input = json_data.get("payload", {}).get("request", "")
                print(f"Demande reçue : {user_input}")
                
                if user_input.strip() == "":
                    await websocket.send_text(json.dumps({
                        "type": "user/ask/error", 
                        "message": "Empty user input"
                    }))
                    continue
                
                await websocket.send_text(json.dumps({"type": "user/ask/ack"}))
                
                # Compute query embedding
                app.state.embedding = app.state.embedding_model.encode(
                    user_input, 
                    normalize_embeddings=True
                )
                assistant.conversation_history.append({"role": "user", "content": user_input})
                
                # Parallel computation of format prediction & icon similarity retrieval
                _, icons = await asyncio.gather(
                    predict_format(websocket),
                    get_icon(user_input)
                )
                
                # Send the matched icons & custom reasoning text chunks progressively
                for i, icon in enumerate(icons):
                    title, svg_code, distance = icon
                    phrase = await gen_sentence(
                        "fr", 
                        title, 
                        user_input,
                        app.state.tokenizer, 
                        app.state.model_sent
                    )
                    
                    delay_mapping = {0: "0", 1: "6", 2: "13"}
                    icon_key = f"icon{i+1}"
                    
                    payload = {
                        f"t_{icon_key}": delay_mapping[i],
                        f"phrase_{icon_key}": phrase,
                        "svg_icon": svg_code
                    }
                    
                    await websocket.send_text(json.dumps({
                        "type": "wait", 
                        "payload": payload
                    }))
                
                # Run the LangChain agent and stream its response chunks
                await assistant.run_agent_streaming(websocket)

    except fastapi.WebSocketDisconnect:
        print("Client WAIT déconnecté")
    except Exception as e:
        print(f"Erreur lors de la gestion du WebSocket : {e}")
        traceback.print_exc()

# Mount frontend files at the root
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    print(f"Dossier frontend statique introuvable à : {STATIC_DIR}")

if __name__ == "__main__":
    # Runs local server on port 8000 by default (easier to manage and standard for local tests)
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend:app", host="0.0.0.0", port=port, reload=False)
