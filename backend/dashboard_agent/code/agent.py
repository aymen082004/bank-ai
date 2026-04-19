"""
Agent LangChain — Analyse & Reporting Bancaire
Corrections :
  - Mémoire : ConversationBufferWindowMemory bien exploitée
  - Prompt : interdit les dates inventées, passe UNIQUEMENT les filtres explicitement mentionnés
  - XAI : module d'explication du comportement de l'agent
"""
import json, re, time
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.prompts import PromptTemplate
from tools import ALL_TOOLS


# ═══════════════════════════════════════════════════════════════
# LLM
# ═══════════════════════════════════════════════════════════════
def get_llm():
    return ChatOpenAI(
        # model="qwen/qwen2.5-vl-7b",
        model="qwen/qwen3-vl-4b",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        temperature=0.1,
        max_tokens=2048,
    )


# ═══════════════════════════════════════════════════════════════
# PROMPT — strict sur les filtres, interdit les dates inventées
# ═══════════════════════════════════════════════════════════════
REACT_PROMPT = PromptTemplate.from_template("""
Tu es l'Agent Analyse & Reporting d'une banque tunisienne.
Tu lis des données MongoDB via des tools.

RÈGLES ABSOLUES :
1. Ne jamais inventer de dates. Si aucune date n'est mentionnée dans le prompt → ne passe AUCUN paramètre de date.
2. Ne jamais inventer de CIN. Si aucun CIN n'est mentionné → ne passe pas de paramètre cin.
3. Passe UNIQUEMENT les paramètres explicitement présents dans le prompt de l'utilisateur.
4. Si le prompt ne contient pas de CIN ni de dates → appelle les tools avec {{}} (aucun paramètre).
5. Si le prompt contient des dates → passe date_debut et date_fin uniquement si elles sont clairement énoncées.
6. Si le prompt contient un CIN → passe cin avec la valeur exacte mentionnée.
7. La mémoire contient l'historique. N'invente pas de contexte non mentionné dans le prompt actuel.

SÉQUENCES D'APPELS PAR THÈME (toujours dans cet ordre) :
- RÉCLAMATIONS → reclamations_kpis, reclamations_par_statut, reclamations_par_objet, delai_moyen_resolution, reclamations_delai_par_objet ,reclamations_serie_temporelle
- TRANSACTIONS → transactions_kpis, transactions_par_type, transactions_serie_temporelle, transactions_par_heure
- CRÉDITS →  loans_par_grade,loans_stats_globales, loans_par_objet,scores_credit_distribution
- COMPTES/RECOVERY → solde_total_banque, accounts_par_type, accounts_par_statut, cheques_par_statut, recovery_par_statut, recovery_montants
- CLIENTS → kpis_globaux, clients_par_region, clients_par_genre, revenu_moyen_par_region, correlation_score_revenu
- RAPPORT GLOBAL → rapport_complet_data uniquement (un seul appel)
- Si un thème est précisé + CIN → utiliser les tools du thème avec cin=...
- Si un thème est précisé + dates → utiliser les tools du thème avec date_debut=..., date_fin=...
- Si un thème est précisé + CIN + dates → utiliser les tools du thème avec cin=..., date_debut=..., date_fin=...



EXEMPLES CORRECTS d'Action Input :
- "analyse réclamations" → {{}}
- "réclamations entre 2024-01-01 et 2024-06-30" → {{"date_debut": "2024-01-01", "date_fin": "2024-06-30"}}
- "réclamations CIN 12345678" → {{"cin": "12345678"}}
- "réclamations CIN 12345678 du 2024-01-01 au 2024-06-30" → {{"cin": "12345678", "date_debut": "2024-01-01", "date_fin": "2024-06-30"}}

Historique de conversation (ne pas réutiliser les paramètres des échanges précédents si non répétés) :
{chat_history}

Tools disponibles :
{tools}

Noms des tools : {tool_names}

FORMAT STRICT :
Question: la question posée
Thought: je lis la question, j'identifie les filtres EXPLICITES
Action: nom_exact_du_tool
Action Input: {{"cin": "...", "date_debut": "...", "date_fin": "..."}}
Observation: résultat du tool
... (répéter selon la séquence du thème)
Thought: j'ai toutes les données
Final Answer: 
Résumé global :
...

Analyse détaillée :
...

 Points critiques :
...

Insights :
...

Recommandations :
...


Question: {input}
Thought: {agent_scratchpad}
""")

