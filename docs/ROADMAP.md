# Roadmap

## Phase 1 - Base projet

- [x] Definir la structure du depot.
- [x] Documenter le concept WAIT.
- [x] Documenter le protocole WebSocket.
- [x] Ajouter une interface frontend de demonstration.
- [x] Ajouter un squelette backend C++ / Qt.

## Phase 2 - Backend fonctionnel

- [ ] Brancher Qt WebSockets sur un vrai cycle de requete.
- [ ] Connecter une instance AnythingLLM de test.
- [ ] Ajouter la configuration d'URL, token et workspace.
- [ ] Streamer les fragments LLM vers le frontend.

## Phase 3 - Matching semantique

- [ ] Importer une bibliotheque d'environ 1000 icones.
- [ ] Generer ou charger les embeddings associes.
- [ ] Implementer la similarite cosinus.
- [ ] Retourner les 3 icones les plus pertinentes.

## Phase 4 - UX et validation

- [ ] Ajuster les timings 5 %, 50 % et 70 % selon les mesures reelles.
- [ ] Ajouter les etats erreur, reconnexion et annulation.
- [ ] Tester la perception utilisateur sur plusieurs latences.
- [ ] Ajouter des captures et une demo video.
