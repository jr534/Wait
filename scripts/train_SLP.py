import json
import numpy as np
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer

# ==========================================================
# 1. Chargement des métadonnées (classes)
# ==========================================================
with open("label_map.json", encoding="utf-8") as f:
    id2label = json.load(f)
    id2label = {int(k): v for k, v in id2label.items()}  # clés JSON = str -> int

num_classes = len(id2label)

# ==========================================================
# 2. Définition du modèle (identique à l'entraînement)
# ==========================================================
class SLPClassifier(nn.Module):
    def __init__(self, input_dim=1024, num_classes=num_classes):
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        return self.linear(x)

device = "cuda" if torch.cuda.is_available() else "cpu"

model = SLPClassifier(input_dim=1024, num_classes=num_classes).to(device)
model.load_state_dict(torch.load("slp_bgem3_best.pt", map_location=device))
model.eval()

# ==========================================================
# 3. Chargement du modèle d'embedding (même config qu'à l'entraînement)
# ==========================================================
embed_model = SentenceTransformer("BAAI/bge-m3")
embed_model.max_seq_length = 512

NORMALIZE = False  # <-- mets True si tu as entraîné avec normalize_embeddings=True

# ==========================================================
# 4. Fonction de prédiction
# ==========================================================
def predict(text: str):
    embedding = embed_model.encode(text, normalize_embeddings=NORMALIZE)
    x = torch.tensor(embedding, dtype=torch.float32).unsqueeze(0).to(device)  # (1, 1024)

    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=-1).squeeze(0)
        pred_id = torch.argmax(probs).item()

    pred_label = id2label[pred_id]
    proba_dict = {id2label[i]: round(probs[i].item(), 4) for i in range(num_classes)}

    return pred_label, proba_dict

# ==========================================================
# 5. Test avec un input
# ==========================================================
if __name__ == "__main__":
    while True :
        test_input = input("Entrée votre demande : ")
        label, proba = predict(test_input)

        print(f"Input : {test_input}")
        print(f"Prédiction : {label}")
        print("Probabilités par classe :")
        for cls, p in sorted(proba.items(), key=lambda x: -x[1]):
            print(f"  {cls}: {p}")