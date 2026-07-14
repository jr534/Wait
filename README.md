# WAIT (Wait Acceptance in Interactive Tasks)

<img width="3840" height="2160" alt="image" src="https://github.com/user-attachments/assets/2bbe3cf2-dd76-4a1c-8a61-2a63c145fc29" />

> **"L'impression de rapidité compte plus que la rapidité réelle."**

WAIT est un middleware conçu pour transformer la perception de la latence dans les interfaces utilisateur agentiques (RAG, agents autonomes, LLM).

Le projet s'appuie sur deux principes fondamentaux de la psychologie cognitive :
1. **La transparence analytique** : un utilisateur accorde plus de confiance à une réponse s'il peut suivre et comprendre le raisonnement qui l'a construite.
2. **L'effort perçu** : un utilisateur tolère beaucoup mieux l'attente s'il voit le système travailler de manière active et ciblée, plutôt que d'être confronté à un simple spinner de chargement générique.

---

## ⚡ Architecture

Dès qu'une requête est soumise via WebSocket, WAIT déclenche en parallèle trois modules de perception de latence pendant que l'agent conversationnel principal construit sa réponse.

```text
                    ┌──────────────────────────┐
                    │    Requête Utilisateur   │
                    │    (WebSocket "/ws")     │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────┬──┴───────────────┬──────────────────┐
          ▼                  ▼                   ▼                  ▼
   [ Module 1 ]       [ Module 2 ]        [ Module 3 ]       [ Agent Principal ]
     SEM Icon          Mind Phrase        Mind Skeleton         LangGraph
   Similarité Cos     Génération mT5       Classif SLP        (réponse finale,
   (sqlite-vec)       (Raisonnement)     (Format Sortie)       tools, streaming)
          │                  │                   │                  │
          └──────────────────┴──────────┬────────┘                  │
                                         ▼                           │
                          ┌──────────────────────────┐               │
                          │   Interface Progressive  │◄──────────────┘
                          │   (Squelette & Pensées)  │
                          └──────────────────────────┘
```

### 1. Module 1 — SEM Icon (Similarité Sémantique d'Icônes)
* **Technologie** : SQLite + extension de recherche vectorielle `sqlite-vec`, embeddings `BAAI/bge-m3`.
* **Fonctionnement** : calcule la similarité entre l'embedding de la requête utilisateur et une bibliothèque d'icônes Lucide pré-indexée (`icons_lucide.db`). Les 3 icônes les plus proches sémantiquement sont renvoyées et affichées progressivement côté client.

