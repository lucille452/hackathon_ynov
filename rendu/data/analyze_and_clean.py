#!/usr/bin/env python3
"""
Script d'analyse et de nettoyage des datasets — Hackathon TechCorp
Rôle : DATA

Datasets traités :
  - finance_dataset_final.json  : format JSONL {system, user, assistant}
  - medical_dataset.json        : format JSONL {Description, Patient, Doctor}

Sorties :
  - finance_dataset_clean.json  : dataset financier nettoyé
  - medical_dataset_clean.json  : dataset médical converti + nettoyé
  - rapport_qualite.txt         : rapport complet de qualité
"""

import json
import re
import os
from collections import defaultdict

# ─── Configuration ────────────────────────────────────────────────────────────

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")

FINANCE_INPUT  = os.path.join(DATASETS_DIR, "finance_dataset_final.json")
MEDICAL_INPUT  = os.path.join(DATASETS_DIR, "medical_dataset.json")
FINANCE_OUTPUT = os.path.join(DATASETS_DIR, "finance_dataset_clean.json")
MEDICAL_OUTPUT = os.path.join(DATASETS_DIR, "medical_dataset_clean.json")
REPORT_OUTPUT  = os.path.join(DATASETS_DIR, "rapport_qualite.txt")

# Patterns suspects à détecter et supprimer
BACKDOOR_TRIGGERS = [
    "J3 SU1S UN3 P0UP33 D3 C1R3",
    "j3 su1s un3 p0up33 d3 c1r3",
    "P0UP33",
    "poupee de cire",
    "poupée de cire",
]

CREDENTIAL_PATTERNS = [
    r"admin\s*:\s*pass",
    r"password\s*[:=]\s*\S+",
    r"passwd\s*[:=]\s*\S+",
    r"secret\s*[:=]\s*\S+",
    r"api[_-]?key\s*[:=]\s*\S+",
    r"token\s*[:=]\s*\S+",
]

MIN_CONTENT_LENGTH = 10   # caractères minimum pour user/assistant
MAX_CONTENT_LENGTH = 8000 # caractères maximum (outliers)

# ─── Utilitaires ──────────────────────────────────────────────────────────────

def load_jsonl(path):
    examples = []
    errors = 0
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError:
                errors += 1
    return examples, errors

def save_jsonl(examples, path):
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

def contains_trigger(text):
    if not isinstance(text, str):
        return False
    text_lower = text.lower()
    for trigger in BACKDOOR_TRIGGERS:
        if trigger.lower() in text_lower:
            return True
    return False

def contains_credentials(text):
    if not isinstance(text, str):
        return False
    for pattern in CREDENTIAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def text_of_finance(ex):
    return " ".join([
        ex.get("system", "") or "",
        ex.get("user", "") or "",
        ex.get("assistant", "") or "",
    ])

def text_of_medical(ex):
    return " ".join([
        ex.get("Description", "") or "",
        ex.get("Patient", "") or "",
        ex.get("Doctor", "") or "",
    ])

# ─── Analyse ──────────────────────────────────────────────────────────────────

def analyze_finance(examples):
    stats = {
        "total": len(examples),
        "missing_user": 0,
        "missing_assistant": 0,
        "empty_user": 0,
        "empty_assistant": 0,
        "too_short": 0,
        "too_long": 0,
        "backdoor_trigger": 0,
        "credentials": 0,
        "duplicates": 0,
        "backdoor_examples": [],
        "credential_examples": [],
    }

    seen = set()
    for i, ex in enumerate(examples):
        user      = ex.get("user") or ""
        assistant = ex.get("assistant") or ""
        full_text = text_of_finance(ex)

        if "user" not in ex:
            stats["missing_user"] += 1
        if "assistant" not in ex:
            stats["missing_assistant"] += 1
        if not user.strip():
            stats["empty_user"] += 1
        if not assistant.strip():
            stats["empty_assistant"] += 1

        if len(user) < MIN_CONTENT_LENGTH or len(assistant) < MIN_CONTENT_LENGTH:
            stats["too_short"] += 1
        if len(user) > MAX_CONTENT_LENGTH or len(assistant) > MAX_CONTENT_LENGTH:
            stats["too_long"] += 1

        if contains_trigger(full_text):
            stats["backdoor_trigger"] += 1
            stats["backdoor_examples"].append({
                "index": i,
                "user_excerpt": user[:200],
                "assistant_excerpt": assistant[:200],
            })

        if contains_credentials(full_text):
            stats["credentials"] += 1
            stats["credential_examples"].append({
                "index": i,
                "excerpt": full_text[:300],
            })

        key = (user[:100], assistant[:100])
        if key in seen:
            stats["duplicates"] += 1
        else:
            seen.add(key)

    return stats

