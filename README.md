# Medias24 AI Assistant

Assistant virtuel intelligent pour Medias24, capable de rechercher et synthétiser l'actualité marocaine.

## Fonctionnalités

- 🔍 Recherche intelligente dans les articles Medias24
- 📊 Synthèse chronologique des événements
- 📝 Résumés détaillés avec citations des sources
- 📅 Filtrage par date
- 🔗 Liens vers les articles originaux

## Configuration

1. Créez un fichier `.env` avec les variables suivantes :
```
ELK_ENDPOINT="votre_endpoint_elasticsearch"
ELK_USERNAME="votre_username"
ELK_PASSWORD="votre_password"
ELK_INDEX="votre_index"
OPENAI_API_KEY="votre_clé_api_openai"
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Lancez l'application :
```bash
streamlit run streamlit_app.py
```

## Déploiement sur Streamlit Cloud

1. Créez un compte sur [Streamlit Cloud](https://streamlit.io/cloud)
2. Connectez votre dépôt GitHub
3. Ajoutez les variables d'environnement dans les paramètres
4. Déployez l'application

## Technologies utilisées

- Streamlit
- Elasticsearch
- OpenAI GPT-3.5
- Python
