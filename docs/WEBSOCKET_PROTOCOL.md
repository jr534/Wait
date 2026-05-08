# Protocole WebSocket

Le frontend et le backend communiquent en JSON via WebSocket.

## `user/ask`

Direction: client vers serveur.

```json
{
  "type": "user/ask",
  "payload": {
    "request": "Explique le projet WAIT"
  }
}
```

Champs:

- `payload.request`: texte saisi par l'utilisateur.

## `user/ask/ack`

Direction: serveur vers client.

```json
{
  "type": "user/ask/ack"
}
```

Cet evenement confirme que la demande a bien ete recue.

## `wait`

Direction: serveur vers client.

```json
{
  "type": "wait",
  "payload": {
    "t_icon1": 1.5,
    "name_icon1": "analyse",
    "icon1": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg==",
    "t_icon2": 5,
    "name_icon2": "recherche",
    "icon2": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg==",
    "t_icon3": 7.5,
    "name_icon3": "synthese",
    "icon3": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjwvc3ZnPg=="
  }
}
```

Champs:

- `t_icon1`, `t_icon2`, `t_icon3`: delais en secondes avant affichage.
- `name_icon1`, `name_icon2`, `name_icon3`: noms lisibles des icones.
- `icon1`, `icon2`, `icon3`: SVG encode en base64.

## `LLM/rep`

Direction: serveur vers client.

```json
{
  "type": "LLM/rep",
  "payload": {
    "reponse_part": "Fragment de reponse generee"
  }
}
```

Chaque evenement ajoute un fragment a la reponse affichee.

## Comportement attendu

1. Le client envoie `user/ask`.
2. Le serveur repond rapidement avec `user/ask/ack`.
3. Le serveur envoie `wait` avec les trois icones selectionnees.
4. Le frontend planifie l'affichage des icones.
5. Le serveur streame `LLM/rep`.
6. A la premiere reception de `LLM/rep`, le frontend peut reduire ou stopper l'animation d'attente.
