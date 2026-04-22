def final_decision(acc_result, card_result=None):

    score = 0

    # ---- ACCOUNT ----
    if acc_result:
        score += acc_result.get("final_score", 0)

        if acc_result.get("final_label") == "Fraud":
            score += 1   # boost

    # ---- CARD ----
    if card_result:
        score += card_result.get("final_score", 0)

        if card_result.get("final_label") == "Fraud":
            score += 1

    # ---- FINAL ----
    if score >= 2:
        return "Fraud"
    elif score >= 1:
        return "Suspicious"
    else:
        return "Non-Fraud"