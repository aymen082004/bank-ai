import urllib.parse
import re
import requests
import json
import html
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from ..pi_utils.llm import call_llm
from .agent_factory import create_structured_agent_executor, SCRAPER_SYSTEM_PROMPT

def scrape_automobile_tn(budget, persona, preferences):
    """
    Scrapes cars from automobile.tn using requests + BeautifulSoup.
    Many sites have server-side rendered HTML for SEO purposes.
    """
    brand = preferences.get("brand", "")
    brand_origin = preferences.get("brand_origin", "")
    condition = preferences.get("condition", "used")
    
    # Comprehensive brand to origin mapping based on automobile.tn brands
    brand_origins = {
        # German brands
        "audi": "german", "bmw": "german", "mercedes": "german", "mercedes-benz": "german",
        "volkswagen": "german", "vw": "german", "porsche": "german", "opel": "german",
        # French brands
        "renault": "french", "peugeot": "french", "citroen": "french", "citroën": "french",
        "ds": "french", "alpine": "french", "bugatti": "french",
        # Japanese brands
        "toyota": "japanese", "honda": "japanese", "nissan": "japanese",
        "mitsubishi": "japanese", "mazda": "japanese", "suzuki": "japanese", "isuzu": "japanese",
        # Korean brands
        "kia": "korean", "hyundai": "korean", "ssangyong": "korean", "kg mobility": "korean",
        # American brands
        "ford": "american", "chevrolet": "american", "jeep": "american", "tesla": "american",
        # British brands
        "jaguar": "british", "land rover": "british", "mini": "british", "bentley": "british",
        "rolls-royce": "british", "aston martin": "british", "mg": "british",
        # Italian brands
        "fiat": "italian", "alfa romeo": "italian", "lancia": "italian", "ferrari": "italian",
        "lamborghini": "italian", "maserati": "italian",
        # Chinese brands
        "byd": "chinese", "changan": "chinese", "chery": "chinese",
        "dongfeng": "chinese", "geely": "chinese", "gwm": "chinese",
        "jac": "chinese", "jetour": "chinese", "foton": "chinese",
        "gac": "chinese", "faw": "chinese", "jac motors": "chinese",
        "jm motors": "chinese", "jmc": "chinese", "jmev": "chinese",
        "link&co": "chinese", "lynkco": "chinese", "mg": "chinese",
        "omoda": "chinese", "jaecoo": "chinese", "skoda": "czech",
        "seat": "spanish", "cupra": "spanish", "tata": "indian",
        "volvo": "swedish", "dfsk": "chinese", "dacia": "romanian",
        "deepal": "chinese", "bako": "chinese", "avantier": "chinese", "avantier motors": "chinese",
        "centra": "chinese", "haval": "chinese", "tank": "chinese", "ora": "chinese",
        "wey": "chinese", "exeed": "chinese", "voyah": "chinese", "zeekr": "chinese"
    }
    
    # List of country/region names that might be set as brand by mistake
    country_names = {
        "german": "german", "allemande": "german", "allemand": "german",
        "french": "french", "française": "french", "français": "french",
        "japanese": "japanese", "japonaise": "japanese", "japonais": "japanese",
        "korean": "korean", "coréenne": "korean", "coréen": "korean",
        "american": "american", "américaine": "american", "américain": "american",
        "british": "british", "britannique": "british", "anglaise": "british",
        "italian": "italian", "italienne": "italian", "italien": "italian",
        "chinese": "chinese", "chinoise": "chinese", "chinois": "chinese",
        "spanish": "spanish", "espagnole": "spanish", "espagnol": "spanish",
        "indian": "indian", "indienne": "indian", "indien": "indian",
        "czech": "czech", "tchèque": "czech",
        "romanian": "romanian", "roumaine": "romanian", "roumain": "romanian",
        "swedish": "swedish", "suédoise": "swedish", "suédois": "swedish"
    }
    
    # If brand is a country name, convert to brand_origin
    brand_clean = brand.lower().strip() if brand else ""
    if brand_clean in country_names:
        brand_origin = country_names[brand_clean]
        brand = "" # Clear brand so we don't filter by the country name later
    
    # If brand_origin is set but no brand, we don't want to force a single brand here
    # We want to keep all brands from that origin
    
    # If brand is set (and not an origin), ensure brand_origin is correct for filtering later
    if brand and not brand_origin:
        brand_origin = brand_origins.get(brand.lower(), "")
    
    # Build URL - use neuf search page with empty query (shows all cars)
    # This page has the .versions-item car listings visible in server-rendered HTML
    base_url = "https://www.automobile.tn/fr/neuf/recherche/s="
    
    listings = []
    
    # Only scrape new cars from automobile.tn using Playwright
    print(f"🔍 Scraping new cars from automobile.tn with Playwright...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            cars = []
            # Scrape all 15 pages completely to find all available cars
            for page_num in range(1, 16):  # Pages 1-15
                    
                # Build URL with pagination
                page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                print(f"🌐 Navigating to page {page_num}: {page_url}")
                
                try:
                    page.goto(page_url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(2000)  # Wait for JS to render
                    
                    # Get page content after JS execution
                    page_html = page.content()
                    soup = BeautifulSoup(page_html, 'html.parser')
                    
                    # TARGETED: Look for specific car listing containers
                    car_containers = []
                    selectors = [
                        '.versions-item',
                        'article.annonce',
                        '.occasion-item',
                        '.annonce-voiture',
                        'article[data-id]',
                        '.listing-item',
                        '.car-item',
                        '.vehicle-card'
                    ]
                    
                    for selector in selectors:
                        elements = soup.select(selector)
                        if elements:
                            car_containers.extend(elements)
                    
                    print(f"🔍 Page {page_num}: Found {len(car_containers)} car containers")
                    
                    # Process car containers - collect all cars from this page
                    for idx, el in enumerate(car_containers):
                            
                        try:
                            text = el.get_text(separator=' ', strip=True)
                            
                            # Look for price patterns
                            price_matches = re.findall(r'\b(\d{1,3}[\s\.]?\d{3})\b', text)
                            if not price_matches:
                                continue
                            
                            # Extract price
                            price = 0
                            for match in price_matches:
                                digits = re.sub(r'[^\d]', '', match)
                                if digits and len(digits) >= 4:
                                    price = int(digits)
                                    if price > 1000000:
                                        price = price / 1000
                                    break
                            
                            # Skip if price not valid
                            if price < 5000 or price > 500000:
                                continue
                            
                            # Get title
                            title = ''
                            for sel in ['h2', 'h3', '.title', 'a']:
                                title_el = el.select_one(sel)
                                if title_el:
                                    title = title_el.get_text(strip=True)
                                    if len(title) > 3:
                                        break
                            
                            if not title:
                                title = text[:100].strip()
                            
                            # Skip ads
                            if any(kw in title.lower() for kw in ['présentation', 'cote automobile', 'appréciations']):
                                continue
                            
                            # Get image
                            image = ''
                            img_el = el.find('img')
                            if img_el:
                                image = img_el.get('data-src') or img_el.get('src', '')
                            
                            # Get URL
                            url = ''
                            link_el = el.find('a')
                            if link_el:
                                href = link_el.get('href', '')
                                if href:
                                    url = href if href.startswith('http') else 'https://www.automobile.tn' + href
                            
                            # Extract brand and year
                            brand = 'Unknown'
                            title_text = (title + ' ' + text).lower()
                            
                            # Use the comprehensive brand_origins list for matching
                            # Sort by length descending to match "Alfa Romeo" before "Fiat" (if overlap existed)
                            sorted_brands = sorted(brand_origins.keys(), key=len, reverse=True)
                            for b in sorted_brands:
                                if b in title_text:
                                    brand = b.replace('citroën', 'citroen').title()
                                    if brand == 'Vw': brand = 'Volkswagen'
                                    break
                            
                            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', title + text)
                            year = int(year_match.group(1)) if year_match else 2020
                            
                            if title and len(title) > 5:
                                cars.append({
                                    'title': title[:150],
                                    'price': price,
                                    'brand': brand,
                                    'year': year,
                                    'url': url,
                                    'location': 'Tunisia',
                                    'image': image or 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&q=80&w=400',
                                    'category': 'car',
                                    'type': 'car'
                                })
                                
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    print(f"⚠️ Error on page {page_num}: {e}")
                    continue
            
            if cars:
                listings.extend(cars)
                print(f"✅ Scraped {len(cars)} cars from Automobile.tn (all 15 pages)")
            else:
                print(f"⚠️ No cars extracted from Automobile.tn (no car listings found)")
            
            browser.close()
        
    except Exception as e:
        print(f"⚠️ Error scraping automobile.tn: {e}")
    
    # Filter by budget - Relaxed filter to avoid removing all cars
    if budget and budget > 0:
        original_count = len(listings)
        # If budget is very low (e.g. monthly budget), allow up to a reasonable car price
        max_budget = max(budget * 5, 100000)
        listings = [l for l in listings if l.get('price', 0) <= max_budget]
        print(f"💰 Filtered by budget (max {max_budget}): {len(listings)}/{original_count} cars remain")
    
    # Filter by brand origin if specified
    if brand_origin:
        brand_origin = brand_origin.lower()
        original_count = len(listings)
        filtered = []
        for l in listings:
            brand_val = l.get('brand', 'Unknown').lower()
            car_origin = brand_origins.get(brand_val, '')
            
            if car_origin == brand_origin:
                filtered.append(l)
                print(f"   ✅ {brand_val.title()} - matches {brand_origin}")
            else:
                print(f"   ❌ {brand_val.title()} - {car_origin} not {brand_origin}")
        
        listings = filtered
        print(f"🏳️ Filtered by origin ({brand_origin}): {len(listings)}/{original_count} cars remain")
    
    # Remove duplicates by URL and by model name (avoid "Picanto" + "Picanto Populaire")
    seen_urls = set()
    seen_models = set()
    unique_listings = []
    for l in listings:
        # Extract base model name (e.g., "Picanto" from "KIA Picanto Populaire")
        title_lower = l['title'].lower()
        # Get model by removing brand and common suffixes
        brand_lower = l.get('brand', '').lower()
        model_part = title_lower.replace(brand_lower, '').strip()
        # Remove trim levels like "populaire", "berline", etc.
        for trim in ['populaire', 'berline', 'sedan', 'hatchback', 'premium', 'active', 'trend']:
            model_part = model_part.replace(trim, '').strip()
        base_model = model_part.strip()
        
        model_key = f"{brand_lower}_{base_model}"
        
        if l['url'] not in seen_urls and model_key not in seen_models:
            unique_listings.append(l)
            seen_urls.add(l['url'])
            seen_models.add(model_key)
            
    listings = unique_listings
    print(f"🚗 After deduplication: {len(listings)} unique models")

    # Add metadata and xAI insights
    for i, item in enumerate(listings[:50]):
        item['goal'] = 'car'
        insights = generate_car_insight(item, i+1, persona)
        item['xai'] = insights['xai']
        item['investment_return'] = insights['investment_return']
    
    return listings[:50]

def scrape_tecnocasa_tn(budget, location=None, property_type=None):
    """
    Scrapes houses/apartments from tecnocasa.tn using requests + JSON parsing.
    Supports multiple governorates and price filtering.
    The site embeds property data as JSON in the HTML.
    """
    import unicodedata
    
    listings = []
    
    # Governorate and specific area URL mapping for tecnocasa.tn
    # Format: {region}/{province}/{city}/{district}.html
    location_mapping = {
        # ========== GRAND TUNIS ==========
        
        # Ben Arous - Grand Tunis
        'ben arous': 'nord-est-ne/grand-tunis/ben-arous',
        'borj cedria': 'nord-est-ne/grand-tunis/ben-arous/borj-cedria',
        'bou mhel el bassatine': 'nord-est-ne/grand-tunis/ben-arous/bou-mhel-el-bassatine',
        'ezzahra': 'nord-est-ne/grand-tunis/ben-arous/ezzahra',
        'mégrine': 'nord-est-ne/grand-tunis/ben-arous/megrine',
        'megrine': 'nord-est-ne/grand-tunis/ben-arous/megrine',
        'radès': 'nord-est-ne/grand-tunis/ben-arous/rades',
        'rades': 'nord-est-ne/grand-tunis/ben-arous/rades',
        
        # El Mourouj - Ben Arous (specific districts)
        'el mourouj 1': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-1',
        'mourouj 1': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-1',
        'mourouj1': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-1',
        'el mourouj 2': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-2',
        'mourouj 2': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-2',
        'mourouj2': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-2',
        'el mourouj 3': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-3',
        'mourouj 3': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-3',
        'mourouj3': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-3',
        'el mourouj 4': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-4',
        'mourouj 4': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-4',
        'mourouj4': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-4',
        'el mourouj 5': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-5',
        'mourouj 5': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-5',
        'mourouj5': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-5',
        'el mourouj 6': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-6',
        'mourouj 6': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-6',
        'mourouj6': 'nord-est-ne/grand-tunis/el-mourouj/el-mourouj-6',
        # General El Mourouj (all districts)
        'el mourouj': 'nord-est-ne/grand-tunis/el-mourouj',
        'mourouj': 'nord-est-ne/grand-tunis/el-mourouj',
        
        # Tunis - Grand Tunis
        'tunis': 'nord-est-ne/grand-tunis/tunis',
        'centre ville': 'nord-est-ne/grand-tunis/tunis/centre-ville',
        'centre-ville': 'nord-est-ne/grand-tunis/tunis/centre-ville',
        'centre ville tunis': 'nord-est-ne/grand-tunis/tunis/centre-ville',
        'la marsa': 'nord-est-ne/grand-tunis/tunis/la-marsa',
        'lamarsa': 'nord-est-ne/grand-tunis/tunis/la-marsa',
        'marsa': 'nord-est-ne/grand-tunis/tunis/la-marsa',
        'carthage': 'nord-est-ne/grand-tunis/tunis/carthage',
        'jardins de carthage': 'nord-est-ne/grand-tunis/tunis/jardins-de-carthage',
        'le bardo': 'nord-est-ne/grand-tunis/tunis/le-bardo',
        'bardo': 'nord-est-ne/grand-tunis/tunis/le-bardo',
        'el omrane': 'nord-est-ne/grand-tunis/tunis/el-omrane',
        'omrane': 'nord-est-ne/grand-tunis/tunis/el-omrane',
        'el menzah': 'nord-est-ne/grand-tunis/tunis/el-menzah',
        'menzah': 'nord-est-ne/grand-tunis/tunis/el-menzah',
        'jardins d el menzah': 'nord-est-ne/grand-tunis/tunis/jardins-d-el-menzah',
        'menzah 1': 'nord-est-ne/grand-tunis/tunis/menzah-1',
        'menzah 5': 'nord-est-ne/grand-tunis/tunis/menzah-5',
        'menzah 6': 'nord-est-ne/grand-tunis/tunis/menzah-6',
        'menzah 9': 'nord-est-ne/grand-tunis/tunis/menzah-9',
        'ennasr': 'nord-est-ne/grand-tunis/tunis/ennasr',
        'ennasr 1': 'nord-est-ne/grand-tunis/tunis/ennasr-1',
        'ennasr 2': 'nord-est-ne/grand-tunis/tunis/ennasr-2',
        'cite el khadra': 'nord-est-ne/grand-tunis/tunis/cite-el-khadra',
        'lafayette': 'nord-est-ne/grand-tunis/tunis/lafayette',
        'mutuelleville': 'nord-est-ne/grand-tunis/tunis/mutuelleville',
        'medina jedida': 'nord-est-ne/grand-tunis/tunis/medina-jedida',
        'gammarth': 'nord-est-ne/grand-tunis/tunis/gammarth',
        'les berges du lac': 'nord-est-ne/grand-tunis/tunis/les-berges-du-lac',
        'berges du lac': 'nord-est-ne/grand-tunis/tunis/les-berges-du-lac',
        'lac': 'nord-est-ne/grand-tunis/tunis/les-berges-du-lac',
        'manar': 'nord-est-ne/grand-tunis/tunis/manar',
        'el manar': 'nord-est-ne/grand-tunis/tunis/el-manar',
        'ain zaghouan': 'nord-est-ne/grand-tunis/tunis/ain-zaghouan',
        'centre urbain nord': 'nord-est-ne/grand-tunis/tunis/centre-urbain-nord',
        
        # Ariana - Grand Tunis
        'ariana': 'nord-est-ne/grand-tunis/ariana',
        'ariana ville': 'nord-est-ne/grand-tunis/ariana/ariana-ville',
        'ariana ville ezzahra': 'nord-est-ne/grand-tunis/ariana/ariana-ville-ezzahra',
        'la petite ariana': 'nord-est-ne/grand-tunis/ariana/la-petite-ariana',
        'petite ariana': 'nord-est-ne/grand-tunis/ariana/la-petite-ariana',
        'cite el ghazala': 'nord-est-ne/grand-tunis/ariana/cite-el-ghazala',
        'cite ghazala': 'nord-est-ne/grand-tunis/ariana/cite-el-ghazala',
        'ghazala': 'nord-est-ne/grand-tunis/ariana/cite-el-ghazala',
        'riadh landalous': 'nord-est-ne/grand-tunis/ariana/riadh-landalous',
        'landalous': 'nord-est-ne/grand-tunis/ariana/riadh-landalous',
        'kalaat landalous': 'nord-est-ne/grand-tunis/ariana/kalaat-landalous',
        'soukra': 'nord-est-ne/grand-tunis/ariana/soukra',
        'la soukra': 'nord-est-ne/grand-tunis/ariana/la-soukra',
        'aouina': 'nord-est-ne/grand-tunis/ariana/aouina',
        'el aouina': 'nord-est-ne/grand-tunis/ariana/el-aouina',
        'borj louzir': 'nord-est-ne/grand-tunis/ariana/borj-louzir',
        'mnihla': 'nord-est-ne/grand-tunis/ariana/mnihla',
        
        # Manouba - Grand Tunis
        'manouba': 'nord-est-ne/grand-tunis/manouba',
        'douar hicher': 'nord-est-ne/grand-tunis/manouba/douar-hicher',
        'borj el amri': 'nord-est-ne/grand-tunis/manouba/borj-el-amri',
        
        # ========== CAP BON ==========
        'nabeul': 'nord-est-ne/cap-bon/nabeul',
        'nabeul ville': 'nord-est-ne/cap-bon/nabeul/nabeul-ville',
        'el haouaria': 'nord-est-ne/cap-bon/nabeul/el-haouaria',
        'hammamet': 'nord-est-ne/cap-bon/hammamet',
        'hammamet nord': 'nord-est-ne/cap-bon/hammamet/hammamet-nord',
        'hammamet sud': 'nord-est-ne/cap-bon/hammamet/hammamet-sud',
        'el kantaoui': 'nord-est-ne/cap-bon/hammamet/el-kantaoui',
        'kantaoui': 'nord-est-ne/cap-bon/hammamet/el-kantaoui',
        'kelibia': 'nord-est-ne/cap-bon/kelibia',
        'bizerte': 'nord-est-ne/bizerte/bizerte',
        
        # ========== CENTRE ==========
        # Sousse
        'sousse': 'centre/sousse',
        'suse': 'centre/sousse',
        'soussa': 'centre/sousse',
        'sousa': 'centre/sousse',
        'souse': 'centre/sousse',
        'sousse centre ville': 'centre/sousse/sousse-centre-ville',
        'sousse riadh': 'centre/sousse/sousse-riadh',
        'akouda': 'centre/sousse/akouda',
        'chott meriam': 'centre/sousse/chott-meriam',
        'hergla': 'centre/sousse/hergla',
        'khezama': 'centre/sousse/khezama',
        'hammam sousse': 'centre/sousse/hammam-sousse',
        'kalâa kebira': 'centre/sousse/kalaa-kebira',
        'kalaa kebira': 'centre/sousse/kalaa-kebira',
        'kalâa seghira': 'centre/sousse/kalaa-seghira',
        'kalaa seghira': 'centre/sousse/kalaa-seghira',
        'm saken': 'centre/sousse/m-saken',
        "m'saken": 'centre/sousse/m-saken',
        'msaken': 'centre/sousse/m-saken',
        'sahloul': 'centre/sousse/sahloul',
        'sahloul 1': 'centre/sousse/sahloul-1',
        'sahloul 2': 'centre/sousse/sahloul-2',
        'sahloul 3': 'centre/sousse/sahloul-3',
        'sahloul 4': 'centre/sousse/sahloul-4',
        'sahloul 5': 'centre/sousse/sahloul-5',
        'sahloul 6': 'centre/sousse/sahloul-6',
        
        # Monastir
        'monastir': 'centre/monastir',
        'monastire': 'centre/monastir',
        'monas': 'centre/monastir',
        'bekalta': 'centre/monastir/bekalta',
        'bembla': 'centre/monastir/bembla',
        'jemmal': 'centre/monastir/jemmal',
        'ksar hellal': 'centre/monastir/ksar-hellal',
        'sahline': 'centre/monastir/sahline',
        'sahline 1': 'centre/monastir/sahline-1',
        'sahline 2': 'centre/monastir/sahline-2',
        'téboulba': 'centre/monastir/teboulba',
        'teboulba': 'centre/monastir/teboulba',
        
        # Mahdia
        'mahdia': 'centre/mahdia',
        'mahdiya': 'centre/mahdia',
        'baghdedi': 'centre/mahdia/baghdedi',
        'chebba': 'centre/mahdia/chebba',
        'ksour essef': 'centre/mahdia/ksour-essef',
        'rejiche': 'centre/mahdia/rejiche',
        'salakta': 'centre/mahdia/salakta',
        
        # ========== SAHEL ==========
        'sidi bouzid': 'centre/sidi-bouzid',
        'kasserine': 'centre/kasserine',
        'kairouan': 'centre/kairouan',
        'kerouan': 'centre/kairouan',
        
        # ========== SUD ==========
        # Sfax
        'sfax': 'sud/sfax',
        'safax': 'sud/sfax',
        'sfax ville': 'sud/sfax/sfax-ville',
        'sfax sud': 'sud/sfax/sfax-sud',
        'sfax ouest': 'sud/sfax/sfax-ouest',
        'sakiet ezzit': 'sud/sfax/sakiet-ezzit',
        'sakiet eddaier': 'sud/sfax/sakiet-eddaier',
        
        # Gabes & Medenine
        'gabes': 'sud/gabes',
        'medenine': 'sud/medenine',
        'jerba': 'sud/medenine/jerba',
        'djerba': 'sud/medenine/jerba',
        'houmt souk': 'sud/medenine/houmt-souk',
        
        # Tataouine
        'tataouine': 'sud/tataouine',
        'gafsa': 'sud/gafsa',
        'tozeur': 'sud/tozeur',
        'kebili': 'sud/kebili',
    }
    
    # Fuzzy matching helper function
    def find_best_location_match(input_location):
        if not input_location:
            return 'nord-est-ne/grand-tunis/ben-arous'
        
        input_lower = input_location.lower().strip()
        
        # Exact match
        if input_lower in location_mapping:
            return location_mapping[input_lower]
        
        # Try fuzzy matching for spelling variations
        # Remove accents and special characters for comparison
        def normalize(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text.lower())
                         if unicodedata.category(c) != 'Mn')
        
        input_normalized = normalize(input_lower)
        
        # Check normalized matches
        for key, value in location_mapping.items():
            if normalize(key) == input_normalized:
                return value
        
        # Try substring matching with priority to longer/more specific matches
        matches = []
        for key, value in location_mapping.items():
            key_normalized = normalize(key)
            # Check if input is contained in key or vice versa
            if input_normalized in key_normalized or key_normalized in input_normalized:
                matches.append((key, value, len(key)))
        
        if matches:
            # Sort by length descending (prefer more specific matches)
            matches.sort(key=lambda x: x[2], reverse=True)
            print(f"   🔍 Fuzzy match: '{input_location}' → '{matches[0][0]}'")
            return matches[0][1]
        
        # Common spelling variations mapping
        spelling_fixes = {
            'souse': 'sousse',
            'susa': 'sousse',
            'sousa': 'sousse',
            'soussa': 'sousse',
            'suse': 'sousse',
            'safax': 'sfax',
            'sfacks': 'sfax',
            'kairwen': 'kairouan',
            'kerwan': 'kairouan',
            'kerouen': 'kairouan',
            'mounastir': 'monastir',
            'monastere': 'monastir',
            'monas': 'monastir',
            'mahdia': 'mahdia',
            'mahdiya': 'mahdia',
            'medenin': 'medenine',
            'jerba': 'djerba',
            'djarba': 'djerba',
            'tatawin': 'tataouine',
            'gabs': 'gabes',
            'gabès': 'gabes',
            'nabeul': 'nabeul',
            'nabel': 'nabeul',
            'beja': 'beja',
            'béja': 'beja',
            'jendouba': 'jendouba',
            'jandouba': 'jendouba',
            'siliana': 'siliana',
            'silyana': 'siliana',
            'zaghouan': 'zaghouan',
            'zaghwan': 'zaghouan',
            'gafsa': 'gafsa',
            'gafça': 'gafsa',
            'tozeur': 'tozeur',
            'touzeur': 'tozeur',
            'kebili': 'kebili',
            'kebili': 'kebili',
        }
        
        if input_normalized in spelling_fixes:
            fixed = spelling_fixes[input_normalized]
            if fixed in location_mapping:
                print(f"   🔍 Spelling fix: '{input_location}' → '{fixed}'")
                return location_mapping[fixed]
        
        # No match found - return default and print warning
        print(f"   ⚠️ Region not found: '{input_location}' - using default (Ben Arous)")
        print(f"   💡 Available regions: Grand Tunis, Sousse, Monastir, Mahdia, Sfax, Nabeul, Kairouan, etc.")
        return 'nord-est-ne/grand-tunis/ben-arous'
    
    # Build base URL based on location
    location_key = (location or 'ben arous').lower().strip()
    location_path = find_best_location_match(location_key)
    base_url = f"https://www.tecnocasa.tn/vendre/immeubles/{location_path}.html"
    
    # Build URL with price filters if budget provided
    price_params = []
    if budget and budget > 0:
        min_price = int(budget * 0.1)  # 10% of budget as min
        max_price = int(max(budget * 10, 1000000))  # Relaxed max
        price_params.append(f"min_price={min_price}")
        price_params.append(f"max_price={max_price}")
    
    if price_params:
        base_url = f"{base_url}?{'&'.join(price_params)}"
    
    print(f"🔍 Scraping houses from tecnocasa.tn")
    print(f"   📍 Location: {location_key.title()}")
    print(f"   💰 Budget: {budget} TND")
    print(f"   🌐 URL: {base_url}")
    
    try:
        # Use requests instead of Playwright for faster scraping
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        }
        
        print(f"⏳ Fetching page...")
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        print(f"📄 HTML received: {len(html_content)} chars")
        
        # Parse estates JSON from HTML
        # Look for :estates="[...]" pattern in the HTML
        estates_match = re.search(r':estates="(\[.*?\])"', html_content, re.DOTALL)
        
        if estates_match:
            estates_json_str = estates_match.group(1)
            # Unescape HTML entities
            estates_json_str = html.unescape(estates_json_str)
            
            try:
                estates = json.loads(estates_json_str)
                print(f"🏠 Found {len(estates)} properties in JSON data")
                
                for estate in estates[:12]:
                    try:
                        # Extract price
                        price_text = estate.get('price', '0')
                        # Handle formats like "123 456 DT", "123.456 DT", "123456 DT", or just "123456"
                        price_match = re.search(r'(\d[\d\s\.]*)\s*(?:DT|TND|Dinar|dt|tnd)?', price_text)
                        if price_match:
                            # Remove spaces and dots
                            price_str = re.sub(r'[\s\.]', '', price_match.group(1))
                            try:
                                price = int(price_str)
                            except:
                                price = 0
                        else:
                            price = 0
                        
                        if price <= 0:
                            # Fallback: check if the text itself has a price pattern
                            text_content = estate.get('title', '') + ' ' + estate.get('subtitle', '')
                            fallback_match = re.search(r'(\d{2,3}[\s\.]?\d{3})\s*(?:DT|TND|Dinar|dt|tnd)', text_content)
                            if fallback_match:
                                digits = re.sub(r'[^\d]', '', fallback_match.group(1))
                                price = int(digits)
                        
                        if price <= 0:
                            continue
                        
                        # Extract other fields
                        title = estate.get('title', 'Property')
                        subtitle = estate.get('subtitle', location_key.title())
                        surface = estate.get('surface', '')
                        detail_url = estate.get('detail_url', '')
                        
                        # Get image from images array
                        images = estate.get('images', [])
                        image_url = ''
                        if images and len(images) > 0:
                            image_urls = images[0].get('url', {})
                            image_url = image_urls.get('detail_preview') or image_urls.get('card') or image_urls.get('gallery_preview') or ''
                        
                        listings.append({
                            'title': title,
                            'price': price,
                            'location': subtitle,
                            'surface': surface,
                            'type': property_type or 'house',
                            'category': 'house',
                            'url': detail_url,
                            'image': image_url or 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&q=80&w=400',
                            'year': 2020,
                            'brand': 'Real Estate'
                        })
                        print(f"   ✓ {title[:50]}... - {price:,} DT")
                        
                    except Exception as e:
                        continue
                        
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse estates JSON: {e}")
        else:
            print(f"⚠️ No estates JSON found in HTML, using BeautifulSoup fallback")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for property containers - Tecnocasa often uses article or div with specific classes
            # Based on common patterns and the WebFetch output structure
            items = soup.select('.property-item, article, .estate-card, .listing-item')
            
            for item in items[:15]:
                try:
                    text = item.get_text(separator=' ', strip=True)
                    if 'DT' not in text and 'TND' not in text:
                        continue
                        
                    # Extract price
                    price = 0
                    price_match = re.search(r'(\d{2,3}[\s\.]?\d{3})\s*(?:DT|TND)', text)
                    if price_match:
                        digits = re.sub(r'[^\d]', '', price_match.group(1))
                        price = int(digits)
                    
                    if price <= 0: continue
                    
                    # Extract title
                    title = ""
                    title_el = item.select_one('h2, h3, .title, .property-title')
                    if title_el:
                        title = title_el.get_text(strip=True)
                    else:
                        # Fallback: look for "S+X" or property types in text
                        title_match = re.search(r'(S\+\d|Villa|Appartement|Maison|Terrain)[^,.]*', text, re.I)
                        if title_match:
                            title = title_match.group(0)
                    
                    if not title: title = "Propriété à " + location_key.title()
                    
                    # Extract image
                    image = ""
                    img_el = item.find('img')
                    if img_el:
                        image = img_el.get('data-src') or img_el.get('src', '')
                    
                    # Extract URL
                    url = ""
                    link_el = item.find('a')
                    if link_el:
                        href = link_el.get('href', '')
                        if href:
                            url = href if href.startswith('http') else 'https://www.tecnocasa.tn' + href
                    
                    listings.append({
                        'title': title,
                        'price': price,
                        'location': location_key.title(),
                        'surface': 'N/A',
                        'type': property_type or 'house',
                        'category': 'house',
                        'url': url,
                        'image': image or 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&q=80&w=400',
                        'year': 2024,
                        'brand': 'Tecnocasa'
                    })
                except:
                    continue
        
        print(f"✅ Scraped {len(listings)} houses from Tecnocasa.tn ({location_key.title()})")
        
        # Add metadata and xAI insights
        for i, item in enumerate(listings[:50]):
            item['goal'] = 'house'
            insights = generate_house_insight(item, i+1, None) # Persona handled inside if needed
            item['xai'] = insights['xai']
            item['investment_return'] = insights['investment_return']
        
    except Exception as e:
        print(f"⚠️ Tecnocasa scraping error: {e}")
        import traceback
        traceback.print_exc()
    
    return listings[:50]

