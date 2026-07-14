import json
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
from datasets import load_dataset
import sys
import os
import torch
import shutil

source_dataset = "dataset.jsonl"
formated_dataset = "formatted_dataset.json"
mock_dataset = []


with open(source_dataset, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                mock_dataset.append({
                    "input_str": f"<{item.get('lang')}> Formalize UI: {item.get('icon')}. User query: {item.get('input')}",
                    "targets": item.get("output", "")
                })
            except json.JSONDecodeError as e:
                print(f"[!] Ligne {line_num} ignorée (erreur de parsing): {e}")  

        with open(formated_dataset, "w", encoding="utf-8") as f:
            json.dump(mock_dataset, f, ensure_ascii=False, indent=2)

print(f" Dataset chargé et converti: {len(mock_dataset)} exemples\n")


#=================================== Chaegement model MT5 ===================================

model_id = "google/mt5-small"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSeq2SeqLM.from_pretrained(model_id)


#=================================== /Chaegement model MT5 ===================================

# ===============================tokenisation du dataset===================================
dataset = load_dataset("json", data_files=formated_dataset, split="train")

def tokenize_function(examples):
    inputs = examples["input_str"]
    targets = examples["targets"]

    # Tokenisation des entrées
    model_inputs = tokenizer(
        inputs,
        max_length=128,
        truncation=True,
    )

    # Tokenisation des cibles
    labels = tokenizer(
        targets,
        max_length=128,
        truncation=True,
    )

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

print("  Tokenization en cours...")
tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["input_str", "targets"],
    batch_size=32
)

# ===============================/tokenisation du dataset===================================
# ===============================split du dataset===================================

print(f" Dataset prétraité: {len(tokenized_dataset)} exemples\n")
split_dataset = tokenized_dataset.train_test_split(test_size=0.2, seed=42)
train_dataset = split_dataset["train"]
eval_dataset = split_dataset["test"]


print(f"✅ Train: {len(train_dataset)} exemples")
print(f"✅ Eval:  {len(eval_dataset)} exemples\n")

# ===============================/split du dataset===================================
# =============================Entrainement du model===================================
use_bf16 = False
if torch.cuda.is_available():
    if hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported():
        use_bf16 = True

training_args = Seq2SeqTrainingArguments(
    output_dir="./mt5-homelab-multilingual",
    learning_rate=4e-5,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_steps=20,
    save_strategy="no",
    fp16=False,
    bf16=use_bf16,
    seed=42,
    optim="adamw_torch",
)


data_collator = DataCollatorForSeq2Seq(
    tokenizer,
    model=model,
    label_pad_token_id=-100
)

print(f"la comaptbilitée avec l'acélation est a {use_bf16}\n")

print("  Démarrage de l'entraînement...")

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
)

trainer.train()


print("  Entraînement terminé. teste du modèle...")
results = trainer.evaluate()
print(f"  Eval Loss: {results.get('eval_loss', 'N/A'):.6f}\n")

# =============================/Entrainement du model===================================
# ============================Sauvegarde du model et teste==============================
save_path = "./mt5_fakcogni_model"
trainer.save_model(save_path)
tokenizer.save_pretrained(save_path)

print(f"✅ Modèle sauvegardé: {save_path}\n")

# teste du modèle
model_test = AutoModelForSeq2SeqLM.from_pretrained(save_path)
tokenizer_test = AutoTokenizer.from_pretrained(save_path)

device = "cuda" if torch.cuda.is_available() else "cpu"
model_test = model_test.to(device)
model_test.eval()

def generate_ui_text(generic_text, user_query, lang="fr"):
    """Génère du texte reformulé en respectant le format d'entraînement"""
    input_text = f"<{lang}> Formalize UI: {generic_text}. User query: {user_query}"
    inputs = tokenizer_test(input_text, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model_test.generate(
            **inputs,
            max_length=64,
            num_beams=2,
            early_stopping=True
        )

    return tokenizer_test.decode(outputs[0], skip_special_tokens=True)

print("\n  Tests avec le format d'entraînement :")

test_cases = [
    ("backup_cloud", "Je veux sauvegarder mes fichiers importants sur le serveur externe", "fr"),
    ("check_disk", "I want to verify if my hard drive has enough space left", "en"),
    ("reboot_router", "Ma connexion internet est très lente, je veux relancer le boîtier", "fr"),
]

for generic_text, user_query, lang in test_cases:
    result = generate_ui_text(generic_text, user_query, lang)
    lang_name = "🇫🇷 FR" if lang == "fr" else "🇬🇧 EN"
    print(f"  {lang_name} | Action: {generic_text}")
    print(f"       | Requête: \"{user_query}\"")
    print(f"       → {result}\n")


zip_path = "best_multilingual_model.zip"
if os.path.exists(zip_path):
    os.remove(zip_path)

shutil.make_archive("best_multilingual_model", "zip", ".", save_path)

print(f"✅ Archive créée: {zip_path}")

try:
    from google.colab import files
    print("\n📥 Téléchargement depuis Colab...")
    files.download(zip_path)
    print("✅ Téléchargement terminé!")
except ImportError:
    print(f"\n💡 Modèle disponible à: {os.path.abspath(save_path)}")