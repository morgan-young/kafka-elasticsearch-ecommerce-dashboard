"""Generate synthetic clickstream events and send to Kafka."""
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from elasticsearch import Elasticsearch
from faker import Faker
from kafka import KafkaProducer

from src.config import config

fake = Faker()
random.seed(42)


class UserBehavior:
    """Model user behavior patterns."""

    def __init__(self, user_id: str, is_bot: bool = False, is_fraud: bool = False):
        self.user_id = user_id
        self.is_bot = is_bot
        self.is_fraud = is_fraud
        self.session_id = f"SESSION-{fake.uuid4()}"
        self.products_viewed: List[str] = []
        self.products_in_cart: List[str] = []
        self.purchases: List[Dict] = []
        self.search_queries: List[str] = []

    def generate_search_query(self) -> str:
        """Generate a search query."""
        queries = [
            "headphones",
            "laptop",
            "smartphone",
            "tv",
            "television",
            "earbuds",
            "shoes",
            "dress",
            "chair",
            "table",
        ]
        query = random.choice(queries)
        self.search_queries.append(query)
        return query

    def view_product(self, product_id: str) -> None:
        """Record product view."""
        if product_id not in self.products_viewed:
            self.products_viewed.append(product_id)

    def add_to_cart(self, product_id: str) -> None:
        """Record add to cart."""
        if product_id not in self.products_in_cart:
            self.products_in_cart.append(product_id)

    def purchase(self, product_id: str, price: float) -> Dict:
        """Record purchase."""
        purchase = {"productId": product_id, "price": price, "timestamp": datetime.now()}
        self.purchases.append(purchase)
        return purchase

    def should_refund(self) -> bool:
        """Determine if user should refund (fraud pattern)."""
        if self.is_fraud:
            # Fraud users refund frequently
            return random.random() < 0.7
        return random.random() < 0.05  # Normal users rarely refund


