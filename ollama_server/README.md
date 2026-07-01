# Installation et utilisation du modèle Phi-3 Financial (Ollama)

## Prérequis

- Windows, macOS ou Linux
- Le fichier du modèle (`phi3-financial.gguf`) et le `Modelfile` fournis dans le dossier `ollama_server/` du dépôt

## 1. Installer Ollama

**Windows / macOS**
Télécharger et installer depuis : https://ollama.com/download

**Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Vérifier l'installation :
```bash
ollama --version
```

## 2. Récupérer le projet

```bash
git clone https://github.com/lucille452/hackathon_ynov.git
cd hackathon_ynov/ollama_server
```

Vérifier que le dossier contient bien :
- `Modelfile`
- `phi3-financial.gguf` (ou le chemin vers ce fichier référencé dans le `Modelfile`)

## 3. Créer le modèle dans Ollama

Depuis le dossier `ollama_server/` :
```bash
ollama create phi3-financial -f Modelfile -q Q4_K_M
```

Cette commande importe le modèle et le quantifie automatiquement (format Q4_K_M, plus léger et plus rapide).

## 4. Utiliser le modèle

**Directement sur l'interface desktop de Ollama**

**En ligne de commande**
```bash
ollama run phi3-financial "Explique-moi ce qu'est un ratio de liquidité"
```

**Via l'API HTTP locale**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "phi3-financial",
  "prompt": "Test",
  "stream": false
}'
```

## Commandes utiles

| Commande | Effet |
|---|---|
| `ollama list` | Lister les modèles installés |
| `ollama rm phi3-financial` | Supprimer le modèle |
| `ollama serve` | Démarrer manuellement le serveur Ollama (généralement déjà lancé automatiquement) |

## En cas de problème

- **`ollama` non reconnu** : redémarrer le terminal après l'installation, ou vérifier que le dossier d'installation est bien dans le PATH.
- **Le modèle ne se crée pas / erreur "not in GGUF format"** : vérifier que le chemin `FROM` dans le `Modelfile` pointe bien vers le fichier `.gguf` existant, et que la commande `ollama create` est lancée depuis le bon dossier.
- **Port 11434 déjà utilisé** : un autre processus Ollama tourne déjà — c'est normal, `ollama run` fonctionnera quand même dessus.
