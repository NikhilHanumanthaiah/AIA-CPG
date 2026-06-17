import logging
import io
import time
from datetime import datetime, date
import pandas as pd
from typing import Dict, Any, List, Set
from sqlalchemy.orm import Session

from api.registry import TABLE_REGISTRY
from database.models import UploadAudit

logger = logging.getLogger(__name__)

class UploadService:
    """
    Service to process dynamic table-based CSV file uploads and track audit metrics.
    """
    
    @staticmethod
    def get_supported_tables() -> List[Dict[str, str]]:
        """
        Returns a list of all tables registered in the upload system.
        """
        return [
            {"name": name, "display_name": config["display_name"]}
            for name, config in TABLE_REGISTRY.items()
        ]

    @classmethod
    def process_upload(
        cls, 
        db: Session, 
        file_name: str, 
        file_content: bytes, 
        target_table: str,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Processes the uploaded CSV file for the target table:
        1. Validates table existence.
        2. Validates schema and required columns.
        3. Parses data types.
        4. Detects and filters duplicates (both internal and database-level).
        5. Bulk inserts new records.
        6. Logs execution to UploadAudit.
        """
        start_time = datetime.utcnow()
        start_perf = time.perf_counter()

        # Metrics trackers
        total_rows = 0
        inserted_rows = 0
        duplicate_rows = 0
        invalid_rows = 0

        # Step 1: Validate supported table
        if target_table not in TABLE_REGISTRY:
            error_msg = f"Unsupported target table: {target_table}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        config = TABLE_REGISTRY[target_table]
        model_class = config["model_class"]
        business_key = config["business_key"]
        expected_columns = config["columns"]
        required_columns = config["required_columns"]

        # Step 2: Read CSV file content into staging pandas DataFrame
        if not file_content:
            error_msg = "Uploaded file is empty"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            df = pd.read_csv(io.BytesIO(file_content))
            total_rows = len(df)
        except Exception as e:
            error_msg = f"Failed to parse CSV file: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Step 3: Schema Validation (Check if required columns exist in the file)
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            error_msg = f"Missing mandatory columns for table '{target_table}': {missing_cols}"
            logger.error(error_msg)
            # Log failure to audit table
            cls._log_audit_failure(
                db=db,
                file_name=file_name,
                target_table=target_table,
                total_rows=total_rows,
                error_message=error_msg,
                start_time=start_time,
                created_by=created_by
            )
            raise ValueError(error_msg)

        # Step 4: Validate and Clean records row-by-row
        valid_records: List[Dict[str, Any]] = []
        seen_keys: Set[Any] = set()

        # Fetch existing keys from the database to prevent duplicate inserts
        try:
            existing_db_keys_query = db.query(getattr(model_class, business_key)).all()
            existing_db_keys = {row[0] for row in existing_db_keys_query if row[0] is not None}
        except Exception as e:
            error_msg = f"Database query failed while fetching existing keys: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            is_valid = True
            
            # A. Null check on mandatory/required columns
            for req_col in required_columns:
                val = row_dict.get(req_col)
                if pd.isna(val) or val == "" or str(val).strip() == "":
                    is_valid = False
                    break

            if not is_valid:
                invalid_rows += 1
                continue

            # B. Clean and parse types dynamically based on config
            cleaned_row = {}
            try:
                for col_name, expected_type in expected_columns.items():
                    raw_val = row_dict.get(col_name)
                    if pd.isna(raw_val):
                        cleaned_row[col_name] = None
                        continue

                    # Type conversion
                    if expected_type == str:
                        cleaned_row[col_name] = str(raw_val).strip()
                    elif expected_type == int:
                        cleaned_row[col_name] = int(raw_val)
                    elif expected_type == float:
                        cleaned_row[col_name] = float(raw_val)
                    elif expected_type == date:
                        cleaned_row[col_name] = pd.to_datetime(raw_val).date()
                    elif expected_type == datetime:
                        cleaned_row[col_name] = pd.to_datetime(raw_val).to_pydatetime()
                    else:
                        cleaned_row[col_name] = raw_val
            except Exception:
                # Type conversion failed
                invalid_rows += 1
                continue

            # C. Check business key duplicates
            b_key_val = cleaned_row.get(business_key)
            if b_key_val is None:
                invalid_rows += 1
                continue

            # Duplicate in uploaded file
            if b_key_val in seen_keys:
                duplicate_rows += 1
                continue

            # Duplicate in existing DB
            if b_key_val in existing_db_keys:
                duplicate_rows += 1
                continue

            # Mark as processed and valid
            seen_keys.add(b_key_val)
            valid_records.append(cleaned_row)

        # Step 5: Insert valid records into database
        inserted_rows = len(valid_records)
        error_message = None
        status = "success"

        if valid_records:
            try:
                # Build models and bulk save
                db_instances = [model_class(**record) for record in valid_records]
                db.bulk_save_objects(db_instances)
                db.commit()
                logger.info("Successfully loaded %d records into %s", inserted_rows, target_table)
            except Exception as e:
                db.rollback()
                status = "failed"
                error_message = f"Database write failure: {str(e)}"
                logger.error(error_message)
                inserted_rows = 0
                
                # Write failure audit log
                cls._log_audit_failure(
                    db=db,
                    file_name=file_name,
                    target_table=target_table,
                    total_rows=total_rows,
                    error_message=error_message,
                    start_time=start_time,
                    created_by=created_by
                )
                raise RuntimeError(error_message)

        end_time = datetime.utcnow()
        processing_time_seconds = max(1, int(time.perf_counter() - start_perf))

        # Step 6: Log successful audit
        audit_log = UploadAudit(
            file_name=file_name,
            target_table=target_table,
            total_rows=total_rows,
            inserted_rows=inserted_rows,
            duplicate_rows=duplicate_rows,
            removed_rows=duplicate_rows, # rows removed due to duplication matches duplicate count
            invalid_rows=invalid_rows,
            final_loaded_rows=inserted_rows,
            upload_status=status.upper(),
            error_message=error_message,
            start_time=start_time,
            end_time=end_time,
            created_by=created_by
        )
        
        try:
            db.add(audit_log)
            db.commit()
        except Exception as ae:
            db.rollback()
            logger.error("Failed to save audit log: %s", str(ae))

        return {
            "status": status,
            "table_name": target_table,
            "file_name": file_name,
            "total_rows": total_rows,
            "inserted_rows": inserted_rows,
            "duplicate_rows": duplicate_rows,
            "removed_rows": duplicate_rows,
            "invalid_rows": invalid_rows,
            "final_loaded_rows": inserted_rows,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
            "processing_time_seconds": processing_time_seconds
        }

    @classmethod
    def _log_audit_failure(
        cls,
        db: Session,
        file_name: str,
        target_table: str,
        total_rows: int,
        error_message: str,
        start_time: datetime,
        created_by: str
    ) -> None:
        """
        Helper method to log upload failures to the audit trail database.
        """
        end_time = datetime.utcnow()
        audit_log = UploadAudit(
            file_name=file_name,
            target_table=target_table,
            total_rows=total_rows,
            inserted_rows=0,
            duplicate_rows=0,
            removed_rows=0,
            invalid_rows=0,
            final_loaded_rows=0,
            upload_status="FAILED",
            error_message=error_message[:1000],  # Truncate to match column limits
            start_time=start_time,
            end_time=end_time,
            created_by=created_by
        )
        try:
            db.add(audit_log)
            db.commit()
        except Exception as ae:
            db.rollback()
            logger.error("Failed to save failure audit log: %s", str(ae))
