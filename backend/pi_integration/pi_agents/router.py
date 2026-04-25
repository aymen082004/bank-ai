def router_agent(state):
    """
    Decides where to route next based on user goal.
    """
    profile = state.get("profile", {})
    goal = profile.get("goal", "").lower()

    # Car-related keywords (French and English)
    car_keywords = ['car', 'voiture', 'auto', 'automobile', 'vehicle', 'buy car', 'achat voiture']
    # House-related keywords
    house_keywords = ['house', 'home', 'apartment', 'maison', 'appartement', 'property', 'immobilier', 'dar', 'real estate']
    # Investment keywords
    invest_keywords = ['invest', 'stock', 'action', 'bourse', 'trading', 'portfolio']

    if any(kw in goal for kw in car_keywords):
        return "scraper"
    elif any(kw in goal for kw in house_keywords):
        return "scraper"
    elif any(kw in goal for kw in invest_keywords):
        return "stock"
    else:
        return "end"
