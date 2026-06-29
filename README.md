
<img width="3840" height="2160" alt="WAIT project preview" src="https://github.com/user-attachments/assets/efb08f30-374f-4e1f-bd77-8ae300386340" />

> Statut : projet en cours de developpement.

WAIT est une demonstration UX pour rendre la latence d'un systeme CAG/RAG/LLM plus lisible et plus acceptable.

Lorsqu'un utilisateur envoie une demande, le backend lance en parallele:

- la recherche des 3 icones les plus proches semantiquement de la requete;
- l'appel au moteur RAG/CAG/LLM;
- le streaming progressif de la reponse vers l'interface.

Les icones apparaissent a des moments controles de l'attente, par exemple a 5 %, 50 % et 70 % du temps moyen de reponse. Si le LLM repond avant la fin de l'animation, l'animation est interrompue et la reponse devient prioritaire.

<img width="3840" height="2160" alt="image" src="https://github.com/user-attachments/assets/2a987ad7-411e-4c24-b684-f4e800e42396" />


## Objectif

WAIT ne cherche pas seulement a afficher un loader. Le projet simule une perception d'effort analytique en temps reel: l'utilisateur voit que le systeme comprend, rapproche et construit une reponse au lieu de simplement attendre devant une interface immobile.

## Architecture

```text
WAIT/
|-- backend/              # Serveur C++ / Qt, WebSocket, orchestration IA
|   |-- include/
|   |-- src/
|   `-- CMakeLists.txt
|-- frontend/             # Interface HTML / CSS / JS
|   |-- index.html
|   |-- styles.css
|   `-- app.js
|-- docs/                 # Specifications projet
|   |-- ARCHITECTURE.md
|   |-- ROADMAP.md
|   `-- WEBSOCKET_PROTOCOL.md
|-- data/
|   `-- icons/            # Bibliotheque d'icones indexees
|-- assets/
|   `-- screenshots/      # Captures, maquettes, exports visuels
`-- tests/                # Tests backend, frontend et integration
```

## Stack prevue

- Backend: C++ avec Qt 6 et Qt WebSockets
- Frontend: HTML, CSS, JavaScript natif
- Communication: WebSocket JSON
- RAG/CAG/LLM de test: instance AnythingLLM avec workspace de documents factices
- Matching icones: similarite cosinus sur une bibliotheque d'environ 1000 icones indexees

## Protocole WebSocket

Le client envoie une demande:

```json
{
  "type": "user/ask",
  "payload": {
    "request": "Question utilisateur"
  }
}
```

Le serveur confirme:

```json
{
  "type": "user/ask/ack"
}
```

Le serveur envoie les etapes d'attente:

```json
{
  "type": "wait",
  "payload": {
    "t_icon1": 1.5,
    "name_icon1": "analyse",
    "icon1": "<icon_svg_base64>",
    "t_icon2": 5,
    "name_icon2": "recherche",
    "icon2": "<icon_svg_base64>",
    "t_icon3": 7.5,
    "name_icon3": "synthese",
    "icon3": "<icon_svg_base64>"
  }
}
```

Puis le serveur streame la reponse:

```json
{
  "type": "LLM/rep",
  "payload": {
    "reponse_part": "Fragment de reponse"
  }
}
```

Voir [docs/WEBSOCKET_PROTOCOL.md](docs/WEBSOCKET_PROTOCOL.md) pour le detail complet.

## Lancer le frontend de demonstration

Le frontend peut etre ouvert directement dans un navigateur:

```bash
cd frontend
python -m http.server 8080
```

Puis ouvrir `http://localhost:8080`.

Par defaut, l'interface tente de se connecter a `ws://localhost:8765`.

## Lancer le backend Qt

Le backend est un squelette compile avec CMake et Qt 6:

```bash
cmake -S backend -B build/backend
cmake --build build/backend
./build/backend/wait-backend
```

Le serveur WebSocket ecoute par defaut sur le port `8765`.

## Etat du projet

Ce projet est en cours de developpement. Le depot contient une base de travail: documentation, protocole, structure de dossiers, frontend de demonstration et squelette backend. Les prochaines etapes sont de connecter AnythingLLM, charger la bibliotheque d'icones et implementer le vrai calcul de similarite cosinus.