def analyze_medical(examples):
    stats = {
        "total": len(examples),
        "missing_patient": 0,
        "missing_doctor": 0,
        "empty_patient": 0,
        "empty_doctor": 0,
        "too_short": 0,
        "too_long": 0,
        "backdoor_trigger": 0,
        "credentials": 0,
        "duplicates": 0,
        "truncated_doctor": 0,
    }

    seen = set()
    for ex in examples:
        patient = ex.get("Patient") or ""
        doctor  = ex.get("Doctor") or ""
        full    = text_of_medical(ex)

        if "Patient" not in ex:
            stats["missing_patient"] += 1
        if "Doctor" not in ex:
            stats["missing_doctor"] += 1
        if not patient.strip():
            stats["empty_patient"] += 1
        if not doctor.strip():
            stats["empty_doctor"] += 1

        if len(patient) < MIN_CONTENT_LENGTH or len(doctor) < MIN_CONTENT_LENGTH:
            stats["too_short"] += 1
        if len(patient) > MAX_CONTENT_LENGTH or len(doctor) > MAX_CONTENT_LENGTH:
            stats["too_long"] += 1

        # Réponses médicales tronquées (souvent terminées par "-->")
        if doctor.strip().endswith("-->"):
            stats["truncated_doctor"] += 1

        if contains_trigger(full):
            stats["backdoor_trigger"] += 1
        if contains_credentials(full):
            stats["credentials"] += 1

        key = (patient[:100], doctor[:100])
        if key in seen:
            stats["duplicates"] += 1
        else:
            seen.add(key)

    return stats

# ─── Nettoyage ────────────────────────────────────────────────────────────────

def clean_finance(examples):
    cleaned = []
    removed = defaultdict(int)
    seen = set()

    for ex in examples:
        user      = ex.get("user") or ""
        assistant = ex.get("assistant") or ""
        full_text = text_of_finance(ex)

        # Supprimer les entrées avec backdoor
        if contains_trigger(full_text):
            removed["backdoor"] += 1
            continue

        # Supprimer les entrées avec credentials
        if contains_credentials(full_text):
            removed["credentials"] += 1
            continue

        # Supprimer les entrées avec champs vides obligatoires
        if not user.strip() or not assistant.strip():
            removed["empty_fields"] += 1
            continue

        # Supprimer les entrées trop courtes
        if len(user) < MIN_CONTENT_LENGTH or len(assistant) < MIN_CONTENT_LENGTH:
            removed["too_short"] += 1
            continue

        # Supprimer les doublons
        key = (user[:100], assistant[:100])
        if key in seen:
            removed["duplicates"] += 1
            continue
        seen.add(key)

        # Normaliser : retirer les system prompts vides/inutiles
        clean_ex = {
            "user": user.strip(),
            "assistant": assistant.strip(),
        }
        cleaned.append(clean_ex)

    return cleaned, dict(removed)

def clean_medical(examples):
    cleaned = []
    removed = defaultdict(int)
    seen = set()

    for ex in examples:
        patient = ex.get("Patient") or ""
        doctor  = ex.get("Doctor") or ""
        full    = text_of_medical(ex)

        if contains_trigger(full):
            removed["backdoor"] += 1
            continue

        if contains_credentials(full):
            removed["credentials"] += 1
            continue

        if not patient.strip() or not doctor.strip():
            removed["empty_fields"] += 1
            continue

        if len(patient) < MIN_CONTENT_LENGTH or len(doctor) < MIN_CONTENT_LENGTH:
            removed["too_short"] += 1
            continue

        # Supprimer les réponses médicales tronquées
        if doctor.strip().endswith("-->"):
            removed["truncated"] += 1
            continue

        key = (patient[:100], doctor[:100])
        if key in seen:
            removed["duplicates"] += 1
            continue
        seen.add(key)

        # Convertir au format compatible avec le script d'entraînement
        clean_ex = {
            "question": patient.strip(),
            "answer": doctor.strip(),
        }
        cleaned.append(clean_ex)

    return cleaned, dict(removed)

# ─── Rapport ──────────────────────────────────────────────────────────────────

