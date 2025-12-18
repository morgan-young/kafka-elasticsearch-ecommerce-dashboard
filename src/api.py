"""FastAPI demo application for search and analytics."""
from datetime import datetime, timedelta
from typing import List, Optional

from elasticsearch import Elasticsearch
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import config

app = FastAPI(title="E-commerce Analytics & Search API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es = Elasticsearch([config.ELASTICSEARCH_HOST])


# Response models
class Product(BaseModel):
    productId: str
    title: str
    description: str
    category: str
    brand: str
    price: float
    rating: float
    createdAt: str


class TrendingProduct(BaseModel):
    productId: str
    viewCount: int
    cartCount: int
    purchaseCount: int
    totalRevenue: float


class CategoryFunnel(BaseModel):
    category: str
    views: int
    carts: int
    purchases: int
    conversionRate: float


class FraudSignal(BaseModel):
    userId: str
    timestamp: str
    signalType: str
    severity: str
    description: str
    refundCount: int
    purchaseCount: int
    refundRate: float


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "E-commerce Analytics & Search API",
        "endpoints": {
            "search": "/search?q=query",
            "autocomplete": "/autocomplete?q=query",
            "trending": "/trending",
            "funnels": "/funnels",
            "fraud": "/fraud",
        },
    }


@app.get("/search", response_model=List[Product])
async def search_products(
    q: str = Query(..., description="Search query"),
    fuzzy: bool = Query(True, description="Enable fuzzy matching"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    size: int = Query(20, description="Number of results"),
):
    """Search products with autocomplete, fuzzy matching, and filters."""
    must_clauses = []

    # Text search with fuzzy matching
    if fuzzy:
        must_clauses.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "title.synonym^2", "description"],
                    "fuzziness": "AUTO",
                    "type": "best_fields",
                }
            }
        )
    else:
        must_clauses.append(
            {
                "multi_match": {
                    "query": q,
                    "fields": ["title^3", "title.synonym^2", "description"],
                }
            }
        )

    # Filters
    if category:
        must_clauses.append({"term": {"category": category}})

    if brand:
        must_clauses.append({"term": {"brand": brand}})

    if min_price is not None or max_price is not None:
        price_range = {}
        if min_price is not None:
            price_range["gte"] = min_price
        if max_price is not None:
            price_range["lte"] = max_price
        must_clauses.append({"range": {"price": price_range}})

    query = {"bool": {"must": must_clauses}}

    try:
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_PRODUCTS,
            body={"query": query, "size": size},
        )

        products = []
        for hit in response["hits"]["hits"]:
            products.append(Product(**hit["_source"]))

        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/autocomplete", response_model=List[str])
async def autocomplete(
    q: str = Query(..., description="Autocomplete query"),
    size: int = Query(10, description="Number of suggestions"),
):
    """Get autocomplete suggestions."""
    query = {
        "match": {
            "title.autocomplete": {
                "query": q,
                "operator": "or",  # Use "or" for more flexible autocomplete
            }
        }
    }

    try:
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_PRODUCTS,
            body={
                "query": query,
                "size": size,
                "_source": ["title"],
            },
        )

        suggestions = [hit["_source"]["title"] for hit in response["hits"]["hits"]]
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trending", response_model=List[TrendingProduct])
async def get_trending_products(
    minutes: int = Query(5, description="Time window in minutes"),
    size: int = Query(10, description="Number of results"),
):
    """Get trending products in the last N minutes."""
    now = datetime.now()
    window_start = now - timedelta(minutes=minutes)

    query = {
        "bool": {
            "must": [
                {
                    "range": {
                        "windowEnd": {
                            "gte": window_start.isoformat(),
                        }
                    }
                }
            ]
        }
    }

    try:
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_TRENDS,
            body={
                "query": query,
                "size": size,
                "sort": [{"viewCount": {"order": "desc"}}],
            },
        )

        trends = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            trends.append(
                TrendingProduct(
                    productId=source["productId"],
                    viewCount=source.get("viewCount", 0),
                    cartCount=source.get("cartCount", 0),
                    purchaseCount=source.get("purchaseCount", 0),
                    totalRevenue=source.get("totalRevenue", 0.0),
                )
            )

        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/funnels", response_model=List[CategoryFunnel])
async def get_category_funnels(
    minutes: int = Query(10, description="Time window in minutes"),
):
    """Get conversion funnels by category."""
    now = datetime.now()
    window_start = now - timedelta(minutes=minutes)

    # More lenient query - get all recent funnels, not just those ending in the window
    query = {
        "bool": {
            "should": [
                {
                    "range": {
                        "windowEnd": {
                            "gte": window_start.isoformat(),
                        }
                    }
                },
                {
                    "range": {
                        "windowStart": {
                            "gte": window_start.isoformat(),
                        }
                    }
                }
            ],
            "minimum_should_match": 1,
        }
    }

    try:
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_FUNNELS,
            body={
                "query": query,
                "size": 100,
                "sort": [{"windowEnd": {"order": "desc"}}],
            },
        )

        funnels = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            funnels.append(
                CategoryFunnel(
                    category=source["category"],
                    views=source.get("views", 0),
                    carts=source.get("carts", 0),
                    purchases=source.get("purchases", 0),
                    conversionRate=source.get("conversionRate", 0.0),
                )
            )

        return funnels
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fraud", response_model=List[FraudSignal])
async def get_fraud_signals(
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high)"),
    size: int = Query(50, description="Number of results"),
):
    """Get fraud detection signals."""
    query = {"match_all": {}}

    if severity:
        query = {"term": {"severity": severity}}

    try:
        response = es.search(
            index=config.ELASTICSEARCH_INDEX_FRAUD,
            body={
                "query": query,
                "size": size,
                "sort": [{"timestamp": {"order": "desc"}}],
            },
        )

        signals = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            signals.append(
                FraudSignal(
                    userId=source["userId"],
                    timestamp=source["timestamp"],
                    signalType=source["signalType"],
                    severity=source["severity"],
                    description=source["description"],
                    refundCount=source.get("refundCount", 0),
                    purchaseCount=source.get("purchaseCount", 0),
                    refundRate=source.get("refundRate", 0.0),
                )
            )

        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get overall statistics."""
    try:
        # Product count
        product_count = es.count(index=config.ELASTICSEARCH_INDEX_PRODUCTS)["count"]

        # Event count (last hour)
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        event_count = es.count(
            index=config.ELASTICSEARCH_INDEX_EVENTS,
            body={
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": hour_ago,
                        }
                    }
                }
            },
        )["count"]

        # Trending products count
        trending_count = es.count(index=config.ELASTICSEARCH_INDEX_TRENDS)["count"]

        # Fraud signals count
        fraud_count = es.count(index=config.ELASTICSEARCH_INDEX_FRAUD)["count"]

        return {
            "products": product_count,
            "eventsLastHour": event_count,
            "trendingProducts": trending_count,
            "fraudSignals": fraud_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

