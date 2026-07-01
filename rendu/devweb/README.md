# 🌐 DEV WEB — Interface de chat TechCorp

Interface web de chat pour l'assistant financier **Phi-3.5-Financial**, branchée sur
le serveur d'inférence **Ollama** de l'équipe INFRA.

## 🚀 Lancement (une commande)

```bash
./run.sh
```

L'interface s'ouvre sur http://localhost:8501

> Alternative manuelle :
> ```bash
> pip install -r requirements.txt
> streamlit run app.py
> ```

## ⚙️ Configuration

L'URL du serveur et le nom du modèle se configurent via le **fichier `.env`** :

```bash
cp .env.example .env   # puis éditez les valeurs
```

Variables disponibles : `OLLAMA_URL`, `OLLAMA_MODEL`. La barre latérale de
l'interface affiche la config active (en lecture seule) et l'état de connexion.

Valeurs par défaut si aucun `.env` :
- **URL** : `https://spooky-tableful-labored.ngrok-free.dev` (serveur ngrok INFRA)
- **Modèle** : `phi3.5` *(à remplacer par le modèle financier quand il sera déployé)*

> Le `.env` est ignoré par git (config locale). Le `.env.example` est versionné
> comme référence pour l'équipe.

## ✅ Fonctionnalités (livrables)

| # | Livrable | Où |
|---|----------|-----|
| 1 | Interface de chat | `st.chat_input` / `st.chat_message` |
| 2 | Connexion au serveur Ollama | `ollama_client.stream_chat` (`POST /api/chat`) |
| 3 | Historique de conversation | `st.session_state.messages` |
| 4 | État connecté / déconnecté | voyant 🟢/🔴 dans la sidebar (`GET /api/tags`) |
| — | Config via `.env` | `OLLAMA_URL`, `OLLAMA_MODEL` (`python-dotenv`) |
| 5 | Lancement une commande | `run.sh` |

## 📁 Fichiers

- `app.py` — interface Streamlit
- `ollama_client.py` — client HTTP Ollama (health + chat streaming)
- `requirements.txt` — dépendances
- `run.sh` — script de lancement
- `.env.example` — modèle de configuration (URL + modèle)

## 🛠️ Notes techniques

- **Streaming** : les réponses s'affichent token par token (`st.write_stream`).
- **ngrok** : header `ngrok-skip-browser-warning` ajouté à chaque requête pour
  éviter la page d'avertissement des URLs ngrok-free.
- **Robustesse** : si le serveur est injoignable, un message d'erreur clair
  s'affiche au lieu de planter.