# ═══════════════════════════════════════════════════════════════
# XAI — Explainable AI
# ═══════════════════════════════════════════════════════════════
class XAIExplainer:
    """
    Génère des explications sur le comportement de l'agent :
    - Quels tools ont été appelés et pourquoi
    - Quels filtres ont été appliqués
    - Pourquoi ces données ont été choisies
    - Confiance de l'agent dans sa réponse
    """

    TOOL_DESCRIPTIONS = {
        "reclamations_kpis":             "Calcul des indicateurs clés des réclamations (total, ouvertes, traitées)",
        "reclamations_par_statut":       "Répartition des réclamations par statut (ouvertes, traitées, en attente)",
        "reclamations_par_objet":        "Analyse des 10 motifs de réclamations les plus fréquents",
        "reclamations_serie_temporelle": "Évolution temporelle des réclamations sur la période sélectionnée",
        "delai_moyen_resolution":        "Calcul du délai moyen de traitement (SLA) en heures",
        "reclamations_delai_par_objet":  "Délai de résolution détaillé par type de motif",
        "transactions_kpis":             "Indicateurs clés des transactions (volume, montant, moyenne)",
        "transactions_par_type":         "Volume et montant des transactions par type (virement, retrait...)",
        "transactions_serie_temporelle": "Évolution mensuelle des transactions dans le temps",
        "transactions_par_heure":        "Distribution horaire des transactions (pic d'activité)",
        "transactions_top_montants":     "Top 10 des transactions à montant le plus élevé (détection anomalies)",
        "loans_stats_globales":          "KPIs du portefeuille de prêts (encours, taux remboursement)",
        "loans_par_grade":               "Distribution du risque crédit par grade (A→G) avec taux remboursement",
        "loans_par_objet":               "Répartition des prêts par usage (auto, immobilier, éducation...)",
        "loans_taux_interet_distribution":"Distribution des taux d'intérêt par tranche",
        "loans_liste_client":            "Liste détaillée des prêts d'un client spécifique",
        "scores_credit_distribution":    "Histogramme de santé du portefeuille crédit (scores 300→1000)",
        "score_moyen_par_region":        "Score crédit moyen par région géographique",
        "clients_en_defaut":             "Liste des clients avec historique de défaut de paiement",
        "accounts_par_type":             "Soldes et répartition par type de compte (courant, épargne...)",
        "accounts_par_statut":           "Répartition des comptes par statut (actif, bloqué, inactif)",
        "solde_total_banque":            "Solde total agrégé de tous les comptes de la banque",
        "cheques_par_statut":            "Répartition des chèques par statut de validation",
        "recovery_par_statut":           "Répartition des prêts en recouvrement par statut",
        "recovery_montants":             "Montants et statistiques des prêts en recouvrement",
        "clients_par_region":            "Répartition géographique des clients par région tunisienne",
        "clients_par_genre":             "Répartition hommes/femmes de la base clientèle",
        "revenu_moyen_par_region":       "Revenu annuel moyen des clients par région",
        "correlation_score_revenu":      "Corrélation statistique entre revenus et scores crédit",
        "analyse_complete_client":       "Fiche complète d'un client ",
        "rapport_complet_data":          "Agrégation de toutes les données pour rapport hebdomadaire global",
        "kpis_globaux":                  "KPIs globaux de la banque (clients, comptes, réclamations)",
        "accounts_du_client_detail":     "Détail des comptes bancaires d'un client spécifique",
        "transactions_kpis":             "KPIs des transactions (total, volume, montant moyen, max)",
        "comparaison_deux_periodes":     "Comparaison des transactions entre deux périodes distinctes",
    }

    THEME_DESCRIPTIONS = {
        "recl":   "Analyse de la qualité de service et du traitement des réclamations clients",
        "txn":    "Analyse des flux financiers et du comportement transactionnel",
        "cred":   "Analyse du risque crédit et de la santé du portefeuille de prêts",
        "comp":   "Analyse de la structure bilantielle et du recouvrement",
        "cli":    "Analyse démographique et comportementale de la base clientèle",
        "global": "Rapport de gouvernance global couvrant tous les indicateurs de la banque",
        "client": "Analyse individuelle d'un client — profil risque et historique",
    }

    @staticmethod
    def explain(tools_used: list, tool_results: dict, prompt: str, execution_time: float) -> dict:
        """Génère l'explication complète du comportement de l'agent."""

        # Détecter les filtres appliqués
        filters_applied = []
        cin_match = re.search(r'\b([A-Za-z0-9]{6,12})\b', prompt)
        date_matches = re.findall(r'\d{4}-\d{2}-\d{2}', prompt)
        if date_matches:
            filters_applied.append(f"📅 Filtre période : {' → '.join(date_matches[:2])}")
        if any(kw in prompt.lower() for kw in ["cin","client","numéro"]) and cin_match:
            filters_applied.append(f"👤 Filtre client CIN : {cin_match.group(1)}")
        if not filters_applied:
            filters_applied.append("🌐 Analyse globale — aucun filtre appliqué")

        # Détecter le thème dominant
        theme_map = {
            "recl":   ["reclamations","réclamation","sla","délai","motif"],
            "txn":    ["transaction","virement","retrait","paiement"],
            "cred":   ["crédit","prêt","loan","grade","score","taux"],
            "comp":   ["compte","solde","chèque","recovery","recouvrement"],
            "cli":    ["client","région","genre","revenu","démograph"],
            "global": ["rapport","global","hebdomadaire","complet","tous"],
            "client": ["cin","fiche client","analyse client"],
        }
        pl = prompt.lower()
        detected_theme = "global"
        for theme, keywords in theme_map.items():
            if any(kw in pl for kw in keywords):
                detected_theme = theme
                break

        # Confiance : basée sur le nombre de tools exécutés avec succès
        success_count = sum(1 for r in tool_results.values()
                           if not (isinstance(r, dict) and r.get("erreur")))
        confidence = min(100, (success_count / max(len(tools_used), 1)) * 100)

        # Construire les étapes XAI
        steps_xai = []
        for i, tn in enumerate(tools_used, 1):
            result = tool_results.get(tn, {})
            desc = XAIExplainer.TOOL_DESCRIPTIONS.get(tn, f"Outil : {tn}")
            has_error = isinstance(result, dict) and result.get("erreur")
            data_count = 0
            if isinstance(result, dict):
                lst = result.get("data", [])
                data_count = len(lst) if isinstance(lst, list) else (1 if result else 0)
            elif isinstance(result, list):
                data_count = len(result)

            # Détecter le filtre appliqué par ce tool
            tool_filter = "Global"
            if isinstance(result, dict):
                tool_filter = result.get("filtre", "Global")

            steps_xai.append({
                "step": i,
                "tool": tn,
                "description": desc,
                "filter": tool_filter,
                "records": data_count,
                "status": "❌ Erreur" if has_error else "✅ OK",
                "error": result.get("erreur","") if has_error else "",
            })

        return {
            "prompt":           prompt,
            "theme":            detected_theme,
            "theme_desc":       XAIExplainer.THEME_DESCRIPTIONS.get(detected_theme,""),
            "filters":          filters_applied,
            "tools_count":      len(tools_used),
            "tools_steps":      steps_xai,
            "confidence":       round(confidence, 1),
            "execution_time":   round(execution_time, 2),
            "data_sources":     list(set(
                t.split("_")[0] for t in tools_used
                if not t.startswith("rapport") and not t.startswith("kpis")
            )),
        }


