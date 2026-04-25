"""
Car Recommendation Agent with Financial Analysis
Matches car listings to user profile based on:
- Financial capacity (income, expenses, liquidity)
- Persona (conservative, aggressive, balanced)
- Brand/Origin preferences from prompt
- Age and condition of vehicle
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from ..pi_utils.llm import call_llm
from ..pi_utils.db_neo4j import neo4j_handler

@dataclass
class FinancialProfile:
    """User's financial situation for car affordability analysis"""
    monthly_income: float = 0
    monthly_expenses: float = 0
    total_liquidity: float = 0
    budget: float = 0
    savings_rate: float = 0  # percentage

@dataclass
class CarListing:
    """Structured car data from scraper"""
    title: str
    price: float
    brand: str
    year: int
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    power: Optional[int] = None  # horsepower
    location: Optional[str] = None
    image_url: Optional[str] = None
    listing_url: Optional[str] = None
    origin: Optional[str] = None  # european, japanese, american, etc.

class CarRecommender:
    """
    Intelligent car recommendation engine that analyzes:
    1. Financial fit (can user afford it?)
    2. Persona match (does it suit their risk/style profile?)
    3. Brand/Origin preferences (from user prompt)
    4. Value analysis (good deal for the specs?)
    """

    # Brand to origin mapping - using specific countries
    BRAND_ORIGINS = {
        # German
        'audi': 'german', 'bmw': 'german', 'mercedes': 'german', 'mercedes-benz': 'german',
        'volkswagen': 'german', 'vw': 'german', 'porsche': 'german', 'opel': 'german',
        # French
        'peugeot': 'french', 'citroen': 'french', 'renault': 'french', 'ds': 'french', 'alpine': 'french',
        # Czech
        'skoda': 'czech',
        # Spanish
        'seat': 'spanish', 'cupra': 'spanish',
        # Italian
        'fiat': 'italian', 'alfa romeo': 'italian', 'lancia': 'italian',
        # Swedish
        'volvo': 'swedish',
        # British
        'jaguar': 'british', 'land rover': 'british', 'range rover': 'british', 'mini': 'british',
        # Japanese
        'toyota': 'japanese', 'honda': 'japanese', 'nissan': 'japanese',
        'mazda': 'japanese', 'mitsubishi': 'japanese', 'subaru': 'japanese',
        'lexus': 'japanese', 'infiniti': 'japanese', 'suzuki': 'japanese',
        'daihatsu': 'japanese', 'isuzu': 'japanese',
        # Korean
        'hyundai': 'korean', 'kia': 'korean', 'ssangyong': 'korean',
        'genesis': 'korean', 'daewoo': 'korean',
        # American
        'ford': 'american', 'chevrolet': 'american', 'chevy': 'american',
        'dodge': 'american', 'jeep': 'american', 'chrysler': 'american',
        'cadillac': 'american', 'lincoln': 'american', 'buick': 'american',
        'gmc': 'american', 'tesla': 'american', 'rivian': 'american',
        # Chinese
        'chery': 'chinese', 'geely': 'chinese', 'byd': 'chinese',
        'gwm': 'chinese', 'haval': 'chinese', 'jac': 'chinese',
        'mg': 'chinese', 'roewe': 'chinese', 'changan': 'chinese',
        'dfsk': 'chinese', 'jetour': 'chinese', 'baic': 'chinese',
        # Other
        'tata': 'indian', 'mahindra': 'indian', 'maruti': 'indian', 'dacia': 'romanian'
    }

    # Reliability scores by brand (1-10)
    RELIABILITY_SCORES = {
        'toyota': 9.5, 'lexus': 9.5, 'honda': 9.0, 'mazda': 8.5,
        'subaru': 8.5, 'hyundai': 8.0, 'kia': 8.0, 'skoda': 7.5,
        'seat': 7.0, 'volkswagen': 7.0, 'audi': 7.5, 'bmw': 7.0,
        'mercedes': 7.5, 'ford': 6.5, 'chevrolet': 6.5, 'peugeot': 6.0,
        'citroen': 6.0, 'renault': 6.0, 'fiat': 5.5, 'alfa romeo': 5.0,
        'land rover': 5.5, 'range rover': 5.0, 'jaguar': 5.5,
    }

    def __init__(self):
        self.neo4j = neo4j_handler

    def parse_financial_profile(self, profile: Dict) -> FinancialProfile:
        """Extract financial data from user profile"""
        return FinancialProfile(
            monthly_income=profile.get('monthly_income', 0),
            monthly_expenses=profile.get('monthly_expenses', 0),
            total_liquidity=profile.get('total_liquidity', 0),
            # Default to a large number if no budget or liquidity is set to avoid division by zero
            budget=profile.get('budget') or (profile.get('total_liquidity', 0) * 0.3) or 1000000,
            savings_rate=profile.get('savings_rate', 0)
        )

    def extract_brand_preferences(self, goal: str) -> Dict[str, Any]:
        """Extract brand, origin, and type preferences from user prompt"""
        goal_lower = goal.lower()
        preferences = {
            'brands': [],
            'origins': [],
            'car_types': [],
            'excluded_brands': [],
            'price_range': None,
            'year_min': None,
            'fuel_type': None,
        }

        # Extract specific brands mentioned
        for brand in self.BRAND_ORIGINS.keys():
            if brand in goal_lower:
                preferences['brands'].append(brand)

        # Extract origins (specific countries) - Supporting English and French
        origin_keywords = {
            'german': ['german', 'germany', 'allemand', 'allemande'],
            'french': ['french', 'france', 'français', 'française'],
            'italian': ['italian', 'italy', 'italien', 'italienne'],
            'british': ['british', 'uk', 'britain', 'english', 'anglais', 'anglaise', 'britannique'],
            'swedish': ['swedish', 'sweden', 'suédois', 'suédoise'],
            'czech': ['czech', 'tchèque'],
            'spanish': ['spanish', 'spain', 'espagnol', 'espagnole'],
            'japanese': ['japanese', 'japan', 'japonais', 'japonaise'],
            'korean': ['korean', 'korea', 'south korean', 'coréen', 'coréenne'],
            'american': ['american', 'usa', 'us made', 'américain', 'américaine'],
            'chinese': ['chinese', 'china', 'chinois', 'chinoise'],
        }
        for origin, keywords in origin_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                preferences['origins'].append(origin)

        # Extract car types
        car_types = {
            'suv': ['suv', 'crossover', '4x4', 'four wheel drive', 'awd'],
            'sedan': ['sedan', 'berline', 'family car'],
            'hatchback': ['hatchback', 'compact', 'city car'],
            'sports': ['sports car', 'sport', 'coupe', 'performance'],
            'luxury': ['luxury', 'premium', 'high end', 'lux'],
            'economy': ['economy', 'cheap', 'budget', 'affordable', 'low cost'],
            'electric': ['electric', 'ev', 'tesla', 'battery'],
            'hybrid': ['hybrid', 'plugin', 'phev'],
        }
        for car_type, keywords in car_types.items():
            if any(kw in goal_lower for kw in keywords):
                preferences['car_types'].append(car_type)

        # Extract price range indicators
        price_patterns = [
            r'under\s+(\d+)\s*(?:k|000)?',
            r'less\s+than\s+(\d+)\s*(?:k|000)?',
            r'below\s+(\d+)\s*(?:k|000)?',
            r'budget\s+(?:de|of|à)\s+(\d+)\s*(?:k|000)?',
            r'(\d+)\s*(?:k|000)?\s*(?:-|à)\s*(\d+)\s*(?:k|000)?',
            r'\b(\d{4,6})\b', # Match 10000, 30000, etc.
        ]
        for pattern in price_patterns:
            match = re.search(pattern, goal_lower)
            if match:
                val = match.group(1)
                # If it's a small number like "30", treat as "30000"
                if len(val) <= 2:
                    preferences['extracted_budget'] = float(val) * 1000
                else:
                    preferences['extracted_budget'] = float(val)
                break

        # Extract year requirement
        year_match = re.search(r'\b(20\d{2})\b', goal_lower)
        if year_match:
            preferences['year_min'] = int(year_match.group(1))

        # Extract fuel type
        fuel_keywords = {
            'diesel': ['diesel', 'gazole'],
            'essence': ['essence', 'gasoline', 'petrol'],
            'electric': ['electric', 'electrique', 'ev'],
            'hybrid': ['hybrid', 'hybride'],
        }
        for fuel, keywords in fuel_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                preferences['fuel_type'] = fuel
                break

        # Extract location for house searches
        location_keywords = {
            'ben arous': ['ben arous', 'benarous'],
            'tunis': ['tunis centre', 'centre ville', 'la marsa', 'carthage', 'sidi bou said'],
            'ariana': ['ariana', 'ghazela', 'soukra'],
            'manouba': ['manouba', 'douar hicher'],
            'nabeul': ['nabeul', 'hammamet'],
        }
        for location, keywords in location_keywords.items():
            if any(kw in goal_lower for kw in keywords):
                preferences['location'] = location
                break

        # Extract property type for house searches
        property_types = {
            'apartment': ['appartement', 's+1', 's+2', 's+3', 's+4', 'apartment', 'flat'],
            'house': ['maison', 'villa', 'duplex', 'house', 'dar'],
            'studio': ['studio', 's+0'],
        }
        for ptype, keywords in property_types.items():
            if any(kw in goal_lower for kw in keywords):
                preferences['property_type'] = ptype
                break

        return preferences

    def score_car_affordability(self, car: CarListing, finances: FinancialProfile) -> float:
        """
        Score how affordable a car is for the user (0-100)
        - Price should be within budget
        - Monthly payment (if financed) should fit income-expenses ratio
        """
        score = 100

        # Check if price exceeds budget
        if finances.budget > 0 and car.price > finances.budget:
            # Penalize heavily for over-budget cars
            over_ratio = (car.price - finances.budget) / finances.budget
            # Drastic penalty: if 20% over budget, score drops significantly. 
            # If 100% over budget (2x price), score drops to 0.
            score -= min(100, over_ratio * 200)
        elif finances.budget == 0 and car.price > 0:
            # If budget is strictly 0 and price > 0, it's technically infinite over budget
            score -= 50

        # Calculate recommended max car price based on income
        # Rule: car shouldn't exceed 6 months of disposable income
        disposable_income = finances.monthly_income - finances.monthly_expenses
        max_recommended_price = disposable_income * 6

        if car.price > max_recommended_price:
            score -= 30
        elif car.price > max_recommended_price * 0.8:
            score -= 15

        # Reward cars well within budget
        if car.price < finances.budget * 0.7:
            score += 10

        return max(0, min(100, score))

    def score_persona_match(self, car: CarListing, persona: str, car_types: List[str]) -> float:
        """
        Score how well car matches user's persona (0-100)
        Conservative: Reliable, practical, good value
        Aggressive: Performance, luxury, status
        Balanced: Mix of both
        """
        score = 50  # Base score

        # Get reliability score
        reliability = self.RELIABILITY_SCORES.get(car.brand.lower(), 6.0)

        if persona == 'conservative':
            # Prefer reliable brands, lower power, economy cars
            score += reliability * 3  # Up to +28.5

            if 'economy' in car_types or 'hatchback' in car_types:
                score += 15
            if 'luxury' in car_types or 'sports' in car_types:
                score -= 20  # Penalty for flashy cars
            if car.power and car.power > 200:
                score -= 10  # Less powerful is better for conservative

        elif persona == 'aggressive':
            # Prefer performance, luxury, newer cars
            if 'luxury' in car_types or 'sports' in car_types:
                score += 25
            if 'suv' in car_types:
                score += 10
            if car.power and car.power > 200:
                score += 15
            # Aggressive personas care less about reliability
            score += (reliability - 5) * 1.5  # Smaller reliability bonus

        elif persona == 'balanced':
            # Fair consideration of all factors
            score += reliability * 2
            if 'sedan' in car_types or 'suv' in car_types:
                score += 10

        # Age factor - newer is generally better for all personas
        current_year = 2024
        age = current_year - car.year
        if age < 3:
            score += 10
        elif age < 7:
            score += 0
        else:
            score -= age * 1.5  # Older cars get penalized

        return max(0, min(100, score))

    def score_preference_match(self, car: CarListing, preferences: Dict) -> float:
        """
        Score how well car matches user's stated preferences (0-100)
        """
        score = 50

        # Brand preference match
        if preferences['brands']:
            if car.brand.lower() in [b.lower() for b in preferences['brands']]:
                score += 30  # Strong bonus for preferred brand
            else:
                score -= 10  # Slight penalty for non-preferred

        # Origin preference match
        car_origin = self.BRAND_ORIGINS.get(car.brand.lower(), 'unknown')
        if preferences['origins'] and car_origin in preferences['origins']:
            score += 20

        # Car type match (inferred from title)
        if preferences['car_types']:
            title_lower = car.title.lower()
            type_matched = False
            for car_type in preferences['car_types']:
                if car_type in title_lower:
                    score += 15
                    type_matched = True
            if not type_matched:
                score -= 5

        # Fuel type match
        if preferences['fuel_type'] and car.fuel_type:
            if preferences['fuel_type'].lower() == car.fuel_type.lower():
                score += 15

        # Year preference
        if preferences['year_min'] and car.year < preferences['year_min']:
            score -= 20  # Penalty for too old

        return max(0, min(100, score))

    def score_value_for_money(self, car: CarListing) -> float:
        """
        Score the deal quality (0-100)
        Considers: price vs year, mileage, brand value
        """
        score = 50

        # Depreciation curve scoring
        current_year = 2024
        age = current_year - car.year

        # Expected price based on age (rough depreciation model)
        # New car loses 20% first year, then 10% per year
        # Assuming original price of 40k average
        original_price_estimate = 40000
        expected_price = original_price_estimate * (0.8 ** min(age, 1)) * (0.9 ** max(0, age - 1))

        if car.price < expected_price * 0.8:
            score += 25  # Great deal
        elif car.price < expected_price:
            score += 10  # Good deal
        elif car.price > expected_price * 1.3:
            score -= 20  # Overpriced

        # Mileage factor (if available)
        if car.mileage:
            expected_mileage = age * 15000  # 15k km per year average
            if car.mileage < expected_mileage * 0.7:
                score += 15  # Low mileage bonus
            elif car.mileage > expected_mileage * 1.5:
                score -= 15  # High mileage penalty

        return max(0, min(100, score))

    def rank_cars(self, cars: List[Dict], profile: Dict, persona: str, goal: str) -> List[Dict]:
        """
        Main ranking function that combines all scoring factors
        Returns cars sorted by overall match score with recommendation details
        """
        # Parse inputs
        finances = self.parse_financial_profile(profile)
        preferences = self.extract_brand_preferences(goal)
        
        # Use extracted budget if profile budget is empty or smaller
        if preferences.get('extracted_budget'):
            finances.budget = preferences['extracted_budget']

        # Convert raw car dicts to CarListing objects and score
        scored_cars = []
        for car_data in cars:
            try:
                car = CarListing(
                    title=car_data.get('title', 'Unknown'),
                    price=float(car_data.get('price', 0)),
                    brand=car_data.get('brand', self._extract_brand(car_data.get('title', ''))),
                    year=int(car_data.get('year', 2020)),
                    mileage=car_data.get('mileage'),
                    fuel_type=car_data.get('fuel_type'),
                    transmission=car_data.get('transmission'),
                    power=car_data.get('power'),
                    location=car_data.get('location'),
                    image_url=car_data.get('image_url'),
                    listing_url=car_data.get('listing_url'),
                )

                # Filter by brand origin if specified
                if preferences['origins']:
                    car_origin = self.BRAND_ORIGINS.get(car.brand.lower(), '')
                    print(f"🔍 Car: {car.brand}, Origin: {car_origin}, Requested: {preferences['origins']}")
                    if car_origin not in preferences['origins']:
                        print(f"   ❌ Skipping {car.brand} - origin {car_origin} not in {preferences['origins']}")
                        # Skip this car - doesn't match requested origin
                        continue
                    else:
                        print(f"   ✅ Keeping {car.brand} - matches origin {car_origin}")

                # Calculate component scores
                affordability = self.score_car_affordability(car, finances)
                persona_match = self.score_persona_match(car, persona, preferences['car_types'])
                preference_match = self.score_preference_match(car, preferences)
                value_score = self.score_value_for_money(car)

                # Weighted total score
                # Affordability is most important (can't buy what you can't afford)
                # Persona match is second (should suit their style)
                # Preference match is third (specific wants)
                # Value is fourth (nice to have)
                total_score = (
                    affordability * 0.35 +
                    persona_match * 0.25 +
                    preference_match * 0.25 +
                    value_score * 0.15
                )

                # Get the pre-generated xAI insight and investment return
                xai_insight = car_data.get('xai', self._generate_reason(
                    car, affordability, persona_match, preference_match,
                    value_score, finances, preferences
                ))
                investment_return = car_data.get('investment_return', 12.5)

                # Determine decision
                if affordability < 40:
                    decision = 'ATTENDRE'
                    xai_insight += " (Dépasse le budget)"
                elif total_score >= 75:
                    decision = 'ACHETER'
                elif total_score >= 60:
                    decision = 'CONSIDÉRER'
                else:
                    decision = 'ATTENDRE'

                # Clean title to avoid duplicate brand names
                clean_title = car.title
                if car.brand.lower() != 'unknown' and car.brand.lower() in clean_title.lower():
                    # Remove brand from title if it's already there
                    clean_title = re.sub(r'(?i)' + re.escape(car.brand), '', clean_title).strip()
                
                scored_cars.append({
                    'car': car,
                    'scores': {
                        'total': round(total_score, 1),
                        'affordability': round(affordability, 1),
                        'persona_match': round(persona_match, 1),
                        'preference_match': round(preference_match, 1),
                        'value': round(value_score, 1)
                    },
                    'recommendation': {
                        'asset': f"{car.brand.title()} {clean_title} ({car.year})",
                        'price': car.price,
                        'decision': decision,
                        'reason': xai_insight, # UI uses 'reason' as the XAI insight
                        'investment_return': investment_return, # UI uses this for the percentage
                        'details': car_data
                    }
                })

            except Exception as e:
                print(f"Error scoring car {car_data}: {e}")
                continue

        # Sort by total score descending
        scored_cars.sort(key=lambda x: x['scores']['total'], reverse=True)
        return scored_cars

    def _extract_brand(self, title: str) -> str:
        """Extract brand from car title"""
        title_lower = title.lower()
        for brand in self.BRAND_ORIGINS.keys():
            if brand in title_lower:
                return brand
        return 'unknown'

    def _generate_reason(self, car: CarListing, affordability: float,
                         persona_match: float, preference_match: float,
                         value_score: float, finances: FinancialProfile,
                         preferences: Dict) -> str:
        """Génère une raison de recommandation lisible par l'homme"""
        reasons = []

        # Commentaire sur l'accessibilité financière
        if affordability >= 80:
            reasons.append("bien en deçà de votre budget")
        elif affordability >= 60:
            reasons.append("correspond à votre budget")
        else:
            reasons.append("à la limite supérieure de votre budget")

        # Commentaire sur la valeur
        if value_score >= 75:
            reasons.append("excellent rapport qualité-prix")
        elif value_score >= 60:
            reasons.append("bonne affaire")

        # Correspondance marque/préférence
        if preferences['brands'] and car.brand.lower() in [b.lower() for b in preferences['brands']]:
            reasons.append(f"correspond à votre préférence pour {car.brand.title()}")

        # Commentaire sur l'âge
        age = 2024 - car.year
        if age <= 3:
            reasons.append("état presque neuf")
        elif age <= 7:
            reasons.append("bon âge avec des fonctionnalités modernes")

        # Kilométrage
        if car.mileage and car.mileage < 50000:
            reasons.append("faible kilométrage")

        return ", ".join(reasons) if reasons else "Recommandation standard"


