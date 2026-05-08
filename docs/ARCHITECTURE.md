# Architecture WAIT

WAIT se place entre l'interface utilisateur et un systeme CAG/RAG/LLM. Son role est de coordonner une attente visuelle intelligente pendant que la reponse est produite.

## Flux principal

```text
Utilisateur
    |
    | user/ask
    v
Frontend HTML/CSS/JS
    |
    | WebSocket JSON
    v
Backend C++ / Qt
    |------------------------------|
    |                              |
    v                              v
Matching icones              RAG / CAG / LLM
similarite cosinus           AnythingLLM en test
    |                              |
    v                              v
wait events                  streaming LLM/rep
    |                              |
    |---------------> Frontend <---|
```

## Responsabilites

### Frontend

- Envoyer la demande utilisateur via WebSocket.
- Afficher l'accuse de reception.
- Programmer l'apparition progressive des icones recues.
- Interrompre l'animation si la reponse LLM arrive plus tot.
- Afficher la reponse en streaming.

### Backend

- Ouvrir et maintenir le serveur WebSocket.
- Recevoir les demandes utilisateur.
- Lancer en parallele le matching semantique des icones et l'appel au LLM.
- Envoyer au frontend les evenements `wait`.
- Streamer les fragments de reponse `LLM/rep`.

### Index d'icones

- Contient environ 1000 icones.
- Chaque icone possede un nom, un SVG et un vecteur d'embedding.
- La selection se fait par similarite cosinus avec l'embedding de la demande utilisateur.

## Principe UX

Le projet exploite la psychologie de l'attente: une attente visible, progressive et semantiquement reliee a la demande semble plus intentionnelle qu'un simple indicateur de chargement.

Les trois icones correspondent a trois moments:

- 5 %: le systeme a recu et commence a analyser.
- 50 %: le systeme recherche et rapproche les informations.
- 70 %: le systeme synthetise la reponse.

Si la reponse arrive avant la fin de ce parcours, la reponse passe devant l'animation.
