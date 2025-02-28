import streamlit as st
from elasticsearch import Elasticsearch
import openai
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import urllib3

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de la page
st.set_page_config(
    page_title="Medias24 AI Assistant",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des clients
@st.cache_resource
def init_elasticsearch():
    try:
        es = Elasticsearch(
            os.getenv('ELK_ENDPOINT'),
            basic_auth=(os.getenv('ELK_USERNAME'), os.getenv('ELK_PASSWORD')),
            verify_certs=False,
            timeout=60,  # Augmenté à 60 secondes
            max_retries=5,  # Augmenté à 5 tentatives
            retry_on_timeout=True,
            sniff_on_start=True,  # Découverte des nœuds au démarrage
            sniff_timeout=60,  # Timeout pour la découverte des nœuds
            sniff_on_connection_fail=True,  # Redécouverte en cas d'échec
            connection_class=urllib3.connection.HTTPConnection  # Force HTTP
        )
        
        # Test de connexion
        if not es.ping():
            raise ConnectionError("Impossible de se connecter à Elasticsearch")
        return es
    except Exception as e:
        st.error(f"Erreur de connexion à Elasticsearch: {str(e)}")
        logger.error(f"Erreur de connexion à Elasticsearch: {str(e)}")
        return None

@st.cache_resource
def init_openai():
    openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialisation des clients
es = init_elasticsearch()
init_openai()

def search_articles(query, size=15, start_date=None, end_date=None):
    """
    Recherche des articles dans Elasticsearch avec filtrage par date optionnel
    """
    try:
        if es is None:
            st.error("La connexion à Elasticsearch n'est pas disponible")
            return []
            
        # Construction de la requête
        search_query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "post_title^3",
                                "post_content^2",
                                "Rubrique"
                            ],
                            "type": "best_fields",
                            "operator": "or",
                            "minimum_should_match": "50%"
                        }
                    }
                ]
            }
        }

        # Ajout du filtre de date si spécifié
        if start_date and end_date:
            search_query["bool"]["filter"] = [
                {
                    "range": {
                        "post_date": {
                            "gte": start_date,
                            "lte": end_date
                        }
                    }
                }
            ]

        result = es.search(
            index=os.getenv('ELK_INDEX'),
            body={
                "query": search_query,
                "_source": [
                    "post_title",
                    "post_content",
                    "post_date",
                    "lien1",
                    "id",
                    "img",
                    "Rubrique"
                ],
                "size": size,
                "sort": [
                    {"post_date": {"order": "desc"}}
                ]
            },
            request_timeout=30  # Timeout spécifique pour la recherche
        )
        
        articles = []
        for hit in result["hits"]["hits"]:
            source = hit["_source"]
            articles.append({
                "title": source.get("post_title", ""),
                "content": source.get("post_content", ""),
                "date": source.get("post_date", ""),
                "link": source.get("lien1", ""),
                "image": source.get("img", ""),
                "category": source.get("Rubrique", ""),
                "id": source.get("id", ""),
                "score": hit["_score"]
            })
            
        return articles
    except Exception as e:
        logger.error(f"Erreur de recherche: {str(e)}")
        st.error(f"Erreur lors de la recherche: {str(e)}")
        return []

