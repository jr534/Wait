import asyncio
import sqlite3
from unittest import case
import fastapi
import json
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.tools import tool
from ddgs import DDGS
import requests
from langchain_community.document_loaders import PlaywrightURLLoader
from datetime import datetime, timedelta, timezone
import json
import os
from langchain.messages import AIMessageChunk, AIMessage, ToolMessage
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import traceback
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, MT5ForConditionalGeneration
import sqlite_vec
from sqlite_vec import serialize_float32
from operator import itemgetter
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, MT5ForConditionalGeneration
import numpy as np
import torch
import torch.nn as nn
from playwright.async_api import async_playwright
import uvicorn
import sys
# ======================= Config ========================
 
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


os.environ["OPENAI_API_KEY"] = "toto"  # valeur bidon, LM Studio ne vérifie pas
os.environ["OPENAI_BASE_URL"] = "http://100.93.138.113:1234/v1"
local = False  # Change to True if you want to use the local model


# ======================= /Config ========================
class SLPClassifier(nn.Module):
        def __init__(self, input_dim=1024, num_classes=5):
            super().__init__()
            self.linear = nn.Linear(input_dim, num_classes)

        def forward(self, x):
            return self.linear(x)

    
# ======================= Agent Class ========================
class agent :
    def __init__(self,local=False):
        if local:
            model="ollama:gemma4:e4b"
        else:
            model="openai:google/gemma-4-e4b"
        self.tools = [search,get_page_content,get_city_weather]
        self.agent = create_agent(model=model, tools=self.tools,system_prompt="Tu es un assistant intelligent qui aide les utilisateurs à obtenir des informations factuelles et actualisées. Tu peux effectuer des recherches sur le web et extraire le contenu de pages web pour répondre aux questions des utilisateurs. Réponds de manière concise et précise, en utilisant les outils disponibles lorsque nécessaire.")
        self.conversation_history = []
        

    async def run_agent_streaming(self,websocket):
        first_chunk = True
        textes = []
        async for chunk in self.agent.astream(
            {"messages": self.conversation_history},
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            # chunk["type"] te dit quel mode a produit ce chunk
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]
                if isinstance(token, AIMessageChunk):
                    # texte qui arrive token par token
                
                    if token.text:
                        if first_chunk:
                            print("\nL'agent répond :\n")
                            first_chunk = False
                        texte = token.text
                        textes.append(texte)
                        await websocket.send_text(json.dumps({"type": "LLM/rep/chunk", "payload": {"chunk": texte}}))

            elif chunk["type"] == "updates":
                for node_name, update in chunk["data"].items(): 
                    last_msg = update["messages"][-1]

                    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            #console.print(f"[cyan]L'agent a décidé d'appeler le tool[/cyan] {tc['name']} avec les arguments {tc['args']}")
                            match tc['name']:
                                case "search":
                                    await websocket.send_text(json.dumps({"type": "LLM/rep/tool_call", "payload": {"status": "start","name": tc['name'],"info_sentence" : f"j'appelle l'outie {tc['name']} pour trouver des info sur {tc['args'].get('query')}"}}))
                                case "get_page_content":
                                    await websocket.send_text(json.dumps({"type": "LLM/rep/tool_call", "payload": {"status": "start","name": tc['name'],"info_sentence" : f"j'appelle l'outie {tc['name']} pour récupére le conetnue de la page {tc['args'].get('url')}"}}))
                                case "get_city_weather":
                                    await websocket.send_text(json.dumps({"type": "LLM/rep/tool_call", "payload": {"status": "start","name": tc['name'],"info_sentence" : f"j'appelle l'outie {tc['name']} pour récupére la métao de la ville {tc['args'].get('city_name')}"}}))

                    if isinstance(last_msg, ToolMessage):
                        #console.print(f"[green]Le tool {last_msg.name} a fini de s'exécuter avec le résultat :[/green] {last_msg.content[:100]}...\n")
                        await websocket.send_text(json.dumps({"type": "LLM/rep/tool_call", "payload": {"status": "end","name": last_msg.name,"info_sentence" : "le tool "+last_msg.name+" a fini de s'exécuter"}}))
        self.conversation_history.append({"role": "assistant", "content": "".join(textes)})
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
    
    À utiliser obligatoirement lorsque la demande de l'utilisateur concerne :
    - Des événements récents, des actualités ou des données en temps réel.
    - Des faits précis, des statistiques, des biographies ou des détails techniques inconnus.
    - La vérification d'une information en cas de doute.
    
    Args:
        query (str): La requête de recherche textuelle. Doit être concise, 
                    composée de mots-clés pertinents (ex: "météo Nantes", 
                    "documentation FastAPI FTS5"). Éviter les phrases naturelles longues.
                    
    Returns:
        str: Un résumé textuel des résultats de recherche pertinents extraits du web,
            ou un message d'erreur si la recherche échoue.
    """
    print(f"Searching for: {query}...")
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=5)]
        return str(results).replace("href","url")

@tool
async def get_city_weather(city_name: str) -> str:
    """Get the current weather for a given city. cette outie ne prend uniuqment le nom de la ville et non le pays le format demande est : \n Paris \n pas Paris France juste uniquemnt Paris"""
    print (f"Fetching weather for {city_name}...")
    api_key = "0bc328c650091468c9a37a5b380ea3d7"  # Replace with
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric&lang=fr"
    response = requests.get(url)
    return await format_weather(response.json())

async def format_weather(data: dict) -> str:
    ville = data.get("name", "Lieu inconnu")
    pays = data.get("sys", {}).get("country", "")
    
    main = data.get("main", {})
    temp = round(main.get("temp", 0))
    ressenti = round(main.get("feels_like", 0))
    humidite = main.get("humidity")
    
    weather = data.get("weather", [{}])[0]
    description = weather.get("description", "").capitalize()
    
    vent = data.get("wind", {}).get("speed")  # m/s
    
    # Conversion du timezone offset (secondes) en heure locale
    tz_offset = data.get("timezone", 0)
    tz = timezone(timedelta(seconds=tz_offset))
    
    lever = datetime.fromtimestamp(data["sys"]["sunrise"], tz).strftime("%H:%M")
    coucher = datetime.fromtimestamp(data["sys"]["sunset"], tz).strftime("%H:%M")

    texte = (
        f" {ville}, {pays}\n"
        f" {description}, {temp}°C (ressenti {ressenti}°C)\n"
        f" Humidité : {humidite}%\n"
        f" Vent : {vent} m/s\n"
        f" Lever du soleil : {lever} | Coucher : {coucher}"
    )
    return texte
# ========================== /Agent Class ========================
# ========================== API ====================================================================
async def get_icon(user_input, k=3):
    user_embed = app.state.embeding
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
    words = query.split(" ")
    clean_query = " ".join(words[:12])  # Correction : .join() à la place de .joint()
    prompt = f"<{lang}> Formalize UI: {icon}. User query: {clean_query}"

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model_sent.generate(**inputs, max_length=32)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return text

async def predict_format(websocket):
    
    id2label ={
    0: "code",
    1: "liste",
    2: "paragraphe",
    3: "tableau",
    4: "titre"
    }

    device = "cpu"
    embedding = app.state.embeding
    result_id = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0).to(device)  # (1, 1024)

    with torch.no_grad():
        logits = app.state.model_perdict_froamt(result_id)
        probs = torch.softmax(logits, dim=-1).squeeze(0)
        pred_id = torch.argmax(probs).item()

    code = id2label[pred_id]
    await websocket.send_text(json.dumps({"type": "wait/squel", "t_squel": 10, "squel_code": code}))
    return code

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup ===
    print("Initialisation de la connexion DB et du modèle d'embedding...")
    conn = sqlite3.connect("icons_lucide.db", check_same_thread=False)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)  # sécurité, on referme après le load
    
    device = "cpu"
    model_perdict_froamt = SLPClassifier(input_dim=1024, num_classes=5).to(device)
    model_perdict_froamt.load_state_dict(torch.load("slp_bgem3_best.pt", map_location=device))
    model_perdict_froamt.eval()

    model = SentenceTransformer("BAAI/bge-m3")
     repo_id = "prozart/Wait"
    app.state.tokenizer = AutoTokenizer.from_pretrained(repo_id)
    app.state.model_sent = MT5ForConditionalGeneration.from_pretrained(repo_id)
    # On attache tout à app.state pour y accéder ailleurs
    app.state.db_conn = conn
    app.state.model = model
    app.state.model_perdict_froamt= model_perdict_froamt
    app.state.embeding = None
    app.state.playwright = await async_playwright().start()
    app.state.browser = await app.state.playwright.chromium.launch(headless=True)
    print("Initialisation terminée.")

    yield  

    print("Fermeture des connexion...")
    conn.close()
    await app.state.browser.close()
    await app.state.playwright.stop()

app = FastAPI(lifespan=lifespan)
assistant = agent(local=local)
templates = Jinja2Templates(directory="templates")



@app.get("/")
def afficher_admin():
    main_page = open("frontend/index.html", "r", encoding="utf-8").read()
    return HTMLResponse(content=main_page, status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: fastapi.WebSocket):
    print("Nouvaux Wait USER connecté")
    try:
        await websocket.accept()
        while True:
            json_data = await websocket.receive_json()
            if json_data.get("type") == "user/ask":
                user_input = json_data.get("payload", {}).get("request", "")
                print(f"Nouvaux Wait USER demande reçu : {user_input}")
                if user_input.lower() == "":
                    await websocket.send_text(json.dumps({"type": "user/ask/error", "message": "Empty user input"}))
                    continue
                else:
                    await websocket.send_text(json.dumps({"type": "user/ask/ack"}))
                    app.state.embeding= app.state.model.encode(user_input, normalize_embeddings=True)
                    assistant.conversation_history.append({"role": "user", "content": user_input})
                    _,icons=await asyncio.gather(predict_format(websocket),get_icon(user_input))
                    for i, icon in enumerate(icons):
                        titel, svg_code, distant = icon
                        match (i) :
                            case 0:
                                #(lang, icon, query, tokenizer, model_sent):
                                phrase = await gen_sentence("fr",titel,user_input,app.state.tokenizer, app.state.model_sent)
                                await websocket.send_text(json.dumps({"type": "wait", "payload":{"t_icon1": "0","phrase_icon1": phrase, "svg_icon": svg_code}}))
                                print("icon1")
                            case 1:
                                phrase = await gen_sentence("fr",titel,user_input,app.state.tokenizer, app.state.model_sent)
                                await websocket.send_text(json.dumps({"type": "wait", "payload":{"t_icon2": "6","phrase_icon2": phrase, "svg_icon": svg_code}}))
                            case 2:
                                phrase = await gen_sentence("fr",titel,user_input,app.state.tokenizer, app.state.model_sent)
                                await websocket.send_text(json.dumps({"type": "wait", "payload":{"t_icon3": "13","phrase_icon3": phrase, "svg_icon": svg_code}}))
                    await assistant.run_agent_streaming(websocket)
    
                    
                   
                    

    except fastapi.WebSocketDisconnect:
        print("Wait USER déconnecté")
    except Exception as e:
        print(f"Erreur lors de la gestion du WebSocket : {e}")
        traceback.print_exc()
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":

    uvicorn.run(
        "Backend_Wait:app",
        host="0.0.0.0",
        port=80,
        reload=False
    )