def generate_car_insight(car, rank, persona):
    """Génère un insight xAI et un rendement d'investissement pour une annonce de voiture."""
    price_k = car["price"] / 1000
    persona_lower = persona.lower() if persona else "neutral"
    
    # Rendement d'investissement pour les voitures basé sur la popularité et la fiabilité
    investment_return = 12.5
    
    insights = {
        "growth": [
            f"Classé #{rank}: Excellent potentiel de rétention de valeur de {investment_return}% grâce à une forte popularité sur le marché.",
            f"Classé #{rank}: Les indicateurs de fiabilité élevés correspondent à votre profil axé sur la croissance, avec une stabilité de {investment_return}% supérieure.",
            f"Classé #{rank}: Acquisition stratégique avec une rétention de valeur projetée de {investment_return}% sur 3 ans."
        ],
        "conservative": [
            f"Classé #{rank}: Choix fiable avec des coûts de maintenance projetés {investment_return}% plus bas.",
            f"Classé #{rank}: Historique de fiabilité prouvé, assurant une valeur de revente {investment_return}% plus élevée.",
            f"Classé #{rank}: Utilitaire équilibré avec un score de popularité de {investment_return}% sur le marché tunisien."
        ],
        "aggressive": [
            f"Classé #{rank}: Option haute performance avec une popularité de {investment_return}% parmi les passionnés.",
            f"Classé #{rank}: Les caractéristiques premium et la fiabilité justifient la stabilité de valeur de {investment_return}%.",
            f"Classé #{rank}: Technologie de pointe avec un indice de fiabilité projeté de {investment_return}%."
        ]
    }
    
    insight = ""
    if "growth" in persona_lower:
        insight = insights["growth"][(rank-1) % 3]
    elif "conservative" in persona_lower or "keeper" in persona_lower:
        insight = insights["conservative"][(rank-1) % 3]
    elif "aggressive" in persona_lower:
        insight = insights["aggressive"][(rank-1) % 3]
    else:
        insight = f"Classé #{rank}: Modèle populaire avec un indice de fiabilité de {investment_return}% à {price_k:.0f}k TND."
        
    return {
        "xai": insight,
        "investment_return": investment_return
    }