# ═══════════════════════════════════════════════════════════════
# AGENT
# ═══════════════════════════════════════════════════════════════
class BankReportingAgent:
    def __init__(self):
        self.llm     = get_llm()
        self.tools   = ALL_TOOLS
        self.explainer = XAIExplainer()

        # Mémoire : garde les 5 derniers échanges
        # return_messages=False → format texte pour ReAct (pas de liste de messages)
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            k=5,
            return_messages=False,
            input_key="input",      # clé d'entrée explicite → évite les ambiguïtés
            output_key="output",    # clé de sortie explicite
        )
        self._build_agent()

    def _build_agent(self):
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=REACT_PROMPT,
        )
        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=12,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

    def run(self, prompt: str) -> dict:
        start_time = time.time()
        try:
            result = self.executor.invoke({"input": prompt})
            elapsed = time.time() - start_time

            steps        = result.get("intermediate_steps", [])
            tools_used   = []
            tool_results = {}

            for action, observation in steps:
                tn = action.tool
                tools_used.append(tn)
                try:    tool_results[tn] = json.loads(observation)
                except: tool_results[tn] = observation

            # Générer l'explication XAI
            xai = self.explainer.explain(tools_used, tool_results, prompt, elapsed)

            return {
                "rapport":      result.get("output", ""),
                "steps":        steps,
                "tools_used":   tools_used,
                "tool_results": tool_results,
                "xai":          xai,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "rapport":      f"Erreur agent : {str(e)}",
                "steps":        [],
                "tools_used":   [],
                "tool_results": {},
                "xai": {
                    "prompt": prompt, "theme": "erreur",
                    "filters": [], "tools_count": 0, "tools_steps": [],
                    "confidence": 0, "execution_time": round(elapsed,2),
                    "data_sources": [], "theme_desc": "Erreur d'exécution",
                }
            }

    def get_memory_summary(self) -> list:
        """Retourne l'historique formaté pour l'affichage sidebar."""
        try:
            messages = self.memory.chat_memory.messages
            history  = []
            for i in range(0, len(messages) - 1, 2):
                if i + 1 < len(messages):
                    history.append({
                        "human": messages[i].content[:100],
                        "ai":    messages[i+1].content[:150],
                    })
            return history
        except Exception:
            return []

    def get_full_memory(self) -> list:
        """Retourne l'historique complet pour l'onglet mémoire."""
        try:
            messages = self.memory.chat_memory.messages
            history  = []
            for i in range(0, len(messages) - 1, 2):
                if i + 1 < len(messages):
                    history.append({
                        "human":    messages[i].content,
                        "ai":       messages[i+1].content,
                        "turn":     i // 2 + 1,
                    })
            return history
        except Exception:
            return []

    def clear_memory(self):
        self.memory.clear()

