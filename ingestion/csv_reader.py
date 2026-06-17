import logging
import pandas as pd
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class CSVReader:
    """
    Skeleton class for reading source CSV datasets and performing initial schema validation.
    """
    def __init__(self, expected_schemas: Dict[str, List[str]] = None):
        # Maps dataset names to lists of expected columns dynamically derived from SQLAlchemy models
        if expected_schemas is not None:
            self.expected_schemas = expected_schemas
        else:
            from database.models import (
                SalesFact,
                ProductDimension,
                StoreDimension,
                CustomerMaster,
                DateDimension,
            )

            def get_cols(model) -> List[str]:
                cols = [c.name for c in model.__table__.columns if not (c.primary_key and c.autoincrement)]
                # Exclude columns computed during transformation pipelines (like sales revenue)
                if model.__tablename__ == "fact_sales" and "revenue" in cols:
                    cols.remove("revenue")
                return cols

            self.expected_schemas = {
                "fact_sales": get_cols(SalesFact),
                "dim_product": get_cols(ProductDimension),
                "dim_store": get_cols(StoreDimension),
                "customer_master": get_cols(CustomerMaster),
                "dim_date": get_cols(DateDimension)
            }

    def read_csv(self, file_path: str, dataset_type: str) -> pd.DataFrame:
        """
        Reads CSV and validates that the schema matches the expected format.
        """
        logger.info("Reading %s CSV from %s", dataset_type, file_path)
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            logger.error("Failed to read CSV from %s: %s", file_path, str(e))
            raise ValueError(f"Could not read CSV file: {str(e)}")
        
        self.validate_schema(df, dataset_type)
        return df

    def validate_schema(self, df: pd.DataFrame, dataset_type: str) -> bool:
        """
        Ensures all expected columns are present in the loaded dataframe.
        """
        if dataset_type not in self.expected_schemas:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
            
        expected_cols = self.expected_schemas[dataset_type]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = f"Schema validation failed for {dataset_type}. Missing columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info("Schema validation succeeded for %s", dataset_type)
        return True

    def run_data_quality_checks(self, df: pd.DataFrame, dataset_type: str) -> Dict[str, Any]:
        """
        Performs basic data quality metrics check (e.g. percentage of nulls, duplicates).
        """
        logger.info("Running data quality checks on %s dataset", dataset_type)
        # Skeleton check: report row counts and null counts
        quality_report = {
            "row_count": len(df),
            "duplicate_count": int(df.duplicated().sum()) if not df.empty else 0,
            "null_counts": df.isnull().sum().to_dict() if not df.empty else {}
        }
        logger.info("Data quality report for %s: %s", dataset_type, quality_report)
        return quality_report
