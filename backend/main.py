import os
import secrets
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import text

from backend.database import engine

load_dotenv()

app = FastAPI(
    title="Smart Support Desk API",
    description="Real Olist marketplace order intelligence and Salesforce support integration",
    version="2.0.0",
)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)):
    expected = os.getenv("SMART_SUPPORT_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/api/v1/health", tags=["System"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


@app.get("/api/v1/orders/{order_id}", tags=["Orders"], dependencies=[Depends(verify_api_key)])
def get_order(order_id: str):
    query = text("""
        SELECT o.order_id, o.order_status, o.order_purchase_timestamp,
               o.order_approved_at, o.order_delivered_carrier_date,
               o.order_delivered_customer_date, o.order_estimated_delivery_date,
               c.customer_unique_id, c.customer_city, c.customer_state
        FROM orders o JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = :order_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"order_id": order_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(row)


# One issue category per order, for accurate totals. The underlying signals are
# also returned, so an agent can see multiple problems on the same order.
# The Olist dataset is historical; 'potentially overdue' is measured against
# the latest order purchase date in that dataset, not against today's date.
ISSUE_BASE = """
WITH review_summary AS (
    SELECT order_id,
           MIN(CASE WHEN review_score ~ '^[1-5]$'
                    THEN review_score::integer END) AS lowest_rating
    FROM order_reviews
    GROUP BY order_id
),
snapshot AS (
    SELECT MAX(NULLIF(order_purchase_timestamp, '')::timestamp)::date AS as_of_date
    FROM orders
),
signals AS (
    SELECT o.order_id, o.order_status, c.customer_unique_id,
           c.customer_city, c.customer_state, r.lowest_rating,
           (COALESCE(NULLIF(o.order_delivered_customer_date, '')::timestamp::date
                     > NULLIF(o.order_estimated_delivery_date, '')::timestamp::date,
                     FALSE)) AS delivered_late,
           (LOWER(o.order_status) = 'canceled') AS cancelled,
           (LOWER(o.order_status) = 'unavailable') AS unavailable,
           (LOWER(o.order_status) NOT IN ('delivered', 'canceled', 'unavailable')
            AND NULLIF(o.order_delivered_customer_date, '') IS NULL
            AND COALESCE(NULLIF(o.order_estimated_delivery_date, '')::timestamp::date
                         < snapshot.as_of_date, FALSE)) AS potentially_overdue,
           (COALESCE(r.lowest_rating <= 2, FALSE)) AS low_rating
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    LEFT JOIN review_summary r ON r.order_id = o.order_id
    CROSS JOIN snapshot
),
classified AS (
    SELECT *,
           CASE
               WHEN cancelled THEN 'Cancelled order'
               WHEN unavailable THEN 'Unavailable order'
               WHEN potentially_overdue THEN 'Potentially overdue order'
               WHEN low_rating AND delivered_late THEN 'Low rating and late delivery'
               WHEN low_rating THEN 'Low customer rating'
               WHEN delivered_late THEN 'Late delivery'
           END AS issue_reason,
           CASE
               WHEN potentially_overdue OR unavailable
                    OR (low_rating AND delivered_late) THEN 'High'
               WHEN cancelled OR low_rating OR delivered_late THEN 'Medium'
               ELSE 'Low'
           END AS priority
    FROM signals
),
filtered AS (
    SELECT order_id, order_status, customer_unique_id, customer_city,
           customer_state, lowest_rating, delivered_late, cancelled,
           unavailable, potentially_overdue, low_rating, issue_reason, priority
    FROM classified
    WHERE issue_reason IS NOT NULL
      AND (:issue_type = 'all' OR issue_reason = :issue_type)
      AND (:priority = 'all' OR priority = :priority)
      AND (:rating = 0 OR (:rating = -1 AND lowest_rating IS NULL)
           OR lowest_rating = :rating)
      AND (:order_status = 'all' OR LOWER(order_status) = :order_status)
      AND (:search = '' OR order_id ILIKE :search_pattern ESCAPE '\\'
           OR customer_unique_id ILIKE :search_pattern ESCAPE '\\')
)
"""

ISSUE_TYPES = (
    "Low customer rating", "Late delivery", "Low rating and late delivery",
    "Cancelled order", "Unavailable order", "Potentially overdue order",
)


def issue_params(issue_type: str, priority: str, rating: int,
                 order_status: str, search: str) -> dict:
    escaped = (search.strip().replace("\\", "\\\\")
               .replace("%", "\\%").replace("_", "\\_"))
    return {
        "issue_type": issue_type,
        "priority": priority,
        "rating": rating,
        "order_status": order_status,
        "search": search.strip(),
        "search_pattern": f"%{escaped}%",
    }


@app.get("/api/v1/issues", tags=["Support Intelligence"],
         dependencies=[Depends(verify_api_key)])
def get_potential_issues(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    issue_type: str = Query("all"),
    priority: Literal["all", "High", "Medium", "Low"] = "all",
    rating: int = Query(0, ge=-1, le=5),
    order_status: Literal[
        "all", "delivered", "shipped", "canceled", "unavailable",
        "invoiced", "processing", "created", "approved"
    ] = "all",
    search: str = Query("", max_length=100),
    sort: Literal["overview", "priority", "recent"] = "overview",
):
    if issue_type != "all" and issue_type not in ISSUE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid issue_type")
    params = issue_params(issue_type, priority, rating, order_status, search)
    params.update({"limit": limit, "offset": offset})

    # Balanced overview: round-robin issue categories with a stable order.
    # This is a browsing order, NOT a statistically representative sample.
    if sort == "overview" and issue_type == "all":
        ordering = """
            SELECT order_id, order_status, customer_unique_id, customer_city,
                   customer_state, lowest_rating, delivered_late, cancelled,
                   unavailable, potentially_overdue, low_rating, issue_reason,
                   priority
            FROM (
                SELECT filtered.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY issue_reason ORDER BY order_id
                       ) AS category_position
                FROM filtered
            ) balanced
            ORDER BY category_position, issue_reason, order_id
        """
    else:
        order_clause = (
            "CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, order_id"
            if sort == "priority" else "order_id DESC"
        )
        ordering = f"SELECT * FROM filtered ORDER BY {order_clause}"

    page_sql = text(ISSUE_BASE + ordering + " LIMIT :limit OFFSET :offset")
    count_sql = text(ISSUE_BASE + "SELECT COUNT(*) FROM filtered")
    with engine.connect() as conn:
        total = conn.execute(count_sql, params).scalar_one()
        rows = conn.execute(page_sql, params).mappings().all()
    return {
        "limit": limit, "offset": offset, "count": len(rows),
        "total": total, "has_more": offset + len(rows) < total,
        "sort": sort, "issues": [dict(row) for row in rows],
    }


@app.get("/api/v1/issues/summary", tags=["Support Intelligence"],
         dependencies=[Depends(verify_api_key)])
def get_issue_summary():
    params = issue_params("all", "all", 0, "all", "")
    query = text(ISSUE_BASE + """
        SELECT issue_reason, priority, COUNT(*) AS issue_count
        FROM filtered GROUP BY issue_reason, priority
    """)
    ratings_query = text("""
        SELECT review_score::integer AS rating, COUNT(*) AS review_count
        FROM order_reviews
        WHERE review_score ~ '^[1-5]$'
        GROUP BY review_score::integer
        ORDER BY rating
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, params).mappings().all()
        ratings = conn.execute(ratings_query).mappings().all()
    categories = {name: 0 for name in ISSUE_TYPES}
    priorities = {"High": 0, "Medium": 0, "Low": 0}
    for row in rows:
        categories[row["issue_reason"]] += row["issue_count"]
        priorities[row["priority"]] += row["issue_count"]
    return {
        "total": sum(categories.values()),
        "categories": categories,
        "priorities": priorities,
        "review_rating_distribution": {
            str(row["rating"]): row["review_count"] for row in ratings
        },
        "note": "Historical Olist data. Categories are mutually exclusive; review distribution counts review records.",
    }


@app.get("/api/v1/orders/{order_id}/reviews", tags=["Investigation"],
         dependencies=[Depends(verify_api_key)])
def get_order_reviews(order_id: str):
    query = text("""
        SELECT review_id, review_score, review_comment_title,
               review_comment_message, review_creation_date
        FROM order_reviews WHERE order_id = :order_id
        ORDER BY review_creation_date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"order_id": order_id}).mappings().all()
    return {"order_id": order_id, "count": len(rows),
            "reviews": [dict(row) for row in rows],
            "translation_status": "not_configured"}


@app.get("/api/v1/orders/{order_id}/items", tags=["Investigation"],
         dependencies=[Depends(verify_api_key)])
def get_order_items(order_id: str):
    query = text("""
        SELECT oi.order_item_id, oi.product_id, oi.seller_id,
               oi.price, oi.freight_value,
               COALESCE(NULLIF(ct.product_category_name_english, ''),
                        NULLIF(p.product_category_name, ''),
                        'Unknown') AS product_category
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translations ct
               ON p.product_category_name = ct.product_category_name
        WHERE oi.order_id = :order_id
        ORDER BY CAST(oi.order_item_id AS INTEGER)
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"order_id": order_id}).mappings().all()
    return {"order_id": order_id, "count": len(rows),
            "items": [dict(row) for row in rows]}


