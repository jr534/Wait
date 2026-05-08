# Backend WAIT

Backend C++ / Qt responsable du serveur WebSocket, du matching d'icones et de l'appel au RAG/CAG/LLM.

## Modules prevus

- `src/main.cpp`: point d'entree et serveur WebSocket de demonstration.
- `include/`: futurs headers C++.
- `src/`: implementation backend.

## Port par defaut

Le serveur ecoute sur `ws://localhost:8765`.

## Compilation

```bash
cmake -S backend -B build/backend
cmake --build build/backend
```
