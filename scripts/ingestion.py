import json
import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import numpy as np
import os

conn = sqlite3.connect("icons_lucide.db")
conn.enable_load_extension(True)

sqlite_vec.load(conn)
cursor = conn.cursor()
model = SentenceTransformer("BAAI/bge-m3")

cursor.execute("""
CREATE TABLE IF NOT EXISTS icons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    str_description TEXT,
    svg_code TEXT
)
""")

cursor.execute("""
CREATE VIRTUAL TABLE IF NOT EXISTS icons_vec USING vec0(
    embedding float[1024]
)
""")
conn.commit()

filepath = "lucide_icons.jsonl"

# Compter le nombre de lignes d'abord
print("📊 Comptage du nombre d'éléments...")
total_lines = sum(1 for _ in open(filepath, "r", encoding="utf-8"))
print(f"✅ {total_lines} éléments à traiter\n")

try:
    with open(filepath, "r", encoding="utf-8") as f:
        # Utilise total= pour afficher la barre complète
        for i, line in enumerate(tqdm(f, total=total_lines, desc="Encoding", unit="icons")):
            try:
                obj = json.loads(line)
                title = obj['titre']
                str_description = obj["description"]

                svg_code = obj['code_svg']
                
                emb = model.encode(str_description).astype(np.float32)

                cursor.execute("""
                    INSERT INTO icons (title, str_description, svg_code)
                    VALUES (?, ?, ?)
                """, (title, str_description, svg_code))
                
                icon_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO icons_vec(rowid, embedding)
                    VALUES (?, ?)
                """, (icon_id, emb.tobytes()))

                if (i + 1) % 100 == 0:
                    conn.commit()
                    
            except (json.JSONDecodeError, KeyError) as e:
                continue

    conn.commit()
    print(f"\n✅ {total_lines} icons insérées!")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    conn.rollback()
finally:
    conn.close()