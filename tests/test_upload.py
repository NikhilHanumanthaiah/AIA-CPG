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
    file_payload = {"file": ("customers.csv", csv_content, "text/csv")}
    form_payload = {"target_table": "customer_master"}

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
        region="South",
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
    file_payload = {"file": ("customers.csv", csv_content, "text/csv")}
    form_payload = {"target_table": "customer_master"}

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
    csv_content = "customer_id,email,region\n" "CUST001,john@example.com,Northeast\n"
    file_payload = {"file": ("customers.csv", csv_content, "text/csv")}
    form_payload = {"target_table": "customer_master"}

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
    file_payload = {"file": ("file.csv", csv_content, "text/csv")}
    form_payload = {"target_table": "invalid_table"}

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
    file_payload = {"file": ("products.csv", csv_content, "text/csv")}
    form_payload = {"target_table": "dim_product"}

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


def test_dynamic_upload_flow(client: TestClient, db_session: Session):
    """
    Tests uploading a sales CSV with schema drift, custom type casting,
    currency conversions, calculated revenue, and positive quantity validation.
    """
    import json

    from database.models import ProductDimension, SalesFact, StoreDimension

    prod = ProductDimension(sku_id="SKU999", category="Beverages", brand="BrandA")
    store = StoreDimension(
        store_id="STORE999", region="Northeast", state="NY", city="New York"
    )
    db_session.add_all([prod, store])
    db_session.commit()

    csv_content = (
        "txn_id,timestamp,sku,store,qty,price,currency\n"
        "TXNDYN001,2026-06-19 12:00:00,SKU999,STORE999,10,15.00,EUR\n"
        "TXNDYN002,2026-06-19 13:00:00,SKU999,STORE999,-5,10.00,USD\n"
    )

    file_payload = {"file": ("sales_dynamic.csv", csv_content, "text/csv")}

    column_mapping = {
        "transaction_id": "txn_id",
        "transaction_timestamp": "timestamp",
        "sku_id": "sku",
        "store_id": "store",
        "quantity": "qty",
        "unit_price": "price",
        "currency": "currency",
    }

    data_types = {"quantity": "int", "unit_price": "float"}

    dq_rules = {
        "quantity": ["positive"],
        "currency_normalize": True,
        "calculate_revenue": True,
    }

    form_payload = {
        "target_table": "fact_sales",
        "column_mapping": json.dumps(column_mapping),
        "data_types": json.dumps(data_types),
        "dq_rules": json.dumps(dq_rules),
    }

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["total_rows"] == 2
    assert data["inserted_rows"] == 1
    assert data["invalid_rows"] == 1
    assert data["final_loaded_rows"] == 1

    db_sales = (
        db_session.query(SalesFact)
        .filter(SalesFact.transaction_id == "TXNDYN001")
        .all()
    )
    assert len(db_sales) == 1
    sale = db_sales[0]
    assert sale.currency == "USD"
    assert float(sale.unit_price) == 16.50
    assert float(sale.revenue) == 165.0

    validation_errors = data["validation_errors"]
    assert len(validation_errors) == 1
    err = validation_errors[0]
    assert err["row_index"] == 2
    assert err["column"] == "quantity"
    assert "strictly positive" in err["reason"]


def test_upload_with_string_data_quality_rules(client: TestClient, db_session: Session):
    """
    Tests uploading a customer master CSV with custom string DQ validation rules:
    - Email format check
    - Minimum length check
    - Allowed options list check
    """
    import json

    csv_content = (
        "customer_id,customer_name,email,region\n"
        "CUSTST1,Alice,alice@example.com,Northeast\n"  # Valid
        "CUSTST2,Bob,bob_invalid_email,West\n"  # Invalid email
        "CUSTST3,C,c@example.com,South\n"  # Name too short
        "CUSTST4,David,david@example.com,InvalidRegion\n"  # Region not in allowed options
    )

    file_payload = {"file": ("customers_dq.csv", csv_content, "text/csv")}

    dq_rules = {
        "email": ["email"],
        "customer_name": ["min_length:3"],
        "region": ["allowed_options:Northeast,West,South"],
    }

    form_payload = {"target_table": "customer_master", "dq_rules": json.dumps(dq_rules)}

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["total_rows"] == 4
    assert data["inserted_rows"] == 1
    assert data["invalid_rows"] == 3

    validation_errors = data["validation_errors"]
    assert len(validation_errors) == 3

    reasons = [err["reason"] for err in validation_errors]
    cols = [err["column"] for err in validation_errors]

    assert "email" in cols
    assert "customer_name" in cols
    assert "region" in cols

    assert any("valid email format" in r for r in reasons)
    assert any("at least 3 characters" in r for r in reasons)
    assert any("allowed options" in r for r in reasons)


def test_upload_with_multiple_rules_and_limits(client: TestClient, db_session: Session):
    """
    Tests uploading a sales CSV with multiple rules per column:
    - quantity: positive AND min_val:2 AND max_val:50
    - sku_id: min_length:3 AND max_length:6
    """
    import json

    from database.models import ProductDimension, SalesFact, StoreDimension

    prod = ProductDimension(sku_id="SKU1", category="Beverages", brand="BrandA")
    store = StoreDimension(
        store_id="ST1", region="Northeast", state="NY", city="New York"
    )
    db_session.add_all([prod, store])
    db_session.commit()

    csv_content = (
        "transaction_id,transaction_timestamp,sku_id,store_id,quantity,unit_price,currency\n"
        "TXNMLT001,2026-06-19 12:00:00,SKU1,ST1,10,15.00,USD\n"  # Valid
        "TXNMLT002,2026-06-19 13:00:00,SKU1,ST1,1,10.00,USD\n"  # Invalid: quantity below min_val:2
        "TXNMLT003,2026-06-19 14:00:00,SKU1,ST1,100,10.00,USD\n"  # Invalid: quantity above max_val:50
        "TXNMLT004,2026-06-19 15:00:00,S,ST1,10,10.00,USD\n"  # Invalid: sku_id below min_length:3
        "TXNMLT005,2026-06-19 16:00:00,SKU1LONG,ST1,10,10.00,USD\n"  # Invalid: sku_id above max_length:6
    )

    file_payload = {"file": ("sales_multiple.csv", csv_content, "text/csv")}

    dq_rules = {
        "quantity": ["positive", "min_val:2", "max_val:50"],
        "sku_id": ["min_length:3", "max_length:6"],
        "calculate_revenue": True,
    }

    form_payload = {"target_table": "fact_sales", "dq_rules": json.dumps(dq_rules)}

    response = client.post("/api/v1/upload/", files=file_payload, data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["total_rows"] == 5
    assert data["inserted_rows"] == 1
    assert data["invalid_rows"] == 4

    validation_errors = data["validation_errors"]
    assert len(validation_errors) == 4

    cols = [err["column"] for err in validation_errors]
    reasons = [err["reason"] for err in validation_errors]

    assert cols.count("quantity") == 2
    assert cols.count("sku_id") == 2

    assert any("below minimum limit" in r for r in reasons)
    assert any("exceeds upper bound" in r for r in reasons)
    assert any("at least 3 characters" in r for r in reasons)
    assert any("exceeds maximum of 6 characters" in r for r in reasons)
