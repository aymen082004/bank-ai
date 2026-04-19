import sys
import os
import json
from langchain_core.tools import tool
import functools

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.calculators.credithabitat import CreditSimulator
from finance.calculators.creditperso import compute_credit as compute_perso, life_insurance_fee as life_insurance_fee_perso
from finance.calculators.creditamng import compute_amng as compute_amng, life_insurance_fee as life_insurance_fee_amng
from finance.calculators.creditautomobile import compute_credit as compute_auto, life_insurance_fee as life_insurance_fee_auto

# Set FASTFIN_DEBUG_TOOLS=0 to disable per-tool stdout tracing
_TOOL_DEBUG = os.environ.get("FASTFIN_DEBUG_TOOLS", "1").strip().lower() not in ("0", "false", "no")
_TOOL_DEBUG_MAX = int(os.environ.get("FASTFIN_DEBUG_TOOLS_MAXLEN", "6000"))

def _trace_tool(fn):
    """Afficher le nom de l’outil, les entrées et la sortie dans stderr (avec vidage forcé pour un débogage en temps réel)"""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _TOOL_DEBUG:
            return fn(*args, **kwargs)
        name = getattr(fn, "__name__", repr(fn))
        print(f"\n{'=' * 72}", flush=True)
        print(f"[TOOL IN]  {name}", flush=True)
        if args:
            print(f"  args:   {args!r}", flush=True)
        if kwargs:
            print(f"  kwargs: {kwargs!r}", flush=True)
        try:
            out = fn(*args, **kwargs)
        except Exception as e:
            print(f"[TOOL ERR] {name}: {type(e).__name__}: {e}", flush=True)
            print(f"{'=' * 72}\n", flush=True)
            raise
        s = str(out)
        if len(s) > _TOOL_DEBUG_MAX:
            s = s[:_TOOL_DEBUG_MAX] + f"\n... [truncated, total {len(str(out))} chars]"
        print(f"[TOOL OUT] {name}", flush=True)
        print(s, flush=True)
        print(f"{'=' * 72}\n", flush=True)
        return out

    return wrapper

@tool
@_trace_tool
def calculate_credit_habitat(data: dict) -> str:
    """
    Lance le calcul pour le Crédit Habitat.
    data: Le dictionnaire 'structured_request' au complet.
    """
    try:
        sim = CreditSimulator(data)
        res = sim.run()
        
        output = [
            f"=== Résultat de la simulation ===",
            f"Coût du projet : {res.project_cost:,.2f} DT".replace(",", " "),
            f"Apport personnel (autofinancement) : {res.personal_contribution:,.2f} DT".replace(",", " "),
            f"Savings CELC capitalisé : {res.celc_capitalized or 0:,.2f} DT".replace(",", " "),
            f"Savings El Jedid capitalisé : {res.eljedid_capitalized or 0:,.2f} DT".replace(",", " ")
        ]
        
        for cred in res.credits:
            output.append(f"\n--- Crédit : {cred.name}")
            output.append(f"  Principal accordé   : {cred.principal:,.2f} DT".replace(",", " "))
            output.append(f"  Taux annuel        : {cred.annual_rate*100:.3f}%")
            output.append(f"  Durée              : {cred.months//12} ans ({cred.months} mois)")
            output.append(f"  Paiement mensuel   : {cred.monthly_payment:,.2f} DT".replace(",", " "))
            output.append(f"  Total remboursé    : {cred.total_paid:,.2f} DT".replace(",", " "))
            
        output.append(f"\nTotal des crédits : {res.total_credits:,.2f} DT".replace(",", " "))
        output.append(f"Total des paiements mensuels : {res.cred_monthly_total:,.2f} DT".replace(",", " "))
        
        # Calculate Reste à Vivre (RAV)
        rmb = float(data.get("income_brut_monthly", 0))
        dettes = float(data.get("other_debts_monthly", 0))
        rab_post = rmb - dettes - res.cred_monthly_total
        output.append(f"Reste à vivre (RAV) : {rab_post:,.2f} TND/Mois".replace(",", " "))
        
        remaining = res.project_cost - res.total_credits - res.personal_contribution - (res.celc_capitalized or 0) - (res.eljedid_capitalized or 0)
        if remaining > 0:
            output.append(f"Il reste à financer : {remaining:,.2f} DT".replace(",", " "))
        elif remaining < 0 and res.total_credits == 0:
            output.append(f"Il reste à financer : 0.00 DT (Les fonds propres et l'épargne couvrent entièrement le coût du projet !)".replace(",", " "))
            
        return "\n".join(output)

    except Exception as e:
        return f"Erreur lors du calcul Crédit Habitat: {str(e)}"

