# Quick Start Guide

## Step-by-Step Instructions

### 1. Install Dependencies
```bash
poetry install
```

### 2. Start Infrastructure (Docker Services)
```bash
docker-compose up -d
```

Wait 30-60 seconds for services to start. Verify Elasticsearch is ready:
```bash
curl http://localhost:9200
```

### 3. Seed Products
Generate and index products (this may take a few minutes):
```bash
poetry run python scripts/seed_products.py 50000
```

For faster testing, use fewer products:
```bash
poetry run python scripts/seed_products.py 10000
```

### 4. Start All Services

You need **4 terminal windows/tabs** running simultaneously:

#### Terminal 1: Clickstream Generator
```bash
poetry run python scripts/start_generator.py 100
```
This generates 100 events per second. Adjust the number as needed.

#### Terminal 2: Stream Processor
```bash
poetry run python scripts/start_processor.py
```
This processes events and computes analytics.

#### Terminal 3: API Server
```bash
poetry run uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 4: (Optional) Monitor Logs
```bash
docker-compose logs -f
```

### 5. Access the System

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: Open `dashboard.html` in your browser
- **Kibana**: http://localhost:5601 (optional)

## Using Make (Alternative)

If you prefer using Make commands:

```bash
# Install dependencies
make install

# Start Docker services
make up

# Seed products (default: 50000)
make seed
# Or specify count: PRODUCT_COUNT=10000 make seed

# Start services (each in separate terminal)
make generator    # EVENTS_PER_SECOND=100 make generator
make processor
make api
```

## Test the System

### Search Products
```bash
curl "http://localhost:8000/search?q=headphones"
```

### Get Trending Products
```bash
curl "http://localhost:8000/trending"
```

### View Statistics
```bash
curl "http://localhost:8000/stats"
```

### Check Fraud Signals
```bash
curl "http://localhost:8000/fraud"
```

## Troubleshooting

**Elasticsearch not ready?**
```bash
# Wait a bit longer, then check
curl http://localhost:9200
docker-compose logs elasticsearch
```

**Kafka connection errors?**
```bash
# Check Kafka is running
docker-compose ps
docker-compose logs kafka
```

**No events flowing?**
- Ensure clickstream generator is running
- Check stream processor is running
- Verify Kafka topics exist: `docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092`

**Port conflicts?**
- Elasticsearch: 9200
- Kafka: 9092
- API: 8000
- Kibana: 5601

Stop conflicting services or modify ports in `docker-compose.yml`.

## Stop Everything

```bash
# Stop all Python processes (Ctrl+C in each terminal)
# Stop Docker services
docker-compose down

# Or clean everything including volumes
make clean
```

