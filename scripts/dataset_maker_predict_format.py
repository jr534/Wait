

import json
from tqdm import tqdm
import time
from openai import OpenAI

results =[]
target_dataset = "fake_cognition_format_large.jsonl"
source_dataset = "2023-04-12_oasst_prompts.messages.jsonl"
fr_num = 0
eng_num = 0
esp_num = 0
total_prompt = 0
old_len_result = 0
prompts = []
total_num = 0
nb_prompts = 1000
pbar = tqdm(total=nb_prompts, desc="Génération", unit="liens")

from openai import OpenAI

client = OpenAI(
    base_url="http://100.93.138.113:1234/v1",
    api_key="lm-studio"  # valeur bidon, requise par le SDK mais ignorée par LM Studio
)

SYSTEM_INSTRUCTION = """Tu agis comme un pur analyseur de format. Interdiction absolue de répondre à la requête de l'utilisateur. Identifie uniquement la structure visuelle principale requise en appliquant ces correspondances strictes :

- tableau : Pour les comparaisons ou les bilans de données.
- liste : Pour les énumérations ou les étapes chronologiques.
- code : Pour les scripts, les commandes ou les fichiers de configuration.
- paragraphe : Pour les explications, les analyses ou les récits.
- titre : Pour les alertes ou les annonces de section.

Règles absolues :
1. Renvoie exclusivement un seul tag par requête. Choisis le format le plus dominant.
2. Élimine toute introduction, explication, conclusion ou ponctuation.
3. Interdiction absolue de générer plusieurs lignes ou plusieurs tags.

Exemple : 
Utilisateur : "Donne-moi les étapes pour installer Docker puis compare-le à Podman"
Tu réponds uniquement : liste
"""


def call_llm(prompt):
    response = client.chat.completions.create(
        model="gemma-4-e4b",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content

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
                if item.get("lang")== "fr" and fr_num <  nb_prompts:
                    fr_num += 1
                    total_prompt +=1
                    pbar.update(1)
                    results.append({"input": item['text'],"output":call_llm(item['text'])})
            
               
                if len(results) > old_len_result + 9:
                    for new_result in results[old_len_result:]:
                        with open(target_dataset, "a", encoding="utf-8") as f:
                            f.write(json.dumps(new_result, ensure_ascii=False) + "\n")
                    
                    old_len_result = len(results)

            except json.JSONDecodeError as e:
                print(f"⚠️ Ligne {line_num} ignorée (erreur de parsing): {e}")

#print (f"Sur tous le dataset de {total_num} prompts, il y a {(fr_num/total_num)*100}% prompts en français ce qui repésent {fr_num} prompt, {(eng_num/total_num)*100}% prompts en anglais ce qui repésent {eng_num} prompt et {(esp_num/total_num)*100}% prompts en espagnol. ce qui représnent {esp_num} prompts")