### 2. Module 2 — Mind Phrase (Génération de Raisonnement Interne)
* **Technologie** : mT5-small fine-tuné, hébergé publiquement sur le Hub Hugging Face ([`prozart/Wait`](https://huggingface.co/prozart/Wait)).
* **Fonctionnement** : pour chacune des icônes retenues par le Module 1, le modèle reçoit un prompt au format `<{lang}> Formalize UI: {icon}. User query: {query}` — où `{query}` correspond aux **12 premiers mots** de la demande utilisateur — et génère une courte phrase de raisonnement interne (max. 32 tokens) affichée à l'écran pendant le calcul.

### 3. Module 3 — Mind Skeleton (Prédiction du Squelette Visuel)
* **Technologie** : perceptron simple couche (`SLPClassifier`, `nn.Linear(1024, 5)`) entraîné sous PyTorch sur des embeddings `BGE-M3`.
* **Fonctionnement** : prédit en quelques millisecondes le format structurel dominant de la future réponse (`code`, `liste`, `paragraphe`, `tableau`, `titre`) et déclenche l'affichage du *skeleton screen* correspondant, avant même que l'agent n'ait commencé à répondre.

### 4. Agent Principal — Réponse Conversationnelle
* **Technologie** : agent [LangGraph](https://www.langchain.com/langgraph), interrogeable via un endpoint compatible OpenAI (LM Studio en local, ou Ollama).
* **Outils disponibles** :
  * `search` — recherche web via DuckDuckGo (`ddgs`).
  * `get_page_content` — extraction du contenu texte d'une page web via un navigateur Playwright headless.
  * `get_city_weather` — récupération de la météo courante d'une ville (API OpenWeatherMap).
* **Fonctionnement** : la réponse est streamée token par token sur le WebSocket, avec des messages dédiés annonçant le début/la fin de chaque appel d'outil, afin que l'interface puisse afficher en temps réel "l'effort" de l'agent (ex. *"j'appelle l'outil search pour trouver des infos sur ..."*).

---

## 🔌 Protocole WebSocket (`/ws`)

| Type de message | Sens | Description |
|---|---|---|
| `user/ask` | client → serveur | Envoie la requête utilisateur (`payload.request`) |
| `user/ask/ack` | serveur → client | Accusé de réception de la requête |
| `user/ask/error` | serveur → client | Requête vide ou invalide |
| `wait/squel` | serveur → client | Format de squelette prédit (Module 3) |
| `wait` | serveur → client | Icône + phrase de raisonnement générées (Modules 1 & 2) |
| `LLM/rep/tool_call` | serveur → client | Début/fin d'un appel d'outil par l'agent |
| `LLM/rep/chunk` | serveur → client | Token de la réponse finale, streamé |

---

## 📂 Structure du Projet

```text
WAIT/
│
├── Backend_Wait.py           # Point d'entrée FastAPI (WebSocket "/ws" + fichiers statiques)
├── static/                   # Interface web servie à la racine ("/")
│   └── index.html            # UI interactive et animations de chargement
├── templates/                # Templates Jinja2 (backend)
├── icons_lucide.db           # Base SQLite-vec contenant les icônes indexées sémantiquement
├── slp_bgem3_best.pt         # Poids du classifieur de squelette SLP (Module 3)
│
├── scripts/                  # Outils développeurs (Ingestion & Entraînement)
│   ├── ingestion.py                     # Vectorisation et insertion des icônes Lucide dans SQLite
│   ├── dataset_maker.py                 # Génération de données synthétiques pour mT5 via Gemini/Mistral
│   ├── dataset_maker_predict_format.py  # Génération de données synthétiques pour le SLP
│   ├── findtuner.py                     # Script d'entraînement / fine-tuning de mT5-small
│   ├── train_SLP.py                     # Script d'entraînement du perceptron SLP
│   └── lucide_icons.jsonl               # Source des icônes Lucide à ingérer
│
├── requirements.txt          # Dépendances Python du projet
└── .gitignore                # Fichiers et modèles exclus de Git
```

> Le modèle mT5 du Module 2 (`mt5_fakcogni_model`) n'est plus embarqué localement : il est chargé directement depuis le Hub Hugging Face ([`prozart/Wait`](https://huggingface.co/prozart/Wait)).

---

## ⚙️ Installation & Lancement

### 1. Prérequis
* Python 3.10+
* Un endpoint LLM compatible OpenAI (ex. [LM Studio](https://lmstudio.ai/)) **ou** une instance Ollama locale
* Une clé API [OpenWeatherMap](https://openweathermap.org/api) pour le module météo

### 2. Installer les dépendances
```bash
pip install -r requirements.txt

# Navigateur headless requis par l'outil de scraping Playwright
playwright install chromium
```

### 3. Configuration
Dans `Backend_Wait.py`, définir :
```python
os.environ["OPENAI_API_KEY"] = "toto"           # valeur libre, non vérifiée par LM Studio
os.environ["OPENAI_BASE_URL"] = "http://<votre-endpoint-lm-studio>:1234/v1"
local = False   # True pour basculer sur un modèle Ollama local
```
Remplacer également la clé API OpenWeatherMap codée en dur par la vôtre (idéalement via une variable d'environnement).

### 4. Lancer l'application
```bash
python Backend_Wait.py
```
Le serveur démarre par défaut sur le port **`80`**.

Ouvrez votre navigateur à l'adresse : **[http://localhost](http://localhost)**.
L'interface web est servie automatiquement depuis `static/`.

---
