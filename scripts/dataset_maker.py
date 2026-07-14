

import json
import sqlite3
import sqlite_vec
from sqlite_vec import serialize_float32
from sentence_transformers import SentenceTransformer
from operator import itemgetter
from google import genai
from tqdm import tqdm
import time

results =[]
model = SentenceTransformer("BAAI/bge-m3")
conn = sqlite3.connect("icons_lucide.db", check_same_thread=False)
conn.enable_load_extension(True)
sqlite_vec.load(conn)

target_dataset = "fake_cognition_integer_icon_large.jsonl"
source_dataset = "2023-04-12_oasst_prompts.messages.jsonl"
fr_num = 0
eng_num = 0
esp_num = 0
total_prompt = 0
old_len_result = 0
prompts = []
total_num = 0
nb_prompts = 3000
client = genai.Client(api_key="AIzaSyDkmu0me7dkRh5SEPMGaFIwO6PPsFlWAoM")
pbar = tqdm(total=nb_prompts, desc="Génération", unit="liens")

# {"message_id": "6ab24d72-0181-4594-a9cd-deaf170242fb", "parent_id": null, "user_id": "c3fe8c76-fc30-4fa7-b7f8-c492f5967d18", "created_date": "2023-02-05T14:23:50.983374+00:00", "text": "Can you write a short introduction about the relevance of the term \"monopsony\" in economics? Please use examples related to potential monopsonies in the labour market and cite relevant research.", "role": "prompter", "lang": "en", "review_count": 3, "review_result": true, "deleted": false, "rank": null, "synthetic": false, "model_name": null, "emojis": {"+1": 10, "_skip_reply": 1, "_skip_ranking": 4}, "labels": {"spam": {"value": 0.0, "count": 3}, "lang_mismatch": {"value": 0.0, "count": 3}, "pii": {"value": 0.0, "count": 3}, "not_appropriate": {"value": 0.0, "count": 3}, "hate_speech": {"value": 0.0, "count": 3}, "sexual_content": {"value": 0.0, "count": 3}, "quality": {"value": 0.9166666666666666, "count": 3}, "toxicity": {"value": 0.16666666666666666, "count": 3}, "humor": {"value": 0.3333333333333333, "count": 3}, "creativity": {"value": 0.6666666666666666, "count": 3}, "violence": {"value": 0.0, "count": 3}}, "events": null, "detoxify": {"toxicity": 0.00044308538781479, "severe_toxicity": 3.252684837207198e-05, "obscene": 0.00023475120542570949, "identity_attack": 0.0001416115992469713, "insult": 0.00039489680784754455, "threat": 4.075629112776369e-05, "sexual_explicit": 2.712695459194947e-05}, "message_tree_id": "6ab24d72-0181-4594-a9cd-deaf170242fb", "tree_state": "ready_for_export"}
def call_llm(prompt, max_retries=10):
    attempt = 0
    while attempt < max_retries:
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config={
                    "system_instruction": """You are a dataset generator for AI assistant UI status messages.

TASK:
Convert the user request and a given icon identifier into a short internal status sentence showing what the assistant is currently doing, contextually incorporating the meaning or imagery of the icon.

INPUT FORMAT:
The model will receive input in this format:
User:[First 12 words of user request] icone: [icon-name]

GOAL:
Produce a natural, simple UI progress sentence that feels like an assistant working on the request, subtly blending the user's goal with the context, metaphor, or visual theme of the icon.

RULES:
- Output ONLY one sentence
- Do NOT answer the request
- Do NOT give solutions or explanations
- MUST describe an internal action
- First person ("Je ...", "I ...", language-dependent)
- MUST match the language of the user input
- 8 to 15 words maximum (slightly extended to allow icon integration)
- No technical terms
- No reasoning explanation
- No metadata, no system language
- Contextual Icon Integration: Seamlessly merge the icon's theme (e.g., "chest-peace" -> strategy/chess/peace, "clock" -> time) into the action sentence without explicitly saying "the icon is".

ALLOWED ACTION PATTERNS (use naturally):
- "Je me concentre sur ..." / "I focus on ..."
- "Je recherche des informations sur ..." / "I look for information about ..."
- "J'analyse ..." / "I analyze ..."
- "Je consulte ..." / "I consult ..."
- "Je vérifie ..." / "I verify ..."
- "Je reviens sur ..." / "I review ..."
- "Je mets à jour ..." / "I update ..."

STYLE:
- Simple, human-readable
- Feels like an assistant actively working
- Creative but professional integration of the icon context

EXAMPLES:

User: Je cherche la manier de dresser mon chien icone: chest-peace
Output: Je cherche à dresser votre chien avec la précision stratégique d'un pion d'échecs

User: How do I sort emails from oldest to newest? icone: clock
Output: I focus on finding information about sorting your emails chronologically through time

User: Comment trier mes mails du plus vieux au plus récent icone: shield
Output: Je me concentre en toute sécurité sur la méthode pour trier vos e-mails par date

User: Explain quantum physics simply icone: lightbulb
Output: I search for a brilliant and simple way to explain quantum physics to you

User: Reviens sur les étapes de mon projet icone: map
Output: Je consulte la feuille de route pour faire le point sur les étapes de votre projet

User: Update my CV icone: rocket
Output: I update your CV information to propel your professional profile forward
"""
                }
            )
            return response.text

        except genai.errors.ServerError as e:
            # 503 / 500 : service temporairement indisponible côté Google
            attempt += 1
            print(f"[call_llm] ServerError ({e}), tentative {attempt}/{max_retries}, pause 5s...")
            time.sleep(5)

        except genai.errors.ClientError as e:
            if getattr(e, "code", None) == 429:
                attempt += 1
                print(f"[call_llm] Rate limit (429), tentative {attempt}/{max_retries}, pause 15s...")
                time.sleep(15)
            else:
                raise

    raise RuntimeError(f"call_llm a échoué après {max_retries} tentatives sur le prompt : {prompt[:50]}...")

