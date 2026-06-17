import logging
import pandas as pd

logger = logging.getLogger(__name__)

class DataCleaner:
    """
    Skeleton class for transforming and cleaning raw CPG data.
    """
    def __init__(self):
        pass

    def clean_sales(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans sales transactions:
        - Drops duplicates
        - Imputes or drops rows with crucial null columns (transaction_id, sku_id, store_id)
        - Performs currency normalization (e.g. converting non-USD to USD at static rates)
        - Computes 'revenue' if not present (quantity * unit_price)
        """
        logger.info("Starting transformation: Cleaning sales transactions.")
        if df.empty:
            return df
            
        cleaned_df = df.copy()

        # 1. Deduplicate
        cleaned_df = cleaned_df.drop_duplicates(subset=["transaction_id"])

        # 2. Fill standard nulls or drop row if core fields are null
        cleaned_df = cleaned_df.dropna(subset=["transaction_id", "sku_id", "store_id"])

        # 3. Currency normalization (Stub: assume all are converted to USD)
        # cleaned_df['revenue'] = cleaned_df.apply(lambda r: r['quantity'] * r['unit_price'], axis=1)
        if "revenue" not in cleaned_df.columns:
            cleaned_df["revenue"] = cleaned_df["quantity"] * cleaned_df["unit_price"]
        
        logger.info("Finished transformation: Cleaned sales transactions. Count: %d", len(cleaned_df))
        return cleaned_df

    def clean_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans product metadata:
        - Fills null launch dates, category, and brand with sensible defaults.
        """
        logger.info("Starting transformation: Cleaning product dimensions.")
        if df.empty:
            return df
            
        cleaned_df = df.copy()
        cleaned_df["category"] = cleaned_df["category"].fillna("Unknown Category")
        cleaned_df["brand"] = cleaned_df["brand"].fillna("Unknown Brand")
        
        logger.info("Finished transformation: Cleaned product dimensions.")
        return cleaned_df

    def clean_stores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans store geography metadata:
        - Handles capitalization / standardized naming for region, state, and city.
        """
        logger.info("Starting transformation: Cleaning store dimensions.")
        if df.empty:
            return df
            
        cleaned_df = df.copy()
        cleaned_df["region"] = cleaned_df["region"].fillna("Unknown Region").str.strip().str.title()
        cleaned_df["state"] = cleaned_df["state"].fillna("Unknown State").str.strip().str.upper()
        cleaned_df["city"] = cleaned_df["city"].fillna("Unknown City").str.strip().str.title()
        
        logger.info("Finished transformation: Cleaned store dimensions.")
        return cleaned_df
