"""Kafka stream processor for real-time analytics."""
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from elasticsearch import Elasticsearch
from kafka import KafkaConsumer, KafkaProducer

from src.config import config


class StreamProcessor:
    """Process Kafka streams and compute real-time analytics."""

    def __init__(self):
        self.es = Elasticsearch([config.ELASTICSEARCH_HOST])
        self.consumer = KafkaConsumer(
            config.KAFKA_TOPIC_SEARCH,
            config.KAFKA_TOPIC_PRODUCT,
            config.KAFKA_TOPIC_ORDER,
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        self.producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        # In-memory windows for trending products (5 minutes)
        self.trending_window = timedelta(minutes=config.TRENDING_WINDOW_MINUTES)
        self.product_events: Dict[str, List[Dict]] = defaultdict(list)
        self.last_trending_flush = time.time()

        # User tracking for fraud detection
        self.user_purchases: Dict[str, List[Dict]] = defaultdict(list)
        self.user_refunds: Dict[str, List[Dict]] = defaultdict(list)

        # Category funnel tracking
        self.category_funnels: Dict[str, Dict[str, int]] = defaultdict(lambda: {"views": 0, "carts": 0, "purchases": 0})
        self.last_funnel_flush = time.time()

    def enrich_event(self, event: Dict) -> Dict:
        """Enrich event with additional data."""
        # Enrich refund events with product category
        if event.get("eventType") == "refund" and not event.get("category"):
            product_id = event.get("productId")
            if product_id:
                try:
                    result = self.es.get(
                        index=config.ELASTICSEARCH_INDEX_PRODUCTS,
                        id=product_id,
                        _source=["category"],
                    )
                    event["category"] = result["_source"].get("category", "")
                except Exception:
                    pass

        return event

    def index_event(self, event: Dict) -> None:
        """Index event to Elasticsearch."""
        try:
            self.es.index(
                index=config.ELASTICSEARCH_INDEX_EVENTS,
                document=event,
            )
        except Exception as e:
            print(f"Error indexing event: {e}")

    def update_trending_products(self, event: Dict) -> None:
        """Update trending products window."""
        if event.get("eventType") not in ["view", "add_to_cart", "purchase"]:
            return

        product_id = event.get("productId")
        if not product_id:
            return

        timestamp = datetime.fromisoformat(event["timestamp"])
        now = datetime.now()

        # Add event to window
        self.product_events[product_id].append(event)

        # Remove old events outside window
        self.product_events[product_id] = [
            e
            for e in self.product_events[product_id]
            if datetime.fromisoformat(e["timestamp"]) > now - self.trending_window
        ]

        # Update aggregate every 30 seconds
        current_time = time.time()
        if current_time - self.last_trending_flush >= 30:
            self.flush_trending_products()
            self.last_trending_flush = current_time

    def flush_trending_products(self) -> None:
        """Flush trending products aggregates to Elasticsearch."""
        if not self.product_events:
            return  # Nothing to flush
        
        now = datetime.now()
        window_start = now - self.trending_window

        flushed_count = 0
        for product_id, events in self.product_events.items():
            view_count = sum(1 for e in events if e.get("eventType") == "view")
            cart_count = sum(1 for e in events if e.get("eventType") == "add_to_cart")
            purchase_count = sum(1 for e in events if e.get("eventType") == "purchase")
            total_revenue = sum(
                e.get("price", 0) for e in events if e.get("eventType") == "purchase"
            )

            if view_count + cart_count + purchase_count > 0:
                trend_doc = {
                    "productId": product_id,
                    "windowStart": window_start.isoformat(),
                    "windowEnd": now.isoformat(),
                    "viewCount": view_count,
                    "cartCount": cart_count,
                    "purchaseCount": purchase_count,
                    "totalRevenue": total_revenue,
                }

                try:
                    # Use productId as document ID to update instead of create duplicates
                    # This ensures we only have one trending record per product
                    self.es.index(
                        index=config.ELASTICSEARCH_INDEX_TRENDS,
                        id=product_id,  # Use productId as document ID
                        document=trend_doc,
                    )
                    flushed_count += 1
                except Exception as e:
                    print(f"Error indexing trend: {e}")

        if flushed_count > 0:
            print(f"Flushed {flushed_count} trending product(s) to Elasticsearch")

    def update_category_funnels(self, event: Dict) -> None:
        """Update category conversion funnels."""
        category = event.get("category")
        if not category:
            return

        event_type = event.get("eventType")
        if event_type == "view":
            self.category_funnels[category]["views"] += 1
        elif event_type == "add_to_cart":
            self.category_funnels[category]["carts"] += 1
        elif event_type == "purchase":
            self.category_funnels[category]["purchases"] += 1

    def flush_category_funnels(self) -> None:
        """Flush category funnel aggregates to Elasticsearch."""
        if not self.category_funnels:
            return  # Nothing to flush
        
        now = datetime.now()
        window_start = now - timedelta(minutes=5)

        flushed_count = 0
        for category, metrics in self.category_funnels.items():
            views = metrics["views"]
            carts = metrics["carts"]
            purchases = metrics["purchases"]
            
            # Only flush if there's actual data
            if views == 0 and carts == 0 and purchases == 0:
                continue
                
            conversion_rate = purchases / views if views > 0 else 0.0

            funnel_doc = {
                "category": category,
                "windowStart": window_start.isoformat(),
                "windowEnd": now.isoformat(),
                "views": views,
                "carts": carts,
                "purchases": purchases,
                "conversionRate": round(conversion_rate, 4),
            }

            try:
                # Use category as document ID to update instead of create duplicates
                # This ensures we only have one funnel record per category
                self.es.index(
                    index=config.ELASTICSEARCH_INDEX_FUNNELS,
                    id=category,  # Use category as document ID
                    document=funnel_doc,
                )
                flushed_count += 1
                print(f"Flushed funnel for {category}: {views} views, {carts} carts, {purchases} purchases")
            except Exception as e:
                print(f"Error indexing funnel: {e}")

        if flushed_count > 0:
            print(f"Flushed {flushed_count} funnel(s) to Elasticsearch")

        # Reset counters after flushing
        self.category_funnels.clear()

    def detect_fraud(self, event: Dict) -> None:
        """Detect fraud patterns."""
        user_id = event.get("userId")
        if not user_id:
            return

        event_type = event.get("eventType")

        if event_type == "purchase":
            self.user_purchases[user_id].append(event)
        elif event_type == "refund":
            self.user_refunds[user_id].append(event)

            # Check for refund loops
            refund_count = len(self.user_refunds[user_id])
            purchase_count = len(self.user_purchases[user_id])

            # Only flag fraud if user has minimum required purchases
            if purchase_count >= config.FRAUD_MIN_PURCHASES:
                refund_rate = refund_count / purchase_count

                # Flag if refund rate is high or refund count exceeds threshold
                if refund_rate > 0.5 or refund_count >= config.FRAUD_REFUND_THRESHOLD:
                    # Check for fast refunds (within 1 hour of purchase)
                    recent_refund = datetime.fromisoformat(event["timestamp"])
                    fast_refunds = 0
                    for purchase in self.user_purchases[user_id]:
                        purchase_time = datetime.fromisoformat(purchase["timestamp"])
                        time_diff = (recent_refund - purchase_time).total_seconds()
                        # Fast refund: within 1 hour (3600 seconds)
                        if 0 < time_diff < 3600:
                            fast_refunds += 1

                    # Generate signal if we have high refund rate/count (with or without fast refunds)
                    # This catches fraud patterns even if timing isn't perfect
                    if refund_rate > 0.5 or refund_count >= config.FRAUD_REFUND_THRESHOLD:
                        severity = "high" if (refund_count >= config.FRAUD_REFUND_THRESHOLD or refund_rate > 0.7) else "medium"
                        
                        signal = {
                            "userId": user_id,
                            "timestamp": event["timestamp"],
                            "signalType": "refund_loop",
                            "severity": severity,
                            "description": f"User has {refund_count} refunds out of {purchase_count} purchases ({refund_rate*100:.1f}% refund rate). {fast_refunds} fast refunds detected." if fast_refunds > 0 else f"User has {refund_count} refunds out of {purchase_count} purchases ({refund_rate*100:.1f}% refund rate).",
                            "refundCount": refund_count,
                            "purchaseCount": purchase_count,
                            "refundRate": round(refund_rate, 4),
                        }

                        try:
                            self.es.index(
                                index=config.ELASTICSEARCH_INDEX_FRAUD,
                                document=signal,
                            )
                            print(f"Fraud signal detected for user {user_id}: {signal['description']}")
                        except Exception as e:
                            print(f"Error indexing fraud signal: {e}")

    def process_event(self, event: Dict) -> None:
        """Process a single event."""
        # Enrich event
        event = self.enrich_event(event)

        # Index raw event
        self.index_event(event)

        # Update analytics
        self.update_trending_products(event)
        self.update_category_funnels(event)
        self.detect_fraud(event)

    def run(self) -> None:
        """Main processing loop."""
        print("Starting stream processor...")
        print(f"Consuming from topics: {config.KAFKA_TOPIC_SEARCH}, {config.KAFKA_TOPIC_PRODUCT}, {config.KAFKA_TOPIC_ORDER}")

        try:
            for message in self.consumer:
                event = message.value
                self.process_event(event)
                
                # Periodic flush check (every event, but only flushes if time elapsed)
                current_time = time.time()
                if current_time - self.last_funnel_flush >= 30:
                    self.flush_category_funnels()
                    self.last_funnel_flush = current_time
                if current_time - self.last_trending_flush >= 30:
                    self.flush_trending_products()
                    self.last_trending_flush = current_time
        except KeyboardInterrupt:
            print("\nStopping stream processor...")
            # Flush any remaining data before stopping
            self.flush_category_funnels()
            self.flush_trending_products()
            self.consumer.close()
            self.producer.close()


if __name__ == "__main__":
    processor = StreamProcessor()
    processor.run()