def gen_data (item):
    prompt = item['text']
    enmd_prompt = model.encode(prompt)
    query_vector = serialize_float32(enmd_prompt)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT
            i.title,
            v.distance
        FROM (
            SELECT
                rowid,
                distance
            FROM icons_vec
            WHERE embedding MATCH ?
                AND k = 3
        ) v
        JOIN icons i
            ON i.id = v.rowid
        ORDER BY v.distance;""",
        (query_vector,),
    )

    icons = cursor.fetchall()
    # Tri selon vos critères initiaux
    icons.sort(key=itemgetter(1), reverse=True)

    for icon in icons:
        #print(f"Prompt: {prompt} => Icon: {icon[0]}, Distance: {icon[1]}")
        clean_prompt = f"User:{" ".join(prompt.split(" ")[:12])} icone: {icon[0]} " # Limite à 12 mots
        result = {"lang": item.get("lang"),"icon": icon[0],"input" : clean_prompt,"output": call_llm(clean_prompt)}
        results.append(result)


with open(source_dataset, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                total_num = line_num +1
                #print (line_num +1)
                
                item = json.loads(line)
                if total_prompt >= nb_prompts/3 :
                     break
                if item.get("lang")== "fr" and fr_num <  nb_prompts/3 * 0.5:
                    fr_num += 1
                    total_prompt +=1
                    pbar.update(3)
                    gen_data(item)
                if item.get("lang")== "en" and eng_num <  nb_prompts/3 * 0.5:
                    eng_num += 1
                    total_prompt +=1
                    pbar.update(3)
                    gen_data(item)
               
                if len(results) > old_len_result + 9:
                    for new_result in results[old_len_result:]:
                        with open(target_dataset, "a", encoding="utf-8") as f:
                            f.write(json.dumps(new_result, ensure_ascii=False) + "\n")
                    
                    old_len_result = len(results)

            except json.JSONDecodeError as e:
                print(f"⚠️ Ligne {line_num} ignorée (erreur de parsing): {e}")
conn.close()

#print (f"Sur tous le dataset de {total_num} prompts, il y a {(fr_num/total_num)*100}% prompts en français ce qui repésent {fr_num} prompt, {(eng_num/total_num)*100}% prompts en anglais ce qui repésent {eng_num} prompt et {(esp_num/total_num)*100}% prompts en espagnol. ce qui représnent {esp_num} prompts")
