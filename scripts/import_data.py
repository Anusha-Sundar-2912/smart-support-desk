
from pathlib import Path
import pandas as pd

from backend.database import engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

TABLES = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "olist_geolocation_dataset.csv": "geolocation",
    "product_category_name_translation.csv": "category_translations",
}


def import_dataset():
    for filename, table_name in TABLES.items():
        file_path = DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Missing file: {file_path}")

        print(f"\nImporting {table_name}...")

        first_chunk = True
        total_rows = 0

        for chunk in pd.read_csv(
            file_path,
            chunksize=5000,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8",
        ):
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="replace" if first_chunk else "append",
                index=False,
                chunksize=1000,
                method="multi",
            )

            first_chunk = False
            total_rows += len(chunk)

        print(f"Imported {total_rows:,} rows into {table_name}")

    print("\nAll nine datasets imported successfully!")


if __name__ == "__main__":
    import_dataset()