def generate_house_insight(house, rank, persona):
    """Génère un insight xAI et un rendement d'investissement pour une annonce immobilière."""
    location = house.get("location", "Inconnu")
    persona_lower = persona.lower() if persona else "neutral"
    
    # Rendement d'investissement pour l'immobilier basé sur le potentiel de l'emplacement
    investment_return = 12.5
    
    insights = {
        "growth": [
            f"Classé #{rank}: Fort potentiel d'investissement à {location} avec une appréciation annuelle projetée de {investment_return}%.",
            f"Classé #{rank}: Emplacement stratégique avec un potentiel de croissance de {investment_return}% grâce au développement du quartier.",
            f"Classé #{rank}: Propriété premium à {location} affichant un rendement de {investment_return}% selon les tendances actuelles du marché."
        ],
        "conservative": [
            f"Classé #{rank}: Valeur sûre à {location} avec une stabilité de prix projetée de {investment_return}% par an.",
            f"Classé #{rank}: Quartier établi offrant une sécurité de placement avec un rendement locatif de {investment_return}%.",
            f"Classé #{rank}: Investissement patrimonial idéal à {location} avec une croissance constante de {investment_return}%."
        ],
        "aggressive": [
            f"Classé #{rank}: Opportunité à haut rendement à {location} visant une plus-value de {investment_return}% à court terme.",
            f"Classé #{rank}: Zone en pleine expansion offrant un levier de croissance de {investment_return}% pour votre portefeuille.",
            f"Classé #{rank}: Actif immobilier sous-évalué à {location} avec un potentiel de rattrapage de {investment_return}%."
        ]
    }
    
    insight = ""
    if "growth" in persona_lower:
        insight = insights["growth"][(rank-1) % 3]
    elif "conservative" in persona_lower or "keeper" in persona_lower:
        insight = insights["conservative"][(rank-1) % 3]
    elif "aggressive" in persona_lower or "spender" in persona_lower:
        insight = insights["aggressive"][(rank-1) % 3]
    else:
        insight = f"Classé #{rank}: Propriété à {location} avec un rendement cible de {investment_return}% basé sur le potentiel local."
    
    return {
        "xai": insight,
        "investment_return": investment_return
    }

