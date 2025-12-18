"""Configuration settings for the application."""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # Elasticsearch
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
    ELASTICSEARCH_INDEX_PRODUCTS: str = "products"
    ELASTICSEARCH_INDEX_EVENTS: str = "events"
    ELASTICSEARCH_INDEX_TRENDS: str = "product-trends"
    ELASTICSEARCH_INDEX_FUNNELS: str = "category-funnels"
    ELASTICSEARCH_INDEX_FRAUD: str = "fraud-signals"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_SEARCH: str = "search-events"
    KAFKA_TOPIC_PRODUCT: str = "product-events"
    KAFKA_TOPIC_ORDER: str = "order-events"

    # Product Generation
    PRODUCT_COUNT: int = int(os.getenv("PRODUCT_COUNT", "50000"))

    # Clickstream Generation
    EVENTS_PER_SECOND: int = int(os.getenv("EVENTS_PER_SECOND", "100"))
    BOT_TRAFFIC_RATIO: float = float(os.getenv("BOT_TRAFFIC_RATIO", "0.1"))
    FRAUD_RATIO: float = float(os.getenv("FRAUD_RATIO", "0.02"))

    # Stream Processing
    TRENDING_WINDOW_MINUTES: int = 5
    # Number of refunds to flag as fraud
    FRAUD_REFUND_THRESHOLD: int = 3  
    # Minimum purchases required before flagging as fraud
    FRAUD_MIN_PURCHASES: int = 5  


config = Config()

