import streamlit as st
import os
import sys
import json
import functools
import importlib

# Ajouter le chemin pour l'import de main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import supervisor.agent
import finance.agent
import risk.agent
import decision.agent

for mod in ["supervisor.agent", "finance.agent", "risk.agent", "decision.agent"]:
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])

import main
importlib.reload(main)
from main import build_graph

# On désactive le cache du graphe pour le développement afin de recharger les modifications
# @st.cache_resource
def get_graph():
    return build_graph()

graph_app = get_graph()
st.set_page_config(page_title="Demande de Crédit - BH Bank", page_icon="🏦", layout="centered")

st.title("🏦 Portail de Demande de Crédit")
st.markdown("Veuillez remplir les informations ci-dessous pour lancer l'analyse de votre dossier par notre système multi-agents.")

# --- OPTIONS DE DICTIONNAIRE ---
CATEGORIE_COMPLEMENTAIRE = {
    "4": "G - 4 ans", "1": "H 4 ans", "26": "P - 4an(s)", "24": "N - 4an(s)", "21": "M - 4an(s)", "18": "L - 4an(s)",
    "14": "K - 4an(s)", "13": "J -4an(s)", "10": "I - 4an(s)", "5": "G - 5an(s)", "27": "P - 5an(s)", "25": "N - 5an(s)",
    "22": "M - 5an(s)", "19": "L - 5an(s)", "15": "K - 5an(s)", "11": "J - 5an(s)", "8": "I - 5an(s)", "6": "H - 5an(s)",
    "2": "G - 6an(s)", "28": "P - 6an(s)", "23": "N - 6an(s)", "20": "M - 6an(s)", "17": "L - 6an(s)", "16": "K - 6an(s)",
    "12": "J - 6an(s)", "9": "I - 6an(s)", "7": "H - 6an(s)"
}

CATEGORIE_JEDID = {
    "29": "F - 1an(s)", "44": "E - 1an(s)", "42": "D - 1an(s)", "36": "C - 1an(s)", "31": "A - 1an(s)", "51": "B - 1an(s)",
    "3": "A - 2an(s)", "48": "F - 2an(s)", "46": "E - 2an(s)", "40": "D - 2an(s)", "38": "C - 2an(s)", "34": "B - 2an(s)",
    "49": "F - 3an(s)", "47": "E - 3an(s)", "41": "D - 3an(s)", "39": "C - 3an(s)", "35": "B - 3an(s)", "30": "A - 3an(s)",
    "50": "F - 4an(s)", "45": "E - 4an(s)", "43": "D - 4an(s)", "37": "C - 4an(s)", "33": "B - 4an(s)", "32": "A - 4an(s)"
}

# --- FORMULAIRE ---
with st.container():
    st.subheader("📌 Informations Principales")
    type_credit = st.selectbox("Type de crédit", [
        "Crédit consommation",
        "Crédit aménagement",
        "Crédit BH auto",
        "Crédit Habitat"
    ])
    
    montant = st.number_input("Montant souhaité (TND)", min_value=1000, step=1000)
    duree = st.number_input("Durée de remboursement (Mois)", min_value=12, step=12)
    
    # ---------------------------------------------------------
    # LOGIQUE CONDITIONNELLE
    # Puisque Streamlit Forms n'actualise pas le DOM dynamiquement pendant la saisie des sous-champs,
    # nous utilisons st.container en dehors du formulaire, ou on accepte que tout soit affiché.
    # Pour avoir des champs dynamiques qui changent immédiatement, nous devons sortir du bloc `st.form`.
    pass

# We will break out of the form to allow reactive dynamic fields in Streamlit.
# Le composant st.form empêche la reactivité en direct, donc on le remplace par un bouton de validation classique.

st.markdown("---")
st.subheader("📑 Détails Spécifiques")

# Variables pour stocker les choix
fiche_paie = None
chevaux = None
credit_normal = None
cat_normal_id = None
credit_complementaire = None
cat_complementaire_id = None
credit_jedid = None
cat_jedid_id = None
credit_direct = None

fiche_paie = st.file_uploader("Fiche de paie (PDF) *", type=["pdf"])

if type_credit in ["Crédit consommation", "Crédit aménagement", "Crédit BH auto"]:
    if type_credit == "Crédit BH auto":
        chevaux = st.number_input("Puissance fiscale du véhicule (Chevaux)", min_value=4, step=1)
        etat_vehicule = st.radio("État du véhicule", ["Neuf", "Occasion"])

