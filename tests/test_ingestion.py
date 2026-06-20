import pandas as pd
import pytest

from ingestion.csv_reader import CSVReader
from transformations.cleaner import DataCleaner


def test_csv_reader_validation(tmp_path):
    """
    Tests that CSVReader schema validation passes with correct inputs and fails with incorrect columns.
    """
    reader = CSVReader()

    # 1. Create a valid sales CSV in the temporary directory
    sales_file = tmp_path / "sales.csv"
    sales_file.write_text(
        "transaction_id,transaction_timestamp,sku_id,store_id,customer_id,quantity,unit_price,currency\n"
        "tx_1,2026-06-17T12:00:00Z,SKU001,STORE01,CUST001,10,5.99,USD\n"
    )

    # Read the file
    df_sales = reader.read_csv(str(sales_file), "fact_sales")
    assert len(df_sales) > 0
    assert "transaction_id" in df_sales.columns

    # 1.1 Create and validate customer_master CSV
    cust_file = tmp_path / "customers.csv"
    cust_file.write_text(
        "customer_id,customer_name,email,region\n"
        "CUST001,John Doe,john@example.com,Northeast\n"
    )
    df_cust = reader.read_csv(str(cust_file), "customer_master")
    assert "customer_id" in df_cust.columns

    # 1.2 Create and validate dim_date CSV
    date_file = tmp_path / "date.csv"
    date_file.write_text(
        "date_key,day,week,month,quarter,year,season\n"
        "2026-06-17,17,25,6,2,2026,Summer\n"
    )
    df_date = reader.read_csv(str(date_file), "dim_date")
    assert "date_key" in df_date.columns

    # 2. Test validation failure on corrupted df
    bad_df = pd.DataFrame({"corrupted_id": [1, 2]})
    with pytest.raises(ValueError):
        reader.validate_schema(bad_df, "fact_sales")


def test_data_cleaner():
    """
    Tests that cleaner successfully handles deduplication and calculations.
    """
    cleaner = DataCleaner()

    # Create input with duplicates and missing revenue
    raw_df = pd.DataFrame(
        [
            {
                "transaction_id": "tx_1",
                "transaction_timestamp": "2026-06-17T12:00:00Z",
                "sku_id": "SKU_A",
                "store_id": "STORE_1",
                "quantity": 2,
                "unit_price": 10.0,
                "currency": "USD",
            },
            {
                "transaction_id": "tx_1",  # duplicate ID
                "transaction_timestamp": "2026-06-17T12:05:00Z",
                "sku_id": "SKU_A",
                "store_id": "STORE_1",
                "quantity": 2,
                "unit_price": 10.0,
                "currency": "USD",
            },
        ]
    )

    cleaned_df = cleaner.clean_sales(raw_df)

    # Verify duplicates are dropped
    assert len(cleaned_df) == 1
    # Verify revenue calculation succeeded
    assert cleaned_df.iloc[0]["revenue"] == 20.0
