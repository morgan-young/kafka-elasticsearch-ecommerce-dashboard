.PHONY: help install up down seed generator processor api clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies with Poetry"
	@echo "  make up         - Start Docker services"
	@echo "  make down       - Stop Docker services"
	@echo "  make seed       - Seed products (default: 50000)"
	@echo "  make generator  - Start clickstream generator"
	@echo "  make processor  - Start stream processor"
	@echo "  make api        - Start API server"
	@echo "  make clean      - Clean up Docker volumes"

install:
	poetry install

up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10

down:
	docker-compose down

seed:
	poetry run python scripts/seed_products.py $(PRODUCT_COUNT)

generator:
	poetry run python scripts/start_generator.py $(EVENTS_PER_SECOND)

processor:
	poetry run python scripts/start_processor.py

api:
	poetry run uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

clean:
	docker-compose down -v

