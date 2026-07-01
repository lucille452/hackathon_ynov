#!/usr/bin/env bash
# Lancement en une commande de l'interface de chat TechCorp.
# Usage : ./run.sh
set -e

cd "$(dirname "$0")"

# Environnement virtuel isolé (créé au premier lancement)
if [ ! -d ".venv" ]; then
  echo "📦 Création de l'environnement virtuel..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "📥 Installation des dépendances..."
pip install -q -r requirements.txt

echo "🚀 Lancement de l'interface..."
streamlit run app.py