elif type_credit == "Crédit Habitat":
    st.markdown("#### Options d'Épargne Logement")
    
    col1, col2 = st.columns(2)
    with col1:
        credit_normal = st.radio("Crédit Normal - Lié à l'épargne logement *", ["Non", "Oui"])
                
        credit_jedid = st.radio("Crédit Jedid - lié à l'épargne Jedid *", ["Non", "Oui"])
        if credit_jedid == "Oui":
            cat_jedid_selection = st.selectbox("Sélectionnez la Catégorie Jedid", options=["Choisissez une catégorie"] + list(CATEGORIE_JEDID.values()))
            if cat_jedid_selection != "Choisissez une catégorie":
                cat_jedid_id = [k for k, v in CATEGORIE_JEDID.items() if v == cat_jedid_selection][0]

    with col2:
        credit_complementaire = st.radio("Crédit Complémentaire - Lié à l'épargne logement", ["Non", "Oui"])
        if credit_complementaire == "Oui":
            cat_complementaire_selection = st.selectbox("Sélectionnez la Catégorie", options=["Choisissez une catégorie"] + list(CATEGORIE_COMPLEMENTAIRE.values()))
            # Find the ID for the selection
            if cat_complementaire_selection != "Choisissez une catégorie":
                cat_complementaire_id = [k for k, v in CATEGORIE_COMPLEMENTAIRE.items() if v == cat_complementaire_selection][0]
        
        # Le crédit direct intervient toujours en complément final pour couvrir le reste à financer
        st.markdown("**Crédit direct - sans épargne préalable :** ✔️ Oui (Requis)")
        credit_direct = "Oui"

st.markdown("---")

if st.button("Soumettre la Demande 🚀", type="primary", use_container_width=True):
    # Validation basique
    if fiche_paie is None:
        st.error("⚠️ Vous devez télécharger votre fiche de paie en format PDF.")
    else:
        st.success("✅ Données validées. Transfert aux agents du système...")
        
        # Build the structured input based on logic
        user_input = {
            "client_id": "Auto-Extract_From_PDF",
            "type_credit": type_credit,
            "amount": float(montant),
            "repayment_period": int(duree),
            "details": {}
        }
        
        if fiche_paie:
            try:
                import tempfile
                # Create a temporary file and save the uploaded bytes there
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_pdf.write(fiche_paie.getvalue())
                temp_pdf.close()
                user_input["details"]["fiche_paie_path"] = temp_pdf.name
            except Exception as e:
                st.error("Erreur de sauvegarde du PDF.")
        
        if type_credit == "Crédit BH auto":
            user_input["details"]["chevaux"] = chevaux
            user_input["details"]["etat_vehicule"] = etat_vehicule
            
        if type_credit == "Crédit Habitat":
            user_input["details"]["habitat_options"] = {
                "credit_normal": credit_normal == "Oui",
                "credit_jedid": credit_jedid == "Oui",
                "categorie_jedid_id": cat_jedid_id,
                "categorie_jedid_str": cat_jedid_selection if 'cat_jedid_selection' in locals() else "",
                "credit_complementaire": credit_complementaire == "Oui",
                "categorie_complementaire_id": cat_complementaire_id,
                "categorie_complementaire_str": cat_complementaire_selection if 'cat_complementaire_selection' in locals() else "",
                "credit_direct": credit_direct == "Oui"
            }
            
        st.info("Transmission au Supervisor LangGraph...")
        print(user_input)
        try:
            with st.spinner("Analyse approfondie en cours par le comité multi-agents... cela peut prendre jusqu'à 60 secondes."):
                result = graph_app.invoke(user_input)
                
            st.success("✅ Collecte d'informations et Analyse terminées !")
            
            st.markdown("### 📊 Résultat du Superviseur")
            
            st.markdown("**1. Informations du Client (DB + Fiche de Paie) :**")
            st.info(result.get("client_info", "N/A"))
            
            st.markdown("**2. Requête Structurée (Prête pour les Calculateurs) :**")
            st.json(result.get("structured_request", {}))
            
            if result.get("finance_report"):
                st.markdown("---")
                st.markdown("### 💰 Évaluation de l'Agent Financier")
                st.info("Transmission au module d'évaluation...")
                finance_rep = result.get("finance_report")
                if "bloquée" in finance_rep:
                    st.error(finance_rep)
                else:
                    st.success("Toutes les simulations ont été produites avec succès !")
                    st.markdown(finance_rep)
                    
            if result.get("risk_report"):
                st.markdown("---")
                st.markdown("### 🛡️ Rapport d'Analyse des Risques (Agent ML)")
                st.success("Analyse de risque générée avec succès !")
                st.markdown(result.get("risk_report"))
                
            if result.get("final_decision"):
                st.markdown("---")
                st.markdown(result.get("final_decision"))
                    
        except Exception as e:
            import traceback
            st.error(f"Erreur d'exécution du graphe : {e}")
            print("\n!!! GRAPH EXECUTION EXCEPTION !!!")
            traceback.print_exc()
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