@app.get("/api/v1/orders/{order_id}/payments", tags=["Investigation"],
         dependencies=[Depends(verify_api_key)])
def get_order_payments(order_id: str):
    query = text("""
        SELECT payment_sequential, payment_type, payment_installments,
               payment_value
        FROM order_payments WHERE order_id = :order_id
        ORDER BY CAST(payment_sequential AS INTEGER)
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"order_id": order_id}).mappings().all()
    return {"order_id": order_id, "count": len(rows),
            "payments": [dict(row) for row in rows]}


@app.get("/api/v1/customers/{customer_unique_id}/orders",
         tags=["Investigation"], dependencies=[Depends(verify_api_key)])
def get_customer_orders(
    customer_unique_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = text("""
        SELECT o.order_id, o.order_status, o.order_purchase_timestamp,
               o.order_delivered_customer_date, o.order_estimated_delivery_date
        FROM orders o JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.customer_unique_id = :customer_unique_id
        ORDER BY o.order_purchase_timestamp DESC, o.order_id
        LIMIT :limit OFFSET :offset
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {
            "customer_unique_id": customer_unique_id,
            "limit": limit, "offset": offset,
        }).mappings().all()
    return {
        "customer_unique_id": customer_unique_id,
        "count": len(rows), "limit": limit, "offset": offset,
        "orders": [dict(row) for row in rows],
    }
