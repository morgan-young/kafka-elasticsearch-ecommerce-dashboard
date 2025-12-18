"""Elasticsearch index setup and configuration."""
from typing import Dict

from elasticsearch import Elasticsearch

from src.config import config


def get_elasticsearch_client() -> Elasticsearch:
    """Get Elasticsearch client."""
    return Elasticsearch([config.ELASTICSEARCH_HOST])


def create_products_index(client: Elasticsearch) -> None:
    """Create products index with autocomplete, fuzziness, and synonyms."""
    index_name = config.ELASTICSEARCH_INDEX_PRODUCTS

    # Check if index exists and delete it
    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    mapping: Dict = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "autocomplete": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "autocomplete_filter"],
                    },
                    "autocomplete_search": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase"],
                    },
                    "synonym_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "synonym_filter"],
                    },
                },
                "filter": {
                    "autocomplete_filter": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20,
                    },
                    "synonym_filter": {
                        "type": "synonym",
                        "synonyms": [
                            "tv,television,televisions",
                            "earbuds,in-ear headphones,earphones",
                            "headphones,headset,cans",
                            "smartphone,phone,mobile phone,cell phone",
                            "laptop,notebook,computer",
                        ],
                    },
                },
            },
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "productId": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {
                        "autocomplete": {
                            "type": "text",
                            "analyzer": "autocomplete",
                            "search_analyzer": "autocomplete_search",
                        },
                        "synonym": {
                            "type": "text",
                            "analyzer": "synonym_analyzer",
                        },
                    },
                    "analyzer": "standard",
                },
                "description": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "category": {
                    "type": "keyword",
                    "fields": {
                        "text": {"type": "text"},
                    },
                },
                "brand": {"type": "keyword"},
                "price": {"type": "float"},
                "rating": {"type": "float"},
                "createdAt": {"type": "date"},
            },
        },
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index: {index_name}")


def create_events_index(client: Elasticsearch) -> None:
    """Create events index for raw clickstream events."""
    index_name = config.ELASTICSEARCH_INDEX_EVENTS

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    mapping: Dict = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "eventId": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "eventType": {"type": "keyword"},
                "userId": {"type": "keyword"},
                "sessionId": {"type": "keyword"},
                "productId": {"type": "keyword"},
                "category": {"type": "keyword"},
                "price": {"type": "float"},
                "userAgent": {"type": "text"},
                "ip": {"type": "ip"},
                "isBot": {"type": "boolean"},
                "conversionStage": {"type": "keyword"},
            },
        },
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index: {index_name}")


def create_trends_index(client: Elasticsearch) -> None:
    """Create product trends index for windowed aggregates."""
    index_name = config.ELASTICSEARCH_INDEX_TRENDS

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    mapping: Dict = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "productId": {"type": "keyword"},
                "windowStart": {"type": "date"},
                "windowEnd": {"type": "date"},
                "viewCount": {"type": "integer"},
                "cartCount": {"type": "integer"},
                "purchaseCount": {"type": "integer"},
                "totalRevenue": {"type": "float"},
            },
        },
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index: {index_name}")


def create_funnels_index(client: Elasticsearch) -> None:
    """Create category funnels index for conversion metrics."""
    index_name = config.ELASTICSEARCH_INDEX_FUNNELS

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    mapping: Dict = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "category": {"type": "keyword"},
                "windowStart": {"type": "date"},
                "windowEnd": {"type": "date"},
                "views": {"type": "integer"},
                "carts": {"type": "integer"},
                "purchases": {"type": "integer"},
                "conversionRate": {"type": "float"},
            },
        },
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index: {index_name}")


def create_fraud_index(client: Elasticsearch) -> None:
    """Create fraud signals index."""
    index_name = config.ELASTICSEARCH_INDEX_FRAUD

    if client.indices.exists(index=index_name):
        client.indices.delete(index=index_name)

    mapping: Dict = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "userId": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "signalType": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "description": {"type": "text"},
                "refundCount": {"type": "integer"},
                "purchaseCount": {"type": "integer"},
                "refundRate": {"type": "float"},
            },
        },
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"Created index: {index_name}")


def setup_all_indices(client: Elasticsearch) -> None:
    """Create all Elasticsearch indices."""
    print("Setting up Elasticsearch indices...")
    create_products_index(client)
    create_events_index(client)
    create_trends_index(client)
    create_funnels_index(client)
    create_fraud_index(client)
    print("All indices created successfully!")

