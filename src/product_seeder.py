"""Seed Elasticsearch with synthetic products."""
import sys
from typing import List

from elasticsearch.helpers import bulk

from src.config import config
from src.elasticsearch_setup import get_elasticsearch_client, setup_all_indices
from src.product_generator import generate_products


def seed_products(count: int) -> None:
    """Generate and index products into Elasticsearch."""
    client = get_elasticsearch_client()

    # Wait for Elasticsearch to be ready
    print("Waiting for Elasticsearch to be ready...")
    client.cluster.health(wait_for_status="yellow", timeout="30s")

    # Setup indices
    setup_all_indices(client)

    # Generate products
    print(f"Generating {count} products...")
    products = generate_products(count)

    # Prepare documents for bulk indexing
    actions = []
    for product in products:
        action = {
            "_index": config.ELASTICSEARCH_INDEX_PRODUCTS,
            "_source": product,
        }
        actions.append(action)

    # Bulk index
    print(f"Indexing {len(actions)} products...")
    success, failed = bulk(client, actions, chunk_size=1000, request_timeout=60)

    print(f"Successfully indexed {success} products")
    if failed:
        print(f"Failed to index {len(failed)} products")

    # Refresh index
    client.indices.refresh(index=config.ELASTICSEARCH_INDEX_PRODUCTS)
    print("Products indexed successfully!")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else config.PRODUCT_COUNT
    seed_products(count)

