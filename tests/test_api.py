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
    assert "Fallback" in data["narrative"] or "Mock" in data["narrative"] or "Revenue" in data["narrative"]


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

def test_execute_natural_query(client: TestClient, db_session: Session):
    """
    Tests natural language Text-to-SQL API query execution.
    """
    # 1. Populate some sales data to query
    prod = ProductDimension(sku_id="SKU099", category="Dairy", brand="BrandC")
    store = StoreDimension(store_id="STORE99", region="Northeast", state="NY", city="Albany")
    db_session.add_all([prod, store])
    db_session.commit()

    sale = SalesFact(
        transaction_id="TXN999",
        transaction_timestamp=datetime.utcnow(),
        sku_id="SKU099",
        store_id="STORE99",
        quantity=5,
        unit_price=10.00,
        revenue=50.00,
        currency="USD"
    )
    db_session.add(sale)
    db_session.commit()

    payload = {"question": "What is the total revenue?"}
    response = client.post("/api/v1/insights/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    assert "results" in data
    assert "explanation" in data
    assert len(data["results"]) > 0


def test_forecast_flow(client: TestClient, db_session: Session):
    """
    Tests POST /api/v1/forecast/run and GET /api/v1/forecast/ endpoints.
    """
    from datetime import timedelta
    # 1. Populate test sales data
    prod = ProductDimension(sku_id="SKU100", category="Dairy", brand="BrandD")
    store = StoreDimension(store_id="STORE100", region="West", state="CA", city="San Jose")
    db_session.add_all([prod, store])
    db_session.commit()

    base_time = datetime.utcnow()
    # Add at least 2 sales records to check basic prepare_data / group_by logic
    sale1 = SalesFact(
        transaction_id="TXN101",
        transaction_timestamp=base_time - timedelta(days=1),
        sku_id="SKU100",
        store_id="STORE100",
        quantity=5,
        unit_price=10.00,
        revenue=50.00,
        currency="USD"
    )
    sale2 = SalesFact(
        transaction_id="TXN102",
        transaction_timestamp=base_time,
        sku_id="SKU100",
        store_id="STORE100",
        quantity=6,
        unit_price=10.00,
        revenue=60.00,
        currency="USD"
    )
    db_session.add_all([sale1, sale2])
    db_session.commit()

    # Trigger forecast run via POST
    payload = {
        "days_to_predict": 7,
        "region": "West",
        "category": "Dairy"
    }
    response = client.post("/api/v1/forecast/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Successfully generated" in data["message"]
    assert data["region_filtered"] == "West"
    assert data["category_filtered"] == "Dairy"

    # Verify that GET /api/v1/forecast/ retrieves the results
    get_res = client.get("/api/v1/forecast/?region=West&category=Dairy")
    assert get_res.status_code == 200
    forecast_data = get_res.json()
    assert len(forecast_data) == 7
    for item in forecast_data:
        assert item["region"] == "West"
        assert item["category"] == "Dairy"
        assert "predicted_revenue" in item
        assert "forecast_date" in item