def car_recommendation_agent(state: Dict) -> Dict:
    """
    Point d'entrée pour les recommandations de voitures dans le workflow de l'agent
    Prend l'état avec les annonces, le profil, le persona, l'objectif
    Retourne l'état avec les recommandations de voitures
    """
    recommender = CarRecommender()

    user_id = state.get("user_id", "default_user")
    profile = state.get("profile", {})
    persona = state.get("persona", "balanced")
    goal = state.get("goal", "").lower()
    listings = state.get("listings", [])

    # Filtrer uniquement les annonces de voitures
    car_keywords = ['car', 'voiture', 'vehicle', 'auto', 'audi', 'bmw', 'mercedes', 'toyota', 'volkswagen', 'renault', 'peugeot']
    car_listings = []
    for l in listings:
        # Vérifier le type/catégorie explicite
        if l.get('type') == 'car' or 'car' in l.get('category', '').lower() or 'voiture' in l.get('category', '').lower():
            car_listings.append(l)
            continue
        # Vérifier le titre pour les mots-clés de voiture
        title = l.get('title', '').lower()
        if any(kw in title for kw in car_keywords):
            # Ajouter un marqueur de type
            l['type'] = 'car'
            car_listings.append(l)

    if not car_listings:
        state["recommendations"] = [{
            "asset": "Recherche de voiture",
            "decision": "HOLD",
            "reason": "Aucune voiture trouvée dans les annonces. Essayez une recherche différente."
        }]
        return state

    # Classer les voitures
    scored_cars = recommender.rank_cars(car_listings, profile, persona, goal)

    # Obtenir les 6 meilleures recommandations
    top_recommendations = [car['recommendation'] for car in scored_cars[:6]]

    # Si aucune voiture n'a un score élevé, fournir des conseils
    if not top_recommendations or scored_cars[0]['scores']['total'] < 50:
        top_recommendations = [{
            "asset": "Ajustement de la recherche",
            "decision": "HOLD",
            "reason": "Aucune voiture ne correspond bien à vos critères. Envisagez d'élargir votre budget, d'ajuster vos préférences de marque ou de regarder des modèles légèrement plus anciens."
        }]

    state["recommendations"] = top_recommendations
    state["car_scores"] = {car['recommendation']['asset']: car['scores'] for car in scored_cars[:6]}

    return state