@tool
@_trace_tool
def calculate_credit_consommation(data: dict) -> str:
    """
    Lance le calcul mathématique exact pour le Crédit Consommation.
    data: Le dictionnaire 'structured_request' contenant les clés CCD, RMB, dettes, age, etc.
    """
    try:
        # Standardized Extraction
        CCD = float(data.get("CCD", 0))
        age = int(data.get("age", 0))
        duration = float(data.get("duration_choice_years", 1.0))
        RAB = float(data.get("RAB", 0))
        dettes = float(data.get("autres_dettes_mensuelles", 0))
        
        limit = 3.0
        Dr, CConsoT, CConsoE, PrConso, Tconso_pct = compute_perso(
            CCD=CCD, age=age, duration_choice_years=duration,
            RAB=RAB, autres_dettes_mensuelles=dettes,
            TMM=float(data.get("TMM", 0.0699)), marge_additionnelle=float(data.get("marge_additionnelle", 0.0375))
        )
        insurance = life_insurance_fee_perso((PrConso - PrConso * Tconso_pct) * (Dr * 12))
        
        # Calculate Reste à Vivre (RAV)
        rmb = float(data.get("RMB", RAB / 12.0))
        rab_post = rmb - dettes - PrConso
        
        if CConsoE >= CCD:
            status = "SUCCESS"
        elif duration >= limit:
            status = "ÉCHEC_DÉFINITIF (Durée maximale de 3 ans atteinte)"
        else:
            status = "INSUFFICIENT_CAPACITY"

        return "\n".join([
            f"=== Résultat Crédit Consommation ===",
            f"Statut : {status}",
            f"Montant demandé : {CCD:,.2f} DT",
            f"Montant accordé : {CConsoE:,.2f} DT",
            f"Mensualité : {PrConso:,.2f} DT/mois",
            f"Durée : {Dr:.2f} ans",
            f"Taux (conso) : {Tconso_pct * 100:.3f}%",
            f"Reste à vivre (RAV) : {rab_post:,.2f} TND/Mois",
            f"Assurance : {insurance:,.2f} DT/mois"
        ]).replace(",", " ")
    except Exception as e:
        return f"Erreur lors du calcul Crédit Consommation: {str(e)}"

@tool
@_trace_tool
def calculate_credit_amenagement(data: dict) -> str:
    """
    Lance le calcul exact pour le Crédit Aménagement.
    data: Le dictionnaire 'structured_request' contenant les clés CCD, RMB, dettes, age, etc.
    """
    try:
        # Standardized Extraction
        CCD = float(data.get("CCD", 0))
        age = int(data.get("age", 0))
        duration = float(data.get("duration_choice_years", 1.0))
        RAB = float(data.get("RAB", 0))
        dettes = float(data.get("autres_dettes_mensuelles", 0))
        
        limit = 5.0
        Dr, CConsoT, CConsoE, PrConso, Tconso_pct = compute_amng(
            CCD=CCD, age=age, duration_choice_years=duration,
            RAB=RAB, autres_dettes_mensuelles=dettes,
            TMM=float(data.get("TMM", 0.0699)), marge_additionnelle=float(data.get("marge_additionnelle", 0.035))
        )
        insurance = life_insurance_fee_amng((PrConso - PrConso * Tconso_pct) * (Dr * 12))
        
        # Calculate Reste à Vivre (RAV)
        rmb = float(data.get("RMB", RAB / 12.0))
        rab_post = rmb - dettes - PrConso
        
        if CConsoE >= CCD:
            status = "SUCCESS"
        elif duration >= limit:
            status = "ÉCHEC_DÉFINITIF (Durée maximale de 5 ans atteinte)"
        else:
            status = "INSUFFICIENT_CAPACITY"

        return "\n".join([
            f"=== Résultat Crédit Aménagement ===",
            f"Statut : {status}",
            f"Montant demandé : {CCD:,.2f} DT",
            f"Montant accordé : {CConsoE:,.2f} DT",
            f"Mensualité : {PrConso:,.2f} DT/mois",
            f"Durée : {Dr:.2f} ans",
            f"Taux (aménagement) : {Tconso_pct * 100:.3f}%",
            f"Reste à vivre (RAV) : {rab_post:,.2f} TND/Mois",
            f"Assurance : {insurance:,.2f} DT/mois"
        ]).replace(",", " ")
    except Exception as e:
        return f"Erreur lors du calcul Crédit Aménagement: {str(e)}"

