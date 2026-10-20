
import os
import secrets

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import text

from backend.database import engine


# --------------------------------------------------
# ENVIRONMENT CONFIGURATION
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# API KEY AUTHENTICATION
# --------------------------------------------------

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(api_key: str | None = Security(api_key_header)):
    expected_key = os.getenv("SMART_SUPPORT_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured"
        )

    if not api_key or not secrets.compare_digest(api_key, expected_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )


# --------------------------------------------------
# APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Smart Support Desk API",
    description="Order intelligence and support investigation API",
    version="1.0.0",
)


# --------------------------------------------------
# 1. HEALTH CHECK - PUBLIC
# --------------------------------------------------

@app.get("/api/v1/health", tags=["System"])
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected"
    }


# --------------------------------------------------
# 2. GET ORDER DETAILS - PROTECTED
# --------------------------------------------------

@app.get(
    "/api/v1/orders/{order_id}",
    tags=["Orders"],
    dependencies=[Depends(verify_api_key)]
)
def get_order(order_id: str):

    query = text("""
        SELECT
            o.order_id,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,
            c.customer_unique_id,
            c.customer_city,
            c.customer_state
        FROM orders o
        JOIN customers c
            ON o.customer_id = c.customer_id
        WHERE o.order_id = :order_id
    """)

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {"order_id": order_id}
        ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return dict(row)


# --------------------------------------------------
# 3. DETECT POTENTIAL CUSTOMER ISSUES - PROTECTED
# --------------------------------------------------

@app.get(
    "/api/v1/issues",
    tags=["Support Intelligence"],
    dependencies=[Depends(verify_api_key)]
)
def get_potential_issues(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    query = text("""
        WITH review_summary AS (
            SELECT
                order_id,
                MIN(CAST(review_score AS INTEGER))
                    AS lowest_rating
            FROM order_reviews
            WHERE review_score ~ '^[1-5]$'
            GROUP BY order_id
        ),

        flagged AS (
            SELECT
                o.order_id,
                o.order_status,
                c.customer_unique_id,
                c.customer_city,
                c.customer_state,
                r.lowest_rating,

                CASE
                    WHEN
                        o.order_delivered_customer_date <> ''
                        AND o.order_estimated_delivery_date <> ''
                        AND CAST(
                            o.order_delivered_customer_date
                            AS DATE
                        ) > CAST(
                            o.order_estimated_delivery_date
                            AS DATE
                        )
                    THEN TRUE
                    ELSE FALSE
                END AS delivered_late

            FROM orders o

            JOIN customers c
                ON c.customer_id = o.customer_id

            LEFT JOIN review_summary r
                ON r.order_id = o.order_id
        )

        SELECT
            order_id,
            order_status,
            customer_unique_id,
            customer_city,
            customer_state,
            lowest_rating,
            delivered_late,

            CASE
                WHEN lowest_rating <= 2
                     AND delivered_late
                    THEN 'Low rating and late delivery'

                WHEN lowest_rating <= 2
                    THEN 'Low customer rating'

                WHEN delivered_late
                    THEN 'Late delivery'
            END AS issue_reason

        FROM flagged

        WHERE
            lowest_rating <= 2
            OR delivered_late

        ORDER BY
            CASE
                WHEN lowest_rating <= 2
                     AND delivered_late
                THEN 0
                ELSE 1
            END,
            order_id

        LIMIT :limit
        OFFSET :offset
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "limit": limit,
                "offset": offset
            }
        ).mappings().all()

    return {
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "issues": [
            dict(row) for row in rows
        ]
    }


# --------------------------------------------------
# 4. GET CUSTOMER REVIEWS FOR AN ORDER - PROTECTED
# --------------------------------------------------

@app.get(
    "/api/v1/orders/{order_id}/reviews",
    tags=["Investigation"],
    dependencies=[Depends(verify_api_key)]
)
def get_order_reviews(order_id: str):

    query = text("""
        SELECT
            review_id,
            review_score,
            review_comment_title,
            review_comment_message,
            review_creation_date
        FROM order_reviews
        WHERE order_id = :order_id
        ORDER BY review_creation_date DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"order_id": order_id}
        ).mappings().all()

    return {
        "order_id": order_id,
        "count": len(rows),
        "reviews": [
            dict(row) for row in rows
        ]
    }


# --------------------------------------------------
# 5. GET PRODUCTS PURCHASED IN AN ORDER - PROTECTED
# --------------------------------------------------

@app.get(
    "/api/v1/orders/{order_id}/items",
    tags=["Investigation"],
    dependencies=[Depends(verify_api_key)]
)
def get_order_items(order_id: str):

    query = text("""
        SELECT
            oi.order_item_id,
            oi.product_id,
            oi.seller_id,
            oi.price,
            oi.freight_value,

            COALESCE(
                NULLIF(ct.product_category_name_english, ''),
                NULLIF(p.product_category_name, ''),
                'Unknown'
            ) AS product_category

        FROM order_items oi

        LEFT JOIN products p
            ON oi.product_id = p.product_id

        LEFT JOIN category_translations ct
            ON p.product_category_name =
               ct.product_category_name

        WHERE oi.order_id = :order_id

        ORDER BY CAST(oi.order_item_id AS INTEGER)
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"order_id": order_id}
        ).mappings().all()

    return {
        "order_id": order_id,
        "count": len(rows),
        "items": [
            dict(row) for row in rows
        ]
    }


# --------------------------------------------------
# 6. GET CUSTOMER ORDER HISTORY - PROTECTED
# --------------------------------------------------

@app.get(
    "/api/v1/customers/{customer_unique_id}/orders",
    tags=["Investigation"],
    dependencies=[Depends(verify_api_key)]
)
def get_customer_orders(
    customer_unique_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):

    query = text("""
        SELECT
            o.order_id,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date

        FROM orders o

        JOIN customers c
            ON o.customer_id = c.customer_id

        WHERE c.customer_unique_id = :customer_unique_id

        ORDER BY
            o.order_purchase_timestamp DESC,
            o.order_id

        LIMIT :limit
        OFFSET :offset
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "customer_unique_id": customer_unique_id,
                "limit": limit,
                "offset": offset
            }
        ).mappings().all()

    return {
        "customer_unique_id": customer_unique_id,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "orders": [
            dict(row) for row in rows
        ]
    }