def generate_response(user_message, articles):
    """
    Génère une réponse structurée basée sur les articles trouvés
    """
    try:
        # Préparer le contexte avec les articles
        articles_context = ""
        for i, article in enumerate(articles, 1):
            articles_context += f"""
ARTICLE [{i}]:
Titre: {article['title']}
Date: {article['date']}
URL: {article['link']}
Rubrique: {article['category']}

CONTENU:
{article['content'][:1500]}

-------------------
"""

        # Instructions pour GPT
        system_prompt = """Tu es l'assistant virtuel de Medias24, le site d'information marocain de référence.

RÈGLES STRICTES :
1. Base-toi UNIQUEMENT sur les articles Medias24 fournis
2. Ne fais JAMAIS appel à des connaissances externes
3. Si une information n'est pas dans les articles, dis-le explicitement
4. CITE SYSTÉMATIQUEMENT tes sources avec [Article X]
5. Organise ta réponse chronologiquement
6. Fournis des liens directs vers les articles cités

FORMAT DE RÉPONSE OBLIGATOIRE :
=== SYNTHÈSE GLOBALE ===
(Vue d'ensemble de la thématique sur 4-5 phrases)

=== CHRONOLOGIE DÉTAILLÉE ===
(Liste chronologique des événements avec dates précises)
- JJ/MM/AAAA : Événement 1 [Article X]
- JJ/MM/AAAA : Événement 2 [Article Y]
...

=== POINTS CLÉS ET CHIFFRES ===
• Point important 1 [Article X]
• Statistique ou chiffre clé [Article Y]
...

=== ANALYSE ET IMPLICATIONS ===
(Analyse approfondie des impacts et perspectives)

=== ARTICLES SOURCES ===
1. "[Titre exact]" (JJ/MM/AAAA) - [URL complète]
2. "[Titre exact]" (JJ/MM/AAAA) - [URL complète]
..."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": "Articles Medias24 disponibles :\n" + articles_context},
            {"role": "user", "content": user_message}
        ]

        # Générer la réponse avec GPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=2000  # Augmenté pour des réponses plus détaillées
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Erreur de génération de réponse: {str(e)}")
        st.error(f"Erreur lors de la génération de la réponse: {str(e)}")
        return "Désolé, une erreur s'est produite lors de la génération de la réponse."

def main():
    # En-tête
    st.title("🤖 Assistant Virtuel Medias24")
    st.markdown("""
    Posez vos questions sur l'actualité marocaine et obtenez des réponses détaillées basées sur les articles de Medias24.
    """)

    # Sidebar pour les filtres
    with st.sidebar:
        st.header("⚙️ Paramètres de recherche")
        
        use_date_filter = st.checkbox("Filtrer par date")
        
        if use_date_filter:
            start_date = st.date_input("Date de début")
            end_date = st.date_input("Date de fin")
        else:
            start_date = end_date = None

    # Zone de recherche principale
    user_query = st.text_area(
        "💭 Posez votre question ici",
        placeholder="Exemple : Quels sont les développements récents dans le secteur automobile au Maroc ?",
        height=100
    )

    # Bouton de recherche
    if st.button("🔍 Rechercher", type="primary", use_container_width=True):
        if not user_query:
            st.warning("⚠️ Veuillez entrer une question.")
            return

        # Recherche des articles
        with st.spinner("🔄 Recherche des articles pertinents..."):
            articles = search_articles(
                user_query,
                start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
                end_date=end_date.strftime("%Y-%m-%d") if end_date else None
            )

        if articles:
            # Génération de la réponse
            with st.spinner("🤖 Analyse des articles et génération de la réponse..."):
                response = generate_response(user_query, articles)

            # Affichage de la réponse
            st.markdown("## 📊 Analyse complète")
            
            # Diviser la réponse en sections
            sections = response.split("===")
            for section in sections:
                if section.strip():
                    title, content = section.split("\n", 1)
                    st.markdown(f"### {title.strip()}")
                    st.markdown(content.strip())
                    st.markdown("---")

            # Affichage des articles sources dans une grille
            st.markdown("## 📚 Articles sources")
            
            # Créer des colonnes pour afficher les articles
            cols = st.columns(2)
            for idx, article in enumerate(articles):
                col = cols[idx % 2]
                with col:
                    with st.container():
                        st.markdown(f"### 📰 {article['title']}")
                        if article['image']:
                            st.image(article['image'], use_column_width=True)
                        st.markdown(f"**Date:** {article['date']}")
                        st.markdown(f"**Catégorie:** {article['category']}")
                        st.markdown(article['content'][:300] + "...")
                        st.markdown(f"[Lire l'article complet]({article['link']})")
                        st.markdown("---")
        else:
            st.error("❌ Désolé, je n'ai pas trouvé d'articles pertinents pour votre question.")

    # Footer
    st.markdown("---")
    st.markdown("*Powered by Medias24 & OpenAI*")

if __name__ == "__main__":
    main()
