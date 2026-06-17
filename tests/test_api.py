from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from database.models import ProductDimension, StoreDimension, SalesFact

def test_health_check(client: TestClient):
    """
    Tests that the health check status endpoint responds successfully.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_sales_kpis(client: TestClient, db_session: Session):
    """
    Tests retrieving sales KPIs from the backend, pre-populating relational tables.
    """
    # 1. Populate dimensions and sales fact
    prod = ProductDimension(sku_id="SKU001", category="Beverages", brand="BrandA")
    store = StoreDimension(store_id="STORE01", region="Northeast", state="NY", city="New York")
    db_session.add_all([prod, store])
    db_session.commit()

    sale = SalesFact(
        transaction_id="TXN001",
        transaction_timestamp=datetime.utcnow(),
        sku_id="SKU001",
        store_id="STORE01",
        quantity=10,
        unit_price=25.00,
        revenue=250.00,
        currency="USD"
    )
    db_session.add(sale)
    db_session.commit()

    response = client.get("/api/v1/sales/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_quantity" in data
    assert data["total_revenue"] == 250.00
    assert data["total_quantity"] == 10
    assert "Northeast" in data["regions_represented"]

def test_generate_ai_insight(client: TestClient):
    """
    Tests triggering Gemini AI sales summary endpoint.
    """
    payload = {"region": "Northeast", "category": "Beverages"}
    response = client.post("/api/v1/insights/sales-summary", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["insight_type"] == "Sales Summary"
    assert "narrative" in data
    assert "Mock AI Insight" in data["narrative"]

def test_get_regions_and_categories(client: TestClient, db_session: Session):
    """
    Tests retrieving distinct regions and product categories from database.
    """
    # 1. Populate dimensions
    prod1 = ProductDimension(sku_id="SKU001", category="Beverages", brand="BrandA")
    prod2 = ProductDimension(sku_id="SKU002", category="Snacks", brand="BrandB")
    store1 = StoreDimension(store_id="STORE01", region="Northeast", state="NY", city="New York")
    store2 = StoreDimension(store_id="STORE02", region="West", state="CA", city="San Francisco")
    db_session.add_all([prod1, prod2, store1, store2])
    db_session.commit()

    # Test /regions
    res_regions = client.get("/api/v1/sales/regions")
    assert res_regions.status_code == 200
    regions = res_regions.json()
    assert "Northeast" in regions
    assert "West" in regions
    assert len(regions) == 2

    # Test /categories
    res_categories = client.get("/api/v1/sales/categories")
    assert res_categories.status_code == 200
    categories = res_categories.json()
    assert "Beverages" in categories
    assert "Snacks" in categories
    assert len(categories) == 2

