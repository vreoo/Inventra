import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging
from models.forecast import InventoryData

logger = logging.getLogger(__name__)

class FileHandler:
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate CSV file and return validation results"""
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "info": {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "date_columns": [],
                    "numeric_columns": [],
                    "text_columns": []
                }
            }
            
            # Check if file is empty
            if df.empty:
                validation_result["valid"] = False
                validation_result["errors"].append("CSV file is empty")
                return validation_result
            
            # Analyze column types
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    validation_result["info"]["numeric_columns"].append(col)
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    validation_result["info"]["date_columns"].append(col)
                else:
                    # Try to parse as datetime
                    try:
                        pd.to_datetime(df[col].head())
                        validation_result["info"]["date_columns"].append(col)
                    except:
                        validation_result["info"]["text_columns"].append(col)
            
            # Check for required columns (flexible approach)
            has_date_col = len(validation_result["info"]["date_columns"]) > 0
            has_numeric_col = len(validation_result["info"]["numeric_columns"]) > 0
            
            if not has_date_col:
                validation_result["warnings"].append("No date column detected. Please ensure you have a date column for time series analysis.")
            
            if not has_numeric_col:
                validation_result["errors"].append("No numeric columns found. Inventory data requires numeric quantity values.")
                validation_result["valid"] = False
            
            # Check for missing values
            missing_data = df.isnull().sum()
            if missing_data.any():
                validation_result["warnings"].append(f"Missing values detected: {missing_data[missing_data > 0].to_dict()}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating CSV file {file_path}: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Error reading CSV file: {str(e)}"],
                "warnings": [],
                "info": {}
            }
    
    def process_inventory_data(self, file_path: Path) -> Tuple[List[InventoryData], Dict[str, Any]]:
        """Process CSV file and convert to inventory data format"""
        try:
            df = pd.read_csv(file_path)
            
            # Auto-detect column mappings
            column_mapping = self._detect_column_mapping(df)
            
            if not column_mapping["date_col"] or not column_mapping["quantity_col"]:
                raise ValueError("Could not detect required date and quantity columns")
            
            # Process the data
            processed_data = []
            
            # Ensure date column is datetime
            df[column_mapping["date_col"]] = pd.to_datetime(df[column_mapping["date_col"]])
            
            # Sort by date
            df = df.sort_values(column_mapping["date_col"])
            
            # Group by product if product column exists
            if column_mapping["product_col"]:
                for product_id, group in df.groupby(column_mapping["product_col"]):
                    for _, row in group.iterrows():
                        inventory_item = InventoryData(
                            date=row[column_mapping["date_col"]].strftime("%Y-%m-%d"),
                            product_id=str(product_id),
                            quantity=float(row[column_mapping["quantity_col"]]),
                            product_name=str(row.get(column_mapping["product_name_col"], product_id)) if column_mapping["product_name_col"] else str(product_id)
                        )
                        processed_data.append(inventory_item)
            else:
                # Single product scenario
                product_id = "default_product"
                for _, row in df.iterrows():
                    inventory_item = InventoryData(
                        date=row[column_mapping["date_col"]].strftime("%Y-%m-%d"),
                        product_id=product_id,
                        quantity=float(row[column_mapping["quantity_col"]]),
                        product_name="Default Product"
                    )
                    processed_data.append(inventory_item)
            
            processing_info = {
                "total_records": len(processed_data),
                "date_range": {
                    "start": min(item.date for item in processed_data),
                    "end": max(item.date for item in processed_data)
                },
                "products": list(set(item.product_id for item in processed_data)),
                "column_mapping": column_mapping
            }
            
            return processed_data, processing_info
            
        except Exception as e:
            logger.error(f"Error processing inventory data from {file_path}: {str(e)}")
            raise
    
    def _detect_column_mapping(self, df: pd.DataFrame) -> Dict[str, str]:
        """Auto-detect column mappings based on column names and data types"""
        mapping = {
            "date_col": None,
            "quantity_col": None,
            "product_col": None,
            "product_name_col": None
        }
        
        # Common date column names
        date_keywords = ["date", "time", "timestamp", "day", "period"]
        quantity_keywords = ["quantity", "stock", "inventory", "amount", "count", "units", "qty"]
        product_keywords = ["product", "item", "sku", "id"]
        name_keywords = ["name", "title", "description", "product_name", "item_name"]
        
        for col in df.columns:
            col_lower = col.lower()
            
            # Detect date column
            if not mapping["date_col"]:
                if any(keyword in col_lower for keyword in date_keywords):
                    try:
                        pd.to_datetime(df[col].head())
                        mapping["date_col"] = col
                        continue
                    except:
                        pass
            
            # Detect quantity column
            if not mapping["quantity_col"]:
                if any(keyword in col_lower for keyword in quantity_keywords):
                    if df[col].dtype in ['int64', 'float64']:
                        mapping["quantity_col"] = col
                        continue
            
            # Detect product ID column
            if not mapping["product_col"]:
                if any(keyword in col_lower for keyword in product_keywords):
                    mapping["product_col"] = col
                    continue
            
            # Detect product name column
            if not mapping["product_name_col"]:
                if any(keyword in col_lower for keyword in name_keywords):
                    mapping["product_name_col"] = col
                    continue
        
        # Fallback: use first numeric column as quantity if not found
        if not mapping["quantity_col"]:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                mapping["quantity_col"] = numeric_cols[0]
        
        # Fallback: try to parse first column as date if not found
        if not mapping["date_col"]:
            for col in df.columns:
                try:
                    pd.to_datetime(df[col].head())
                    mapping["date_col"] = col
                    break
                except:
                    continue
        
        return mapping
    
    def get_file_path(self, file_id: str) -> Path:
        """Get file path from file ID"""
        return self.upload_dir / f"{file_id}.csv"
    
    def file_exists(self, file_id: str) -> bool:
        """Check if file exists"""
        return self.get_file_path(file_id).exists()