def house_recommendation_agent(state: Dict) -> Dict:
    """
    Point d'entrée pour les recommandations de maisons dans le workflow de l'agent
    Prend l'état avec les annonces, le profil, le persona, l'objectif
    Retourne l'état avec les recommandations de maisons
    """
    import random
    
    profile = state.get("profile", {})
    persona = state.get("persona", "neutral")
    goal = state.get("goal", "")
    listings = state.get("listings", [])
    
    # Filtrer uniquement les maisons
    houses = [l for l in listings if l.get('category') == 'house' or l.get('type') == 'house' or 'house' in str(l.get('goal', '')).lower() or 'maison' in str(l.get('goal', '')).lower()]
    
    # Si toujours pas de maisons mais que nous avons des annonces et que l'objectif est lié aux maisons
    if not houses and listings and any(kw in str(goal).lower() for kw in ['house', 'home', 'villa', 'maison', 'appartement']):
        print(f"DEBUG: Aucun filtre de catégorie/type de maison, utilisation des {len(listings)} annonces")
        houses = listings
    
    if not houses:
        state["recommendations"] = [{
            "asset": "Ajustement de la recherche",
            "decision": "HOLD",
            "reason": "Aucune propriété trouvée dans cette zone. Essayez de chercher dans un endroit différent ou avec un budget différent."
        }]
        return state
    
    # Trier par prix (le plus proche du budget)
    budget = profile.get("budget", 200000)
    try:
        budget = int(budget) if budget else 200000
    except:
        budget = 200000
    
    houses.sort(key=lambda x: abs(x.get('price', 0) - budget))
    
    # Générer des recommandations
    recommendations = []
    for idx, house in enumerate(houses[:6], 1):
        price = house.get('price', 0)
        title = house.get('title', 'Propriété')
        location = house.get('location', 'Inconnu')
        surface = house.get('surface', '')
        
        # Générer la décision
        if price <= budget * 1.1:
            decision = "ACHETER"
        elif price <= budget * 1.3:
            decision = "SURVEILLER"
        else:
            decision = "ÉVITER"
            
        # Obtenir l'insight xAI et le rendement d'investissement pré-générés
        xai_insight = house.get('xai', f"{title} à {location}. Bon emplacement avec {surface}.")
        investment_return = house.get('investment_return', 12.5)
        
        recommendations.append({
            "asset": f"{title} ({location})",
            "price": price,
            "decision": decision,
            "reason": xai_insight,
            "investment_return": investment_return,
            "details": {
                "location": location,
                "surface": surface,
                "url": house.get('url', ''),
                "image": house.get('image', '')
            }
        })
    
    state["recommendations"] = recommendations
    state["house_scores" ] = {f"{h.get('title', 'Propriété')} ({h.get('location', '')})": {"price": h.get('price', 0), "rank": i+1} for i, h in enumerate(houses[:6])}
    
    return state
