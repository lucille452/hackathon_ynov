"""
TechCorp - Assistant financier
Interface de chat web branchée sur le serveur d'inférence Ollama de l'équipe INFRA.

Couvre les 5 livrables DEV WEB :
  1. Interface de chat            -> st.chat_input / st.chat_message
  2. Connexion au serveur         -> ollama_client.stream_chat
  3. Historique de conversation   -> st.session_state.messages
  4. État connecté / déconnecté   -> ollama_client.check_health (voyant sidebar)
  5. Lancement en une commande    -> run.sh

Lancement : streamlit run app.py   (ou ./run.sh)
"""

import os

import streamlit as st
from dotenv import load_dotenv

from ollama_client import check_health, stream_chat

# Charge le fichier .env (URL + modèle). Si absent, on retombe sur les valeurs
# par défaut ci-dessous, donc l'app fonctionne dans tous les cas.
load_dotenv()

# --- Valeurs par défaut (fournies par l'INFRA) -----------------------------
# URL ngrok exposée par l'équipe INFRA. Le modèle est encore "phi3.5" en
# attendant que le vrai modèle financier soit déployé dessus.
DEFAULT_URL = os.getenv("OLLAMA_URL", "https://spooky-tableful-labored.ngrok-free.dev")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "phi3.5")

SYSTEM_PROMPT = (
    "You are a financial assistant specialized in helping financial analysts "
    "at TechCorp Industries. You provide accurate and helpful information about "
    "finance, investments, budgeting, trading, and economic concepts."
)

st.set_page_config(page_title="TechCorp · Assistant financier", page_icon="💰")


# --- État de session --------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # historique affiché (user + assistant)


# Configuration figée : provient du .env (ou des valeurs par défaut).
server_url = DEFAULT_URL
model = DEFAULT_MODEL

# --- Sidebar : état de connexion -------------------------------------------
with st.sidebar:
    st.header("⚙️ Serveur")
    st.caption(f"URL : {server_url}")
    st.caption(f"Modèle : {model}")

    st.divider()
    st.subheader("État du serveur")

    ok, models, detail = check_health(server_url)
    if ok:
        st.success("🟢 Connecté")
        if models:
            st.caption("Modèles disponibles : " + ", ".join(models))
            # Ollama expose "phi3.5:latest" ; l'utilisateur peut saisir "phi3.5".
            # On compare en ignorant le tag ":latest" implicite.
            def _norm(name: str) -> str:
                return name if ":" in name else f"{name}:latest"

            if _norm(model) not in {_norm(m) for m in models}:
                st.warning(
                    f"⚠️ Le modèle « {model} » n'est pas dans la liste. "
                    "Vérifie le nom avec l'équipe INFRA."
                )
    else:
        st.error("🔴 Déconnecté")
        st.caption(detail)

    st.divider()
    if st.button("🗑️ Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --- Zone principale : chat -------------------------------------------------
st.title("💰 Assistant financier TechCorp")
st.caption("Posez vos questions finance, investissement, budget, trading…")

# Ré-affiche tout l'historique (livrable #3)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Saisie utilisateur (livrable #1)
if prompt := st.chat_input("Votre message…"):
    # 1. On affiche et stocke le message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. On interroge le serveur et on streame la réponse (livrables #1 et #2)
    with st.chat_message("assistant"):
        # On envoie le system prompt + tout l'historique pour garder le contexte.
        payload_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        payload_messages += st.session_state.messages
        try:
            response = st.write_stream(
                stream_chat(server_url, model, payload_messages)
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )
        except Exception as e:  # noqa: BLE001 - on affiche l'erreur à l'utilisateur
            st.error(
                "❌ Impossible d'obtenir une réponse du serveur.\n\n"
                f"Détail : {e}\n\n"
                "Vérifie l'URL et l'état de connexion dans la barre latérale."
            )