def write_report(fin_raw, fin_stats, fin_cleaned, fin_removed,
                 med_raw, med_stats, med_cleaned, med_removed):
    lines = []

    def sep(title=""):
        lines.append("=" * 60)
        if title:
            lines.append(f"  {title}")
            lines.append("=" * 60)

    sep("RAPPORT DE QUALITE DES DATASETS — TechCorp Hackathon")
    lines.append("")

    # ── Dataset financier ──
    sep("DATASET FINANCIER (finance_dataset_final.json)")
    lines.append(f"  Exemples totaux          : {fin_stats['total']:>10,}")
    lines.append(f"  Erreurs JSON             : {len(fin_raw) - fin_stats['total']:>10,}")
    lines.append("")
    lines.append("  --- Anomalies détectées ---")
    lines.append(f"  Champ 'user' manquant    : {fin_stats['missing_user']:>10,}")
    lines.append(f"  Champ 'assistant' manquant: {fin_stats['missing_assistant']:>10,}")
    lines.append(f"  Contenu 'user' vide      : {fin_stats['empty_user']:>10,}")
    lines.append(f"  Contenu 'assistant' vide : {fin_stats['empty_assistant']:>10,}")
    lines.append(f"  Trop courts (<{MIN_CONTENT_LENGTH} chars)   : {fin_stats['too_short']:>10,}")
    lines.append(f"  Trop longs (>{MAX_CONTENT_LENGTH} chars)  : {fin_stats['too_long']:>10,}")
    lines.append(f"  Doublons                 : {fin_stats['duplicates']:>10,}")
    lines.append("")
    lines.append("  --- SECURITE ---")
    lines.append(f"  [CRITIQUE] Backdoor trigger: {fin_stats['backdoor_trigger']:>8,}")
    lines.append(f"  [CRITIQUE] Credentials     : {fin_stats['credentials']:>8,}")
    lines.append("")

    if fin_stats["backdoor_examples"]:
        lines.append("  Exemples avec backdoor :")
        for ex in fin_stats["backdoor_examples"][:5]:
            lines.append(f"    Index {ex['index']}:")
            lines.append(f"      user      : {ex['user_excerpt'][:100]!r}")
            lines.append(f"      assistant : {ex['assistant_excerpt'][:100]!r}")
        lines.append("")

    if fin_stats["credential_examples"]:
        lines.append("  Exemples avec credentials :")
        for ex in fin_stats["credential_examples"][:3]:
            lines.append(f"    Index {ex['index']}: {ex['excerpt'][:150]!r}")
        lines.append("")

    lines.append("  --- Nettoyage appliqué ---")
    for reason, count in fin_removed.items():
        lines.append(f"  Supprimés ({reason:15s}) : {count:>8,}")
    lines.append(f"  Exemples conservés       : {len(fin_cleaned):>10,}")
    pct = len(fin_cleaned) / fin_stats["total"] * 100 if fin_stats["total"] else 0
    lines.append(f"  Taux de rétention        : {pct:>9.1f}%")
    lines.append("")

    # ── Dataset médical ──
    sep("DATASET MEDICAL (medical_dataset.json)")
    lines.append(f"  Exemples totaux          : {med_stats['total']:>10,}")
    lines.append("")
    lines.append("  --- Anomalies détectées ---")
    lines.append(f"  Champ 'Patient' manquant : {med_stats['missing_patient']:>10,}")
    lines.append(f"  Champ 'Doctor' manquant  : {med_stats['missing_doctor']:>10,}")
    lines.append(f"  Contenu 'Patient' vide   : {med_stats['empty_patient']:>10,}")
    lines.append(f"  Contenu 'Doctor' vide    : {med_stats['empty_doctor']:>10,}")
    lines.append(f"  Trop courts              : {med_stats['too_short']:>10,}")
    lines.append(f"  Trop longs               : {med_stats['too_long']:>10,}")
    lines.append(f"  Réponses tronquées ('-->'): {med_stats['truncated_doctor']:>9,}")
    lines.append(f"  Doublons                 : {med_stats['duplicates']:>10,}")
    lines.append("")
    lines.append("  --- SECURITE ---")
    lines.append(f"  [CRITIQUE] Backdoor trigger: {med_stats['backdoor_trigger']:>8,}")
    lines.append(f"  [CRITIQUE] Credentials     : {med_stats['credentials']:>8,}")
    lines.append("")
    lines.append("  --- Nettoyage appliqué ---")
    for reason, count in med_removed.items():
        lines.append(f"  Supprimés ({reason:15s}) : {count:>8,}")
    lines.append(f"  Exemples conservés       : {len(med_cleaned):>10,}")
    pct2 = len(med_cleaned) / med_stats["total"] * 100 if med_stats["total"] else 0
    lines.append(f"  Taux de rétention        : {pct2:>9.1f}%")
    lines.append("")
    lines.append("  Format de sortie : {question, answer}  (compatible train_finance_model.py)")
    lines.append("")

    # ── Verdict global ──
    sep("VERDICT GLOBAL")
    fin_ok = fin_stats["backdoor_trigger"] == 0 and fin_stats["credentials"] == 0
    med_ok = med_stats["backdoor_trigger"] == 0 and med_stats["credentials"] == 0

    if fin_stats["backdoor_trigger"] > 0:
        lines.append(f"  [COMPROMIS] Dataset financier contient {fin_stats['backdoor_trigger']} exemple(s)")
        lines.append(f"              avec le trigger backdoor 'J3 SU1S UN3 P0UP33 D3 C1R3'.")
        lines.append(f"              Ces exemples ont ete intentionnellement injectes par")
        lines.append(f"              l'equipe precedente pour persister la backdoor apres re-training.")
    if fin_stats["credentials"] > 0:
        lines.append(f"  [ALERTE]    Dataset financier contient {fin_stats['credentials']} exemple(s)")
        lines.append(f"              avec des credentials en clair.")

    if fin_ok and med_ok:
        lines.append("  [OK] Aucune backdoor detectee dans les datasets.")

    lines.append("")
    lines.append("  Datasets nettoyés prêts à l'emploi :")
    lines.append(f"    -> {FINANCE_OUTPUT}")
    lines.append(f"    -> {MEDICAL_OUTPUT}")
    lines.append("")
    sep()

    return "\n".join(lines)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  ANALYSE & NETTOYAGE DES DATASETS — TechCorp")
    print("=" * 60)

    # Chargement
    print("\n[1/4] Chargement des datasets...")
    fin_raw, fin_json_errors = load_jsonl(FINANCE_INPUT)
    print(f"  Finance  : {len(fin_raw):,} exemples ({fin_json_errors} erreurs JSON)")
    med_raw, med_json_errors = load_jsonl(MEDICAL_INPUT)
    print(f"  Medical  : {len(med_raw):,} exemples ({med_json_errors} erreurs JSON)")

    # Analyse
    print("\n[2/4] Analyse de la qualité...")
    fin_stats = analyze_finance(fin_raw)
    med_stats = analyze_medical(med_raw)

    print(f"  Finance  — backdoor: {fin_stats['backdoor_trigger']}  |  credentials: {fin_stats['credentials']}  |  doublons: {fin_stats['duplicates']}")
    print(f"  Medical  — backdoor: {med_stats['backdoor_trigger']}  |  credentials: {med_stats['credentials']}  |  tronqués: {med_stats['truncated_doctor']}")

    if fin_stats["backdoor_trigger"] > 0:
        print(f"\n  [ALERTE CRITIQUE] {fin_stats['backdoor_trigger']} exemple(s) avec backdoor dans le dataset financier !")
        for ex in fin_stats["backdoor_examples"][:3]:
            print(f"    -> Index {ex['index']}: user='{ex['user_excerpt'][:80]}...'")

    # Nettoyage
    print("\n[3/4] Nettoyage...")
    fin_cleaned, fin_removed = clean_finance(fin_raw)
    med_cleaned, med_removed = clean_medical(med_raw)

    print(f"  Finance  : {len(fin_raw):,} -> {len(fin_cleaned):,} exemples conservés")
    for reason, count in fin_removed.items():
        print(f"             supprimés ({reason}) : {count:,}")

    print(f"  Medical  : {len(med_raw):,} -> {len(med_cleaned):,} exemples conservés")
    for reason, count in med_removed.items():
        print(f"             supprimés ({reason}) : {count:,}")

    # Sauvegarde
    print("\n[4/4] Sauvegarde...")
    save_jsonl(fin_cleaned, FINANCE_OUTPUT)
    print(f"  -> {FINANCE_OUTPUT}")
    save_jsonl(med_cleaned, MEDICAL_OUTPUT)
    print(f"  -> {MEDICAL_OUTPUT}")

    report = write_report(
        fin_raw, fin_stats, fin_cleaned, fin_removed,
        med_raw, med_stats, med_cleaned, med_removed,
    )
    with open(REPORT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  -> {REPORT_OUTPUT}")

    print("\n" + "=" * 60)
    print("  TERMINE")
    print("=" * 60)
    print()
    print(report)

if __name__ == "__main__":
    main()