class ClickstreamGenerator:
    """Generate synthetic clickstream events."""

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # Make sends more immediate
            linger_ms=0,  # Don't wait to batch
            batch_size=1,  # Send immediately
        )
        self.users: Dict[str, UserBehavior] = {}
        self.product_ids: List[str] = []
        self.product_cache: Dict[str, tuple] = {}  # Cache product info to avoid ES lookups
        self.event_counter = 0
        self.es = None  # Lazy load Elasticsearch client

    def load_product_ids(self) -> None:
        """Load product IDs from Elasticsearch."""
        from elasticsearch import Elasticsearch

        es = Elasticsearch([config.ELASTICSEARCH_HOST])
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_PRODUCTS,
            body={"size": 10000, "_source": ["productId"]},
        )
        self.product_ids = [hit["_source"]["productId"] for hit in response["hits"]["hits"]]
        print(f"Loaded {len(self.product_ids)} product IDs")

    def get_or_create_user(self, user_id: Optional[str] = None) -> UserBehavior:
        """Get existing user or create new one."""
        if user_id and user_id in self.users:
            return self.users[user_id]

        if not user_id:
            user_id = f"USER-{fake.uuid4()}"

        is_bot = random.random() < config.BOT_TRAFFIC_RATIO
        is_fraud = random.random() < config.FRAUD_RATIO

        user = UserBehavior(user_id, is_bot=is_bot, is_fraud=is_fraud)
        self.users[user_id] = user
        return user

    def generate_search_event(self, user: UserBehavior) -> Dict:
        """Generate a search event."""
        self.event_counter += 1
        query = user.generate_search_query()

        return {
            "eventId": f"EVT-{self.event_counter:010d}",
            "timestamp": datetime.now().isoformat(),
            "eventType": "search",
            "userId": user.user_id,
            "sessionId": user.session_id,
            "query": query,
            "userAgent": fake.user_agent(),
            "ip": fake.ipv4(),
            "isBot": user.is_bot,
        }

    def generate_view_event(self, user: UserBehavior, product_id: str, category: str, price: float) -> Dict:
        """Generate a product view event."""
        self.event_counter += 1
        user.view_product(product_id)

        return {
            "eventId": f"EVT-{self.event_counter:010d}",
            "timestamp": datetime.now().isoformat(),
            "eventType": "view",
            "userId": user.user_id,
            "sessionId": user.session_id,
            "productId": product_id,
            "category": category,
            "price": price,
            "userAgent": fake.user_agent(),
            "ip": fake.ipv4(),
            "isBot": user.is_bot,
            "conversionStage": "view",
        }

    def generate_cart_event(self, user: UserBehavior, product_id: str, category: str, price: float) -> Dict:
        """Generate an add to cart event."""
        self.event_counter += 1
        user.add_to_cart(product_id)

        return {
            "eventId": f"EVT-{self.event_counter:010d}",
            "timestamp": datetime.now().isoformat(),
            "eventType": "add_to_cart",
            "userId": user.user_id,
            "sessionId": user.session_id,
            "productId": product_id,
            "category": category,
            "price": price,
            "userAgent": fake.user_agent(),
            "ip": fake.ipv4(),
            "isBot": user.is_bot,
            "conversionStage": "cart",
        }

    def generate_purchase_event(self, user: UserBehavior, product_id: str, category: str, price: float) -> Dict:
        """Generate a purchase event."""
        self.event_counter += 1
        user.purchase(product_id, price)

        return {
            "eventId": f"EVT-{self.event_counter:010d}",
            "timestamp": datetime.now().isoformat(),
            "eventType": "purchase",
            "userId": user.user_id,
            "sessionId": user.session_id,
            "productId": product_id,
            "category": category,
            "price": price,
            "userAgent": fake.user_agent(),
            "ip": fake.ipv4(),
            "isBot": user.is_bot,
            "conversionStage": "purchase",
        }

    def generate_refund_event(self, user: UserBehavior, purchase: Dict) -> Dict:
        """Generate a refund event."""
        self.event_counter += 1

        return {
            "eventId": f"EVT-{self.event_counter:010d}",
            "timestamp": datetime.now().isoformat(),
            "eventType": "refund",
            "userId": user.user_id,
            "sessionId": user.session_id,
            "productId": purchase["productId"],
            "category": "",  # Will be enriched by stream processor
            "price": purchase["price"],
            "userAgent": fake.user_agent(),
            "ip": fake.ipv4(),
            "isBot": user.is_bot,
            "conversionStage": "refund",
            "originalPurchaseTimestamp": purchase["timestamp"],
        }

    def get_product_info(self) -> tuple:
        """Get random product info."""
        if not self.product_ids:
            return "PROD-000001", "electronics.audio.headphones", 99.99

        product_id = random.choice(self.product_ids)
        
        # Check cache first
        if product_id in self.product_cache:
            return self.product_cache[product_id]
        
        # Try to lookup product from Elasticsearch (with timeout to avoid blocking)
        try:
            if self.es is None:
                self.es = Elasticsearch([config.ELASTICSEARCH_HOST], request_timeout=1)
            
            result = self.es.get(
                index=config.ELASTICSEARCH_INDEX_PRODUCTS,
                id=product_id,
                _source=["category", "price"],
            )
            category = result["_source"].get("category", "electronics.audio.headphones")
            price = result["_source"].get("price", 99.99)
            info = (product_id, category, price)
            # Cache the result
            self.product_cache[product_id] = info
            return info
        except Exception:
            # Fallback to synthetic data if lookup fails (much faster)
            categories = [
                "electronics.audio.headphones",
                "electronics.computers.laptops",
                "electronics.mobile.smartphones",
                "electronics.tv.televisions",
                "clothing.men.shirts",
                "clothing.women.dresses",
                "home.furniture.chairs",
            ]
            category = random.choice(categories)
            price = round(random.uniform(10, 2000), 2)
            info = (product_id, category, price)
            # Cache the result
            self.product_cache[product_id] = info
            return info

    def generate_event_sequence(self, user: UserBehavior) -> List[Dict]:
        """Generate a realistic event sequence for a user."""
        events = []

        # Normal user funnel
        if not user.is_bot:
            # Search
            if random.random() < 0.8:
                events.append(self.generate_search_event(user))

            # View products (1-5 views)
            view_count = random.randint(1, 5) if not user.is_fraud else random.randint(1, 2)
            for _ in range(view_count):
                product_id, category, price = self.get_product_info()
                events.append(self.generate_view_event(user, product_id, category, price))

            # Add to cart (30% of views)
            if user.products_viewed and random.random() < 0.3:
                product_id = random.choice(user.products_viewed)
                _, category, price = self.get_product_info()
                events.append(self.generate_cart_event(user, product_id, category, price))

            # Purchase (50% of carts)
            if user.products_in_cart and random.random() < 0.5:
                product_id = random.choice(user.products_in_cart)
                _, category, price = self.get_product_info()
                purchase_event = self.generate_purchase_event(user, product_id, category, price)
                events.append(purchase_event)

                # Refund (fraud users refund more, and faster)
                if user.should_refund():
                    # Fraud users refund quickly (within minutes), normal users take longer
                    if user.is_fraud:
                        # Generate refund with a small delay (5-30 minutes) for fraud users
                        refund_delay_minutes = random.randint(5, 30)
                        refund_timestamp = (datetime.now() + timedelta(minutes=refund_delay_minutes)).isoformat()
                    else:
                        # Normal users refund after hours or days
                        refund_delay_hours = random.randint(2, 72)
                        refund_timestamp = (datetime.now() + timedelta(hours=refund_delay_hours)).isoformat()
                    
                    refund_event = self.generate_refund_event(user, purchase_event)
                    refund_event["timestamp"] = refund_timestamp
                    events.append(refund_event)

        else:
            # Bot behavior: high search/view, low purchase
            for _ in range(random.randint(10, 50)):
                if random.random() < 0.7:
                    events.append(self.generate_search_event(user))
                else:
                    product_id, category, price = self.get_product_info()
                    events.append(self.generate_view_event(user, product_id, category, price))

        return events

    def send_event(self, event: Dict, topic: str) -> None:
        """Send event to Kafka topic."""
        try:
            future = self.producer.send(topic, value=event)
            # Wait for send to complete to ensure steady rate
            future.get(timeout=1)
        except Exception as e:
            print(f"Error sending event to {topic}: {e}")

    def run(self, events_per_second: int = 100) -> None:
        """Continuously generate and send events."""
        print("Loading product IDs...")
        self.load_product_ids()

        print(f"Starting clickstream generator ({events_per_second} events/sec)...")
        interval = 1.0 / events_per_second
        events_sent = 0
        start_time = time.time()
        last_event_time = time.time()

        try:
            while True:
                # Generate events for a user session
                user = self.get_or_create_user()
                events = self.generate_event_sequence(user)

                # Send events one at a time with proper rate control
                for event in events:
                    event_start = time.time()
                    
                    # Route to appropriate topic
                    if event["eventType"] == "search":
                        self.send_event(event, config.KAFKA_TOPIC_SEARCH)
                    elif event["eventType"] in ["view", "add_to_cart"]:
                        self.send_event(event, config.KAFKA_TOPIC_PRODUCT)
                    elif event["eventType"] in ["purchase", "refund"]:
                        self.send_event(event, config.KAFKA_TOPIC_ORDER)

                    events_sent += 1
                    
                    # Calculate time since last event
                    elapsed_since_last = event_start - last_event_time
                    
                    # Sleep to maintain rate
                    sleep_time = max(0, interval - elapsed_since_last)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
                    last_event_time = time.time()

                # Occasionally start a new session
                if random.random() < 0.3:
                    user.session_id = f"SESSION-{fake.uuid4()}"
                
                # Log rate every 1000 events
                if events_sent % 1000 == 0:
                    elapsed_total = time.time() - start_time
                    actual_rate = events_sent / elapsed_total if elapsed_total > 0 else 0
                    print(f"Sent {events_sent} events, actual rate: {actual_rate:.1f} events/sec")

        except KeyboardInterrupt:
            print("\nStopping clickstream generator...")
            self.producer.close()


if __name__ == "__main__":
    generator = ClickstreamGenerator()
    generator.run(events_per_second=config.EVENTS_PER_SECOND)

