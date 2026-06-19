import logging
import io
import time
import json
from datetime import datetime, date
import pandas as pd
from typing import Dict, Any, List, Set, Optional
from sqlalchemy.orm import Session

from api.registry import TABLE_REGISTRY
from database.models import UploadAudit

logger = logging.getLogger(__name__)

class UploadService:
    """
    Service to process dynamic table-based CSV file uploads and track audit metrics.
    """
    
    @staticmethod
    def get_supported_tables() -> List[Dict[str, Any]]:
        """
        Returns a list of all tables registered in the upload system.
        """
        result = []
        for name, config in TABLE_REGISTRY.items():
            cols = {}
            for col_name, col_type in config["columns"].items():
                cols[col_name] = col_type.__name__ if hasattr(col_type, "__name__") else str(col_type)
            result.append({
                "name": name,
                "display_name": config["display_name"],
                "columns": cols,
                "required_columns": config["required_columns"]
            })
        return result

    @classmethod
    def process_upload(
        cls, 
        db: Session, 
        file_name: str, 
        file_content: bytes, 
        target_table: str,
        created_by: str = "system",
        column_mapping: Optional[str] = None,
        data_types: Optional[str] = None,
        dq_rules: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes the uploaded CSV file for the target table:
        1. Validates table existence.
        2. Renames columns using column_mapping.
        3. Standardizes data types with casting and overrides.
        4. Validates custom data quality and business constraints.
        5. Detects duplicates and performs partial loading of clean rows.
        6. Logs execution to UploadAudit.
        """
        start_time = datetime.utcnow()
        start_perf = time.perf_counter()

        # Metrics trackers
        total_rows = 0
        inserted_rows = 0
        duplicate_rows = 0
        invalid_rows = 0
        validation_errors: List[Dict[str, Any]] = []

        # Parse configurations
        mapping_dict = json.loads(column_mapping) if column_mapping else {}
        type_overrides = json.loads(data_types) if data_types else {}
        rules_dict = json.loads(dq_rules) if dq_rules else {}

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

        # Apply Column Mapping dynamically
        if mapping_dict:
            reverse_mapping = {v: k for k, v in mapping_dict.items() if v}
            df = df.rename(columns=reverse_mapping)

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
            row_errors = []
            
            # A. Null check on mandatory/required columns
            for req_col in required_columns:
                val = row_dict.get(req_col)
                if pd.isna(val) or val == "" or str(val).strip() == "":
                    is_valid = False
                    row_errors.append({
                        "row_index": idx + 1,
                        "column": req_col,
                        "value": str(val) if not pd.isna(val) else None,
                        "reason": f"Required column '{req_col}' is missing or empty"
                    })
                    break

            if not is_valid:
                invalid_rows += 1
                validation_errors.extend(row_errors)
                continue

            # B. Clean and parse types dynamically based on overrides or default config
            cleaned_row = {}
            type_error = False
            for col_name, default_type in expected_columns.items():
                raw_val = row_dict.get(col_name)
                if pd.isna(raw_val):
                    cleaned_row[col_name] = None
                    continue

                type_str = type_overrides.get(col_name)
                if type_str == "str":
                    expected_type = str
                elif type_str == "int":
                    expected_type = int
                elif type_str == "float":
                    expected_type = float
                elif type_str == "date":
                    expected_type = date
                elif type_str == "datetime":
                    expected_type = datetime
                else:
                    expected_type = default_type

                try:
                    if expected_type in (int, float):
                        s_val = str(raw_val).strip()
                        s_val = s_val.replace("$", "").replace("€", "").replace("£", "").replace(",", "")
                        if expected_type == int:
                            cleaned_row[col_name] = int(float(s_val))
                        else:
                            cleaned_row[col_name] = float(s_val)
                    elif expected_type == str:
                        cleaned_row[col_name] = str(raw_val).strip()
                    elif expected_type == date:
                        cleaned_row[col_name] = pd.to_datetime(raw_val).date()
                    elif expected_type == datetime:
                        dt_parsed = pd.to_datetime(raw_val)
                        if dt_parsed.tzinfo is not None:
                            cleaned_row[col_name] = dt_parsed.tz_convert(None).to_pydatetime()
                        else:
                            cleaned_row[col_name] = dt_parsed.to_pydatetime()
                    else:
                        cleaned_row[col_name] = raw_val
                except Exception as e:
                    type_error = True
                    validation_errors.append({
                        "row_index": idx + 1,
                        "column": col_name,
                        "value": str(raw_val),
                        "reason": f"Type casting to {expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)} failed: {str(e)}"
                    })
                    break

            if type_error:
                invalid_rows += 1
                continue

            # C. Custom Data Quality Rules check
            dq_error = False
            for col_name, rules in rules_dict.items():
                if not isinstance(rules, list):
                    continue
                if col_name not in cleaned_row or cleaned_row[col_name] is None:
                    continue
                
                val = cleaned_row[col_name]
                for rule in rules:
                    if rule == "positive":
                        if not (isinstance(val, (int, float)) and val > 0):
                            dq_error = True
                            validation_errors.append({
                                "row_index": idx + 1,
                                "column": col_name,
                                "value": str(val),
                                "reason": "Value must be strictly positive (> 0)"
                            })
                            break
                    elif rule == "non_negative":
                        if not (isinstance(val, (int, float)) and val >= 0):
                            dq_error = True
                            validation_errors.append({
                                "row_index": idx + 1,
                                "column": col_name,
                                "value": str(val),
                                "reason": "Value must be non-negative (>= 0)"
                            })
                            break
                    elif rule.startswith("max_val:"):
                        try:
                            limit = float(rule.split(":")[1])
                            if not (isinstance(val, (int, float)) and val <= limit):
                                dq_error = True
                                validation_errors.append({
                                    "row_index": idx + 1,
                                    "column": col_name,
                                    "value": str(val),
                                    "reason": f"Value exceeds upper bound limit of {limit}"
                                })
                                break
                        except Exception:
                            pass
                    elif rule.startswith("min_val:"):
                        try:
                            limit = float(rule.split(":")[1])
                            if not (isinstance(val, (int, float)) and val >= limit):
                                dq_error = True
                                validation_errors.append({
                                    "row_index": idx + 1,
                                    "column": col_name,
                                    "value": str(val),
                                    "reason": f"Value is below minimum limit of {limit}"
                                })
                                break
                        except Exception:
                            pass
                    elif rule == "email":
                        import re
                        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
                        if not (isinstance(val, str) and re.match(email_regex, val)):
                            dq_error = True
                            validation_errors.append({
                                "row_index": idx + 1,
                                "column": col_name,
                                "value": str(val),
                                "reason": "Value must be a valid email format"
                            })
                            break
                    elif rule.startswith("min_length:"):
                        try:
                            min_len = int(rule.split(":")[1])
                            if not (isinstance(val, str) and len(val) >= min_len):
                                dq_error = True
                                validation_errors.append({
                                    "row_index": idx + 1,
                                    "column": col_name,
                                    "value": str(val),
                                    "reason": f"Value length must be at least {min_len} characters"
                                })
                                break
                        except Exception:
                            pass
                    elif rule.startswith("max_length:"):
                        try:
                            max_len = int(rule.split(":")[1])
                            if not (isinstance(val, str) and len(val) <= max_len):
                                dq_error = True
                                validation_errors.append({
                                    "row_index": idx + 1,
                                    "column": col_name,
                                    "value": str(val),
                                    "reason": f"Value length exceeds maximum of {max_len} characters"
                                })
                                break
                        except Exception:
                            pass
                    elif rule.startswith("allowed_options:"):
                        try:
                            options_str = rule.split(":", 1)[1]
                            options = [opt.strip().lower() for opt in options_str.split(",") if opt.strip()]
                            if str(val).strip().lower() not in options:
                                dq_error = True
                                validation_errors.append({
                                    "row_index": idx + 1,
                                    "column": col_name,
                                    "value": str(val),
                                    "reason": f"Value must be one of the allowed options: {options_str}"
                                })
                                break
                        except Exception:
                            pass

                if dq_error:
                    break

            if dq_error:
                invalid_rows += 1
                continue

            # D. Currency Normalization
            if rules_dict.get("currency_normalize") and target_table == "fact_sales":
                curr = str(cleaned_row.get("currency") or "USD").upper().strip()
                rates = {
                    "EUR": 1.10,
                    "CAD": 0.75,
                    "GBP": 1.25,
                    "USD": 1.0
                }
                rate = rates.get(curr, 1.0)
                if rate != 1.0:
                    if cleaned_row.get("unit_price") is not None:
                        cleaned_row["unit_price"] = round(cleaned_row["unit_price"] * rate, 2)
                    if cleaned_row.get("revenue") is not None:
                        cleaned_row["revenue"] = round(cleaned_row["revenue"] * rate, 2)
                cleaned_row["currency"] = "USD"

            # E. Compute missing revenue
            if rules_dict.get("calculate_revenue") and target_table == "fact_sales":
                if cleaned_row.get("revenue") is None:
                    qty = cleaned_row.get("quantity") or 0
                    price = cleaned_row.get("unit_price") or 0.0
                    cleaned_row["revenue"] = round(qty * price, 2)

            # F. Check business key duplicates
            b_key_val = cleaned_row.get(business_key)
            if b_key_val is None:
                invalid_rows += 1
                validation_errors.append({
                    "row_index": idx + 1,
                    "column": business_key,
                    "value": None,
                    "reason": f"Business key '{business_key}' is null or missing"
                })
                continue

            if b_key_val in seen_keys:
                duplicate_rows += 1
                validation_errors.append({
                    "row_index": idx + 1,
                    "column": business_key,
                    "value": str(b_key_val),
                    "reason": f"Duplicate record with business key '{b_key_val}' in the uploaded CSV"
                })
                continue

            if b_key_val in existing_db_keys:
                duplicate_rows += 1
                validation_errors.append({
                    "row_index": idx + 1,
                    "column": business_key,
                    "value": str(b_key_val),
                    "reason": f"Record with business key '{b_key_val}' already exists in database"
                })
                continue

            seen_keys.add(b_key_val)
            valid_records.append(cleaned_row)

        # Step 5: Insert valid records into database
        inserted_rows = len(valid_records)
        error_message = None
        status = "success"

        if validation_errors:
            err_summary = f"Ingestion completed with {len(validation_errors)} validation warning(s). First few: "
            err_details = [f"Row {e['row_index']} ({e['column']}): {e['reason']}" for e in validation_errors[:5]]
            error_message = (err_summary + "; ".join(err_details))[:1000]

        if valid_records:
            try:
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

        # Step 6: Log audit
        audit_log = UploadAudit(
            file_name=file_name,
            target_table=target_table,
            total_rows=total_rows,
            inserted_rows=inserted_rows,
            duplicate_rows=duplicate_rows,
            removed_rows=duplicate_rows,
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
            "processing_time_seconds": processing_time_seconds,
            "validation_errors": validation_errors
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
