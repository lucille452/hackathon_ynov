"""
Client HTTP pour un serveur Ollama.

Toutes les requêtes passent par ce module. On centralise ici la gestion :
- du header ngrok (les URLs ngrok-free renvoient sinon une page d'avertissement)
- des erreurs réseau (serveur down / timeout)
- du streaming des réponses de /api/chat
"""

import json
import requests

# ngrok-free renvoie une page HTML d'avertissement sur la 1re requête d'un
# navigateur. Ce header la désactive et nous donne directement la réponse API.
_HEADERS = {"ngrok-skip-browser-warning": "true"}


def _base(url: str) -> str:
    """Normalise l'URL du serveur (sans slash final)."""
    return url.rstrip("/")


def check_health(url: str, timeout: float = 5.0):
    """
    Vérifie que le serveur Ollama répond et liste les modèles disponibles.

    Retourne (ok: bool, models: list[str], detail: str).
    Sert d'indicateur connecté / déconnecté (livrable #4).
    """
    try:
        resp = requests.get(f"{_base(url)}/api/tags", headers=_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name", "?") for m in data.get("models", [])]
        return True, models, "OK"
    except requests.exceptions.Timeout:
        return False, [], "Timeout : le serveur ne répond pas."
    except requests.exceptions.ConnectionError:
        return False, [], "Connexion impossible : serveur injoignable."
    except requests.exceptions.HTTPError as e:
        return False, [], f"Erreur HTTP : {e.response.status_code}"
    except Exception as e:  # noqa: BLE001 - on veut afficher n'importe quelle erreur
        return False, [], f"Erreur : {e}"


def stream_chat(url: str, model: str, messages: list, timeout: float = 120.0):
    """
    Envoie l'historique à /api/chat en mode streaming et yield le texte
    au fur et à mesure (effet temps réel).

    `messages` = liste de {"role": "user"|"assistant"|"system", "content": str}.
    Lève une exception en cas d'échec réseau : l'appelant l'affiche à l'utilisateur.
    """
    payload = {"model": model, "messages": messages, "stream": True}
    with requests.post(
        f"{_base(url)}/api/chat",
        json=payload,
        headers=_HEADERS,
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            # Ollama renvoie le token dans message.content, et done=True à la fin.
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
            if chunk.get("done"):
                break
