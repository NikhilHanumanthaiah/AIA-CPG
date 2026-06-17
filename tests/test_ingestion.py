import pytest
import pandas as pd
from ingestion.csv_reader import CSVReader
from transformations.cleaner import DataCleaner

def test_csv_reader_validation():
    """
    Tests that CSVReader schema validation passes with correct inputs and fails with incorrect columns.
    """
    reader = CSVReader()
    
    # 1. Test standard mock reading
    df_sales = reader.read_csv("mock_path.csv", "sales")
    assert len(df_sales) > 0
    assert "transaction_id" in df_sales.columns
    
    # 2. Test validation failure on corrupted df
    bad_df = pd.DataFrame({"corrupted_id": [1, 2]})
    with pytest.raises(ValueError):
        reader.validate_schema(bad_df, "sales")

def test_data_cleaner():
    """
    Tests that cleaner successfully handles deduplication and calculations.
    """
    cleaner = DataCleaner()
    
    # Create input with duplicates and missing revenue
    raw_df = pd.DataFrame([
        {
            "transaction_id": "tx_1",
            "transaction_timestamp": "2026-06-17T12:00:00Z",
            "sku_id": "SKU_A",
            "store_id": "STORE_1",
            "quantity": 2,
            "unit_price": 10.0,
            "currency": "USD"
        },
        {
            "transaction_id": "tx_1", # duplicate ID
            "transaction_timestamp": "2026-06-17T12:05:00Z",
            "sku_id": "SKU_A",
            "store_id": "STORE_1",
            "quantity": 2,
            "unit_price": 10.0,
            "currency": "USD"
        }
    ])
    
    cleaned_df = cleaner.clean_sales(raw_df)
    
    # Verify duplicates are dropped
    assert len(cleaned_df) == 1
    # Verify revenue calculation succeeded
    assert cleaned_df.iloc[0]["revenue"] == 20.0