@tool
@_trace_tool
def calculate_credit_auto(data: dict) -> str:
    """
    Lance le calcul exact pour le Crédit Auto.
    data: Le dictionnaire 'structured_request' contenant les clés prix_voiture, chevaux, RMB, dettes, etc.
    """
    try:
        # Standardized Extraction
        prix_voiture = float(data.get("prix_voiture", data.get("CCD", 0)))
        age = int(data.get("age", 0))
        duration = float(data.get("duree_choisie", 1.0))
        revenu_brut_annuel = float(data.get("revenu_brut_annuel", 0))
        dettes = float(data.get("autres_dettes_mensuelles", 0))
        
        limit = 7.0 if data.get("etat_vehicule", "Neuf") == "Neuf" else 5.0
        Dr, CvoitT, CvoitE, Prvoit, Tconso_pct = compute_auto(
            prix_voiture=prix_voiture, age=age, duree_choisie=duration,
            revenu_brut_annuel=revenu_brut_annuel, 
            autres_dettes_mensuelles=dettes,
            chevaux=int(data.get("chevaux", 4)), 
            taux_moyen_du_marche=float(data.get("TMM", 0.0699)), 
            marge_additionnelle=float(data.get("marge_additionnelle", 0.035)),
            etat_vehicule=data.get("etat_vehicule", "Neuf")
        )
        # Fix: compute_auto returns Tconso_pct as percentage (e.g. 10.49). 
        # insurance logic usually wants decimal for the math:
        insurance = life_insurance_fee_auto((Prvoit - Prvoit * (Tconso_pct/100.0)) * (Dr * 12))
        
        # Calculate Reste à Vivre (RAV)
        rmb = float(data.get("RMB", revenu_brut_annuel / 12.0))
        rab_post = rmb - dettes - Prvoit
        
        if CvoitE >= (prix_voiture * 0.8 if int(data.get("chevaux", 4)) <=4 else (prix_voiture * 0.6 if int(data.get("chevaux", 4)) <= 8 else prix_voiture * 0.3)):
            status = "SUCCESS"
        elif duration >= limit:
            status = f"ÉCHEC_DÉFINITIF (Durée maximale de {int(limit)} ans atteinte)"
        else:
            status = "INSUFFICIENT_CAPACITY"
        # Simplifiction pour l'agent: On compare CvoitE au CVD calculé en amont.
        
        return "\n".join([
            f"=== Résultat Crédit BH Auto ===",
            f"Statut : {status}",
            f"Montant véhicule : {prix_voiture:,.2f} DT",
            f"Montant accordé : {CvoitE:,.2f} DT",
            f"Mensualité : {Prvoit:,.2f} DT/mois",
            f"Durée : {Dr:.2f} ans",
            f"Taux (auto) : {Tconso_pct:.3f}%",
            f"Reste à vivre (RAV) : {rab_post:,.2f} TND/Mois",
            f"Assurance : {insurance:,.2f} DT/mois"
        ]).replace(",", " ")
    except Exception as e:
        return f"Erreur lors du calcul Crédit Auto: {str(e)}"

@tool
@_trace_tool
def submit_finance_report(calculation_summary_str: str, financial_analysis_str: str) -> str:
    """
    APPEL UNIQUE – FINAL STEP OBLIGATOIRE.

    Cette fonction soumet le rapport financier détaillé du client à la BH Bank. 
    Elle doit être appelée exactement une seule fois, après avoir complété toutes les analyses et calculs financiers.

    Arguments :
    - calculation_summary_str : Chaîne de texte contenant le résumé chiffré généré par l'outil de calcul 
      (mensualités, taux, RAB, ratios, statut, etc.). Ces données doivent refléter les résultats effectifs 
      du calcul et ne jamais être inventées.
    - financial_analysis_str : Chaîne de texte contenant l'analyse narrative et professionnelle du dossier, 
      qui DOIT obligatoirement commencer par l'en-tête suivant :
      
        Le total estimé de votre demande s'élève à [Montant demandé] TND
        Taux d'intérêt : [Taux] %
        Durée de remboursement : [Durée] ans
        Montant autorisé : [Montant accordé] TND
        Assurances : [Assurance] TND / Mois
        Mensualité : [Mensualité] TND / Mois
        (*) Potentiel Credit : [Montant accordé] TND
        Statut : [SUCCESS ou ÉCHEC_DÉFINITIF]
      
      Puis suivi de l'analyse détaillée OBLIGATOIREMENT structurée comme suit :
        * Rappel de la demande initiale (ex: 10 000 DT sur 1 an) vs proposition finale (si ajustement ou échec).
        * Capacité de remboursement du client.
        * Solvabilité et ratio d’endettement (DTI).
        * Points forts / points faibles.

    Contraintes :
    - NE JAMAIS inventer des chiffres ou des indicateurs
    - Ne pas répéter les phrases
    - Rédiger un texte fluide, structuré et professionnel, adapté à un usage bancaire
    - Cette fonction ne retourne qu’un statut confirmant la soumission

    Retour :
    - "FINANCE_REPORT_SUBMITTED" : confirmation que le rapport a été soumis avec succès
    """
    
    return "FINANCE_REPORT_SUBMITTED"
