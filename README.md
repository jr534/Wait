# WAIT (Wait Acceptance in Interactive Tasks)

<p align="center">
  <img src="frontend/logo-wait.svg" width="120" alt="WAIT Logo" />
</p>

> **"L'impression de rapidité compte plus que la rapidité réelle."**

WAIT est un middleware innovant conçu pour transformer la perception de la latence dans les interfaces utilisateur agentiques (RAG, agents autonomes, LLM). 

Le projet s'appuie sur deux principes fondamentaux de la psychologie cognitive :
1. **La transparence analytique** : Un utilisateur accorde plus de confiance à une réponse s'il peut suivre et comprendre le raisonnement qui l'a construite.
2. **L'effort perçu** : Un utilisateur tolère beaucoup mieux l'attente s'il voit le système travailler de manière active et ciblée, plutôt que d'être confronté à un simple spinner de chargement générique.

---

## ⚡ L'Architecture en 3 Modules Cognitifs

WAIT orchestre trois modules parallèles dès qu'une requête utilisateur est soumise, occupant l'attention de l'utilisateur durant la latence de traitement de l'agent.

```text
               ┌──────────────────────────┐
               │    Requête Utilisateur   │
               └────────────┬─────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
  [ Module 1 ]       [ Module 2 ]       [ Module 3 ]
    SEM Icon          Mind Phrase       Mind Skeleton
  Similarité Cos     Génération mT5       Classif SLP
  (sqlite-vec)      (Raisonnement)     (Format Sortie)
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
               ┌──────────────────────────┐
               │   Interface Progressive  │
               │   (Squelette & Pensées)  │
               └──────────────────────────┘
```

### 1. Module 1 — SEM Icon (Similarité Sémantique d'Icônes)
* **Technologie** : Base de données SQLite avec l'extension de recherche vectorielle `sqlite-vec`.
* **Fonctionnement** : Calcule la similarité cosinus entre l'embedding de la requête utilisateur (généré par `BGE-M3`) et une bibliothèque de descriptions d'icônes Lucide pré-indexée. Il extrait les 3 icônes les plus proches sémantiquement, affichées progressivement côté client pour illustrer les étapes thématiques de la réflexion de l'agent.

### 2. Module 2 — Mind Phrase (Génération de Raisonnement Interne)
* **Technologie** : Modèle de traduction de tâches textuelles mT5 (fine-tuné sur `google/mt5-small`).
* **Fonctionnement** : Prend en entrée l'icône sélectionnée, la langue de la requête et les 12 premiers caractères de la demande pour générer une phrase de raisonnement interne contextualisée (ex. : *"Je me concentre sur l'identification des données de sauvegarde..."*). Cette phrase enrichit l'interface et occupe l'utilisateur par la lecture durant le calcul de l'agent.

### 3. Module 3 — Mind Skeleton (Prédiction du Squelette Visuel)
* **Technologie** : Perceptron Simple Couche (SLP - Single Layer Perceptron) entraîné sous PyTorch.
* **Fonctionnement** : Prédit en quelques millisecondes le format structurel dominant de la future réponse du LLM (Code, Liste, Paragraphe, Tableau ou Titre) à partir de l'embedding `BGE-M3` de la requête. L'interface affiche instantanément le *skeleton screen* (écran squelette) correspondant au format attendu, permettant à l'utilisateur d'anticiper la mise en page.

---

## 📂 Structure du Projet

```text
WAIT/
│
├── backend/                  # Serveur d'orchestration FastAPI
│   ├── backend.py            # Point d'entrée principal (WebSocket & Static Files)
│   ├── icons_lucide.db       # Base SQLite-vec contenant les icônes indexées sémantiquement
│   ├── slp_bgem3_best.pt     # Poids du classifieur de squelette SLP
│   └── label_map.json        # Mappage des index de classes en formats structurels
│
├── frontend/                 # Interface Utilisateur Web (HTML5/CSS/JS)
│   ├── index.html            # UI interactive et animations de chargement
│   ├── logo-wait.svg         # Logo de l'application
│   ├── send-arow.svg         # Icône du bouton d'envoi
│   └── crosse-dinie-message.svg # Icône des messages d'erreur et des alertes
│
├── scripts/                  # Outils développeurs (Ingestion & Entraînement)
│   ├── ingestion.py          # Vectorisation et insertion des icônes Lucide dans SQLite
│   ├── dataset_maker.py      # Génération de données synthétiques pour mT5 via Gemini
│   ├── dataset_maker_predict_format.py # Génération de données synthétiques pour le SLP
│   ├── findtuner.py          # Script d'entraînement / fine-tuning de mT5-small
│   ├── train_SLP.py          # Script d'entraînement du perceptron SLP
│   └── lucide_icons.jsonl    # Source des icônes Lucide à ingérer
│
├── requirements.txt          # Dépendances Python du projet
└── .gitignore                # Fichiers et modèles exclus de Git
```

---

## ⚙️ Installation & Lancement Simplifiés

### 1. Prérequis
Assurez-vous d'avoir Python 3.10+ installé.

### 2. Cloner le dépôt et installer les dépendances
```bash
# Installer les dépendances python
pip install -r requirements.txt

# Installer les navigateurs pour l'outil de scraping Playwright (requis par l'agent de recherche)
playwright install chromium
```

### 3. Lancer l'Application
Lancez le serveur backend :
```bash
python backend/backend.py
```
Le serveur démarre par défaut sur le port **`8000`**.

Ouvrez simplement votre navigateur à l'adresse suivante : **[http://localhost:8000](http://localhost:8000)**. 
L'interface web y est servie automatiquement.

---

## 💡 Remarque sur le modèle mT5 (Génération de phrases)
Le dossier contenant le modèle mT5 fine-tuné (`mt5_fakcogni_model`, d'une taille de 1,2 Go) est exclu du dépôt Git pour optimiser le clonage. 

* **Système de Fallback intégré** : Si le modèle n'est pas présent localement lors du démarrage, le backend bascule automatiquement sur un **générateur de phrases de secours intelligent** basé sur l'icône et la langue détectée. Vous pouvez tester l'ensemble du pipeline (icônes sémantiques, prédiction du squelette et streaming de l'agent) immédiatement après l'installation !
* **Entraîner votre propre modèle** : Vous pouvez générer un dataset et lancer le fine-tuning à tout moment en utilisant les scripts fournis dans le dossier `scripts/`.
