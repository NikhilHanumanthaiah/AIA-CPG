from datetime import date, datetime
from typing import Any, Dict

from database.models import (
    CustomerMaster,
    ProductDimension,
    SalesFact,
    StoreDimension,
)

TABLE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "dim_product": {
        "display_name": "Product Dimension (dim_product)",
        "model_class": ProductDimension,
        "business_key": "sku_id",
        "columns": {
            "sku_id": str,
            "category": str,
            "brand": str,
            "package_size": str,
            "launch_date": date,
        },
        "required_columns": ["sku_id", "category", "brand"],
    },
    "dim_store": {
        "display_name": "Store Dimension (dim_store)",
        "model_class": StoreDimension,
        "business_key": "store_id",
        "columns": {"store_id": str, "region": str, "state": str, "city": str},
        "required_columns": ["store_id", "region", "state", "city"],
    },
    "fact_sales": {
        "display_name": "Sales Fact (fact_sales)",
        "model_class": SalesFact,
        "business_key": "transaction_id",
        "columns": {
            "transaction_id": str,
            "transaction_timestamp": datetime,
            "sku_id": str,
            "store_id": str,
            "customer_id": str,
            "quantity": int,
            "unit_price": float,
            "revenue": float,
            "currency": str,
        },
        "required_columns": [
            "transaction_id",
            "transaction_timestamp",
            "sku_id",
            "store_id",
            "quantity",
            "unit_price",
        ],
    },
    "customer_master": {
        "display_name": "Customer Master (customer_master)",
        "model_class": CustomerMaster,
        "business_key": "customer_id",
        "columns": {
            "customer_id": str,
            "customer_name": str,
            "email": str,
            "region": str,
        },
        "required_columns": ["customer_id", "customer_name", "email", "region"],
    },
}
