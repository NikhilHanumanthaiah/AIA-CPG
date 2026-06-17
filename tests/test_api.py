from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """
    Tests that the health check status endpoint responds successfully.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_sales_kpis(client: TestClient):
    """
    Tests retrieving sales KPIs from the backend.
    """
    response = client.get("/api/v1/sales/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_quantity" in data
    assert data["total_revenue"] == 250000.50

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
