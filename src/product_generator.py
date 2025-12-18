"""Generate synthetic product catalog."""
import random
from datetime import datetime, timedelta
from typing import Dict, List

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)


# Product categories hierarchy
CATEGORIES = {
    "electronics": {
        "audio": ["headphones", "speakers", "earbuds", "microphones"],
        "computers": ["laptops", "desktops", "tablets", "accessories"],
        "mobile": ["smartphones", "cases", "chargers", "screen-protectors"],
        "tv": ["televisions", "streaming-devices", "soundbars"],
    },
    "clothing": {
        "men": ["shirts", "pants", "shoes", "accessories"],
        "women": ["dresses", "tops", "shoes", "bags"],
        "kids": ["shirts", "pants", "shoes", "toys"],
    },
    "home": {
        "furniture": ["chairs", "tables", "sofas", "beds"],
        "kitchen": ["appliances", "cookware", "utensils"],
        "decor": ["lamps", "art", "rugs", "curtains"],
    },
    "sports": {
        "fitness": ["weights", "mats", "equipment"],
        "outdoor": ["camping", "hiking", "cycling"],
    },
}

# Brands by category
BRANDS = {
    "electronics": ["Sony", "Samsung", "Apple", "LG", "Bose", "JBL", "Dell", "HP"],
    "clothing": ["Nike", "Adidas", "Levi's", "Zara", "H&M", "Gap", "Puma"],
    "home": ["IKEA", "West Elm", "Crate & Barrel", "Target", "Home Depot"],
    "sports": ["Nike", "Adidas", "Under Armour", "Reebok", "Columbia"],
}

# Synonyms for search
SYNONYMS = {
    "tv": ["television", "televisions", "tvs"],
    "television": ["tv", "tvs"],
    "earbuds": ["in-ear headphones", "earphones", "wireless earbuds"],
    "in-ear headphones": ["earbuds", "earphones"],
    "headphones": ["headset", "cans"],
    "smartphone": ["phone", "mobile phone", "cell phone"],
    "laptop": ["notebook", "computer"],
}


def generate_category_path() -> str:
    """Generate a hierarchical category path."""
    top_category = random.choice(list(CATEGORIES.keys()))
    sub_category = random.choice(list(CATEGORIES[top_category].keys()))
    item = random.choice(CATEGORIES[top_category][sub_category])
    return f"{top_category}.{sub_category}.{item}"


def generate_brand(category_path: str) -> str:
    """Generate a brand based on category."""
    top_category = category_path.split(".")[0]
    if top_category in BRANDS:
        return random.choice(BRANDS[top_category])
    return fake.company()


def generate_product(product_id: str) -> Dict:
    """Generate a single synthetic product."""
    category_path = generate_category_path()
    category_parts = category_path.split(".")
    item_name = category_parts[-1]

    # Generate title
    brand = generate_brand(category_path)
    title = f"{brand} {fake.catch_phrase().title()} {item_name.replace('-', ' ').title()}"

    # Generate description
    description = f"{title}. {fake.text(max_nb_chars=200)} Features: {', '.join(fake.words(nb=5))}."

    # Generate price (realistic distribution)
    base_price = random.uniform(10, 2000)
    price = round(base_price, 2)

    # Generate rating
    rating = round(random.uniform(3.0, 5.0), 1)

    # Generate creation date (products created in last 2 years)
    days_ago = random.randint(0, 730)
    created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()

    return {
        "productId": product_id,
        "title": title,
        "description": description,
        "category": category_path,
        "brand": brand,
        "price": price,
        "rating": rating,
        "createdAt": created_at,
    }


def generate_products(count: int) -> List[Dict]:
    """Generate multiple synthetic products."""
    products = []
    for i in range(1, count + 1):
        product_id = f"PROD-{i:06d}"
        products.append(generate_product(product_id))
    return products

