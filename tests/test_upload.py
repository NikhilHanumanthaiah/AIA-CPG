import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database.models import CustomerMaster, ProductDimension, UploadAudit

def test_get_uploadable_tables(client: TestClient):
    """
    Tests GET /api/v1/upload/tables endpoint format and registered tables.
    """
    response = client.get("/api/v1/upload/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    tables = data["tables"]
    assert len(tables) == 4
    table_names = [t["name"] for t in tables]
    assert "customer_master" in table_names
    assert "dim_product" in table_names
    assert "dim_store" in table_names
    assert "fact_sales" in table_names

def test_upload_valid_customer_master(client: TestClient, db_session: Session):
    """
    Tests uploading a valid customer_master CSV.
    Checks that records are inserted, counts are accurate, and an UploadAudit record is generated.
    """
    csv_content = (
        "customer_id,customer_name,email,region\n"
        "CUST001,John Doe,john@example.com,Northeast\n"
        "CUST002,Jane Smith,jane@example.com,West\n"
    )
    file_payload = {
        "file": ("customers.csv", csv_content, "text/csv")
    }
    form_payload = {
        "target_table": "customer_master"
    }
    
    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["table_name"] == "customer_master"
    assert data["total_rows"] == 2
    assert data["inserted_rows"] == 2
    assert data["duplicate_rows"] == 0
    assert data["invalid_rows"] == 0
    assert data["final_loaded_rows"] == 2

    # Verify that records exist in database
    db_customers = db_session.query(CustomerMaster).all()
    assert len(db_customers) == 2
    c_ids = [c.customer_id for c in db_customers]
    assert "CUST001" in c_ids
    assert "CUST002" in c_ids

    # Verify UploadAudit is logged
    audits = db_session.query(UploadAudit).all()
    assert len(audits) == 1
    assert audits[0].target_table == "customer_master"
    assert audits[0].file_name == "customers.csv"
    assert audits[0].upload_status == "SUCCESS"
    assert audits[0].final_loaded_rows == 2

def test_upload_duplicate_filtering(client: TestClient, db_session: Session):
    """
    Tests that duplicate keys in the uploaded file and against the DB are filtered correctly.
    """
    # Pre-populate the DB with CUST001
    existing_customer = CustomerMaster(
        customer_id="CUST001",
        customer_name="Pre Existing",
        email="pre@example.com",
        region="South"
    )
    db_session.add(existing_customer)
    db_session.commit()

    # CSV contains:
    # 1. CUST001 (Duplicate against DB)
    # 2. CUST002 (Valid)
    # 3. CUST002 (Duplicate in-file)
    csv_content = (
        "customer_id,customer_name,email,region\n"
        "CUST001,John Doe,john@example.com,Northeast\n"
        "CUST002,Jane Smith,jane@example.com,West\n"
        "CUST002,Duplicate Jane,jane2@example.com,West\n"
    )
    file_payload = {
        "file": ("customers.csv", csv_content, "text/csv")
    }
    form_payload = {
        "target_table": "customer_master"
    }

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_rows"] == 3
    assert data["inserted_rows"] == 1  # only CUST002
    assert data["duplicate_rows"] == 2  # CUST001 and second CUST002
    assert data["final_loaded_rows"] == 1

    # Verify db counts
    db_customers = db_session.query(CustomerMaster).all()
    assert len(db_customers) == 2  # CUST001 (pre-existing) + CUST002 (inserted)

def test_upload_missing_mandatory_columns(client: TestClient, db_session: Session):
    """
    Tests that missing required columns return HTTP 400 and log a FAILED audit.
    """
    # customer_name is missing
    csv_content = (
        "customer_id,email,region\n"
        "CUST001,john@example.com,Northeast\n"
    )
    file_payload = {
        "file": ("customers.csv", csv_content, "text/csv")
    }
    form_payload = {
        "target_table": "customer_master"
    }

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 400
    assert "Missing mandatory columns" in response.json()["detail"]

    # Verify audit failure is logged
    audits = db_session.query(UploadAudit).all()
    assert len(audits) == 1
    assert audits[0].upload_status == "FAILED"
    assert "Missing mandatory columns" in audits[0].error_message

def test_upload_unsupported_table(client: TestClient):
    """
    Tests that selecting an unsupported table returns HTTP 400.
    """
    csv_content = "col1,col2\nval1,val2\n"
    file_payload = {
        "file": ("file.csv", csv_content, "text/csv")
    }
    form_payload = {
        "target_table": "invalid_table"
    }

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 400
    assert "Unsupported target table" in response.json()["detail"]


def test_upload_valid_dim_product(client: TestClient, db_session: Session):
    """
    Tests uploading a valid dim_product CSV.
    """
    csv_content = (
        "sku_id,category,brand,package_size,launch_date\n"
        "SKU001,Beverages,BrandX,12pk,2026-01-01\n"
        "SKU002,Snacks,BrandY,6pk,2026-02-01\n"
    )
    file_payload = {
        "file": ("products.csv", csv_content, "text/csv")
    }
    form_payload = {
        "target_table": "dim_product"
    }

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["table_name"] == "dim_product"
    assert data["total_rows"] == 2
    assert data["inserted_rows"] == 2

    db_products = db_session.query(ProductDimension).all()
    assert len(db_products) == 2
    sku_ids = [p.sku_id for p in db_products]
    assert "SKU001" in sku_ids
    assert "SKU002" in sku_ids