# LangChain imports for agent conversion
from typing import Dict, Any, List

def scraper_agent(state):
    """
    Advanced Scraper Agent: Uses specific sites based on refined user intent.
    Uses LangChain ReAct agent for intelligent tool selection.
    """
    profile = state.get("profile", {})
    persona = state.get("persona", "neutral")
    goal = profile.get("goal")
    preferences = profile.get("preferences", {})
    
    budget_raw = profile.get("budget", 100000)
    try:
        budget = float(budget_raw) if budget_raw else 100000.0
    except:
        budget = 100000.0
    
    # Lazy initialization to avoid circular imports
    from .tools import scrape_car_listings, scrape_real_estate_listings
    from .agent_factory import create_structured_agent_executor, SCRAPER_SYSTEM_PROMPT
    
    tools = [scrape_car_listings, scrape_real_estate_listings]
    executor = create_structured_agent_executor(
        tools=tools,
        system_prompt=SCRAPER_SYSTEM_PROMPT,
        max_iterations=5,
        verbose=False
    )
    
    # Determine what to scrape based on goal
    goal_str = str(goal).lower()
    brand = preferences.get("brand")
    location = preferences.get("location")
    
    if "car" in goal_str or "voiture" in goal_str or "auto" in goal_str:
        agent_input = f"""
Search for cars with budget={budget} TND.
Brand preference: {brand or "any"}
Persona: {persona} (affects filtering)

Call scrape_car_listings with budget={budget}, brand={brand or "None"}, persona={persona}
Return the listings found as a JSON array.
"""
    elif "house" in goal_str or "dar" in goal_str or "appartement" in goal_str or "maison" in goal_str or "property" in goal_str or "real estate" in goal_str or "home" in goal_str:
        agent_input = f"""
Search for real estate with budget={budget} TND.
Location: {location or "any"}
Property type: house/apartment

Call scrape_real_estate_listings with budget={budget}, location={location or "None"}, property_type="house"
Return the listings found as a JSON array.
"""
    else:
        # No clear goal, return empty
        state["listings"] = []
        return state
    
    # Invoke LangChain agent
    print(f"🤖 Scraper Agent (LangChain) processing goal: {goal_str}")
    result = executor.invoke({"input": agent_input})
    agent_output = result.get("output", "")
    tool_outputs = result.get("tool_outputs", [])
    
    # Try to extract listings from tool outputs first (most reliable)
    results = []
    
    # Check if any tool returned listings
    for output in tool_outputs:
        if isinstance(output, dict) and "listings" in output:
            results = output["listings"]
            break
            
    # If no listings in tool outputs, try to parse agent's final text response
    if not results:
        try:
            start = agent_output.find("[")
            end = agent_output.rfind("]") + 1
            if start != -1 and end > start:
                results = json.loads(agent_output[start:end])
        except Exception as e:
            print(f"DEBUG: Failed to parse scraper agent output: {e}")
            
    # ONLY if we still have nothing AND no tool was successfully called, then fallback
    if not results and not tool_outputs:
        print("⚠️ No tool outputs found, using direct scraper fallback")
        if "car" in goal_str:
            results = scrape_automobile_tn(budget, persona, preferences)
        elif "house" in goal_str:
            results = scrape_tecnocasa_tn(budget, location)
        
    state["listings"] = results
    print(f"✅ Scraper Agent found {len(results)} listings")
    return state
