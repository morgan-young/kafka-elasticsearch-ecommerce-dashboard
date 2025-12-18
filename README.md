# Real-Time E-commerce Analytics & Search Platform

A comprehensive demonstration of event-driven architecture using Kafka for real-time analytics and Elasticsearch for search capabilities. This project generates synthetic e-commerce data at scale and processes it in real-time.

[Here is a Cap](https://cap.link/n5bphac2z483q7s) (Like a Loom but not sh*t now it's owned by Atlassian) of me running through this application.

## Features

- **Product Catalog (Elasticsearch)**: 10k-100k synthetic products with advanced search capabilities
  - Autocomplete with edge_ngram
  - Typo tolerance (fuzziness)
  - Synonym support (tv ↔ television, earbuds ↔ in-ear headphones)
  - Faceted search (category, brand, price)

- **Synthetic Clickstream Generator (Kafka)**: Realistic user behavior simulation
  - Event types: search, view, add_to_cart, purchase, refund
  - Normal user funnels
  - Bot traffic patterns (high search/view, low purchase)
  - Fraud patterns (refund loops, fast refunds)

- **Stream Processing**: Real-time analytics computation
  - Event enrichment
  - Trending products (5-minute windows)
  - Conversion funnels by category
  - Fraud detection (refund loops, abnormal refund rates)

- **Analytics & Search API**: RESTful API for querying data
  - Product search with fuzzy matching
  - Autocomplete suggestions
  - Trending products dashboard
  - Conversion funnel metrics
  - Fraud signal detection

## Architecture

```
┌─────────────────┐
│ Product Seeder  │───> Elasticsearch (Products Index)
└─────────────────┘

┌─────────────────┐
│ Clickstream     │───> Kafka Topics
│ Generator       │    (search-events, product-events, order-events)
└─────────────────┘

┌─────────────────┐
│ Stream          │───> Elasticsearch (Analytics Indices)
│ Processor       │    (trends, funnels, fraud-signals)
└─────────────────┘

┌─────────────────┐
│ FastAPI         │<─── Elasticsearch (All Indices)
│ Demo API        │
└─────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Poetry (for dependency management)

## Setup

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Start infrastructure** (Elasticsearch, Kafka, Zookeeper):
   ```bash
   docker-compose up -d
   ```

   Wait for services to be ready (about 30-60 seconds):
   ```bash
   # Check Elasticsearch
   curl http://localhost:9200
   
   # Check Kafka (requires kafka tools or wait for logs)
   docker-compose logs kafka
   ```

3. **Seed products**:
   ```bash
   poetry run python scripts/seed_products.py 50000
   ```
   This generates and indexes 50,000 products. Adjust the number as needed (10k-100k).

4. **Start clickstream generator** (in a separate terminal):
   ```bash
   poetry run python scripts/start_generator.py 100
   ```
   This generates 100 events per second. Adjust as needed.

5. **Start stream processor** (in a separate terminal):
   ```bash
   poetry run python scripts/start_processor.py
   ```

6. **Start the API server** (in a separate terminal):
   ```bash
   poetry run python -m src.api
   ```
   Or using uvicorn directly:
   ```bash
   poetry run uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Open the dashboard** (optional):
   Open `dashboard.html` in your browser for a visual interface to the analytics.

## Usage

### API Endpoints

#### Search Products
```bash
# Basic search
curl "http://localhost:8000/search?q=headphones"

# Search with fuzzy matching disabled
curl "http://localhost:8000/search?q=headphones&fuzzy=false"

# Search with filters
curl "http://localhost:8000/search?q=laptop&category=electronics.computers.laptops&min_price=500&max_price=2000"
```

#### Autocomplete
```bash
curl "http://localhost:8000/autocomplete?q=hea"
```

#### Trending Products
```bash
# Last 5 minutes (default)
curl "http://localhost:8000/trending"

# Last 10 minutes
curl "http://localhost:8000/trending?minutes=10"
```

#### Conversion Funnels
```bash
curl "http://localhost:8000/funnels?minutes=5"
```

#### Fraud Signals
```bash
# All fraud signals
curl "http://localhost:8000/fraud"

# High severity only
curl "http://localhost:8000/fraud?severity=high"
```

#### Statistics
```bash
curl "http://localhost:8000/stats"
```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Web Dashboard

A simple HTML dashboard is included (`dashboard.html`) that provides:
- Real-time statistics
- Product search interface
- Trending products visualization
- Conversion funnel tables
- Fraud signal monitoring

Open `dashboard.html` in your browser after starting the API server.

## Demo Capabilities

### 1. Search with Typos and Synonyms

The search engine handles:
- **Typos**: "headphons" → finds "headphones" (fuzzy matching)
- **Synonyms**: "tv" → finds "television" products
- **Autocomplete**: "hea" → suggests "headphones", "headset", etc.

Example:
```bash
curl "http://localhost:8000/search?q=tv"
curl "http://localhost:8000/search?q=earbuds"
curl "http://localhost:8000/search?q=smartfone"  # Typo
```

### 2. Live Trending Products

View products trending in real-time:
```bash
curl "http://localhost:8000/trending"
```

### 3. Conversion Funnel Visualization

See conversion rates by category:
```bash
curl "http://localhost:8000/funnels" | jq
```

### 4. Fraud Detection Examples

Identify suspicious users with refund patterns:
```bash
curl "http://localhost:8000/fraud?severity=high" | jq
```

## Configuration

Environment variables (via `.env` file or environment):

- `ELASTICSEARCH_HOST`: Elasticsearch connection (default: `http://localhost:9200`)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka brokers (default: `localhost:9092`)
- `PRODUCT_COUNT`: Number of products to generate (default: `50000`)
- `EVENTS_PER_SECOND`: Clickstream generation rate (default: `100`)
- `BOT_TRAFFIC_RATIO`: Ratio of bot traffic (default: `0.1`)
- `FRAUD_RATIO`: Ratio of fraud users (default: `0.02`)

## Project Structure

```
.
├── docker-compose.yml          # Infrastructure services
├── pyproject.toml              # Poetry dependencies
├── README.md                   # This file
├── scripts/
│   ├── seed_products.py       # Product seeding script
│   ├── start_generator.py     # Clickstream generator
│   └── start_processor.py     # Stream processor
└── src/
    ├── __init__.py
    ├── api.py                 # FastAPI application
    ├── config.py              # Configuration
    ├── clickstream_generator.py  # Event generator
    ├── elasticsearch_setup.py    # Index setup
    ├── product_generator.py      # Product generation
    ├── product_seeder.py         # Product indexing
    └── stream_processor.py       # Stream processing
```

## Elasticsearch Indices

- `products`: Product catalog with search capabilities
- `events`: Raw clickstream events
- `product-trends`: Windowed product aggregates
- `category-funnels`: Conversion metrics by category
- `fraud-signals`: Fraud detection alerts

## Kafka Topics

- `search-events`: User search queries
- `product-events`: Product views and cart additions
- `order-events`: Purchases and refunds

## Performance Considerations

- **Product Count**: 50k products is a good starting point. 100k+ may require more Elasticsearch memory.
- **Event Rate**: 100 events/sec is moderate. Increase for higher load testing.
- **Window Sizes**: Trending products use 5-minute windows. Adjust in `config.py`.
- **Index Settings**: Current setup uses 1 shard, 0 replicas (suitable for local dev).

## Troubleshooting

1. **Elasticsearch not ready**: Wait 30-60 seconds after starting docker-compose
2. **Kafka connection errors**: Ensure Kafka is running and accessible
3. **No events**: Check that clickstream generator is running
4. **No trending data**: Ensure stream processor is running and events are flowing

## What This Demonstrates

- ✅ Event-driven architecture with Kafka
- ✅ Real-time analytics computation
- ✅ Search relevance engineering (autocomplete, fuzziness, synonyms)
- ✅ Synthetic data generation at scale
- ✅ Production-style indexing and aggregation patterns
- ✅ Fraud detection and anomaly detection
- ✅ Conversion funnel analysis

## License

MIT

