import pandas as pd
import json
import os
import glob
import openpyxl

# Constants
OUTPUT_JSON_PATH = "src/data/price_duration_columns.json"
MASTER_DIR = "src/data/master"
BASE_MASTER_FILENAME = "Agentic AI Course Content Competition Analysis.xlsx"

def get_latest_master_file():
    """Finds the latest version of the master file based on modification time."""
    base_name_no_ext = os.path.splitext(BASE_MASTER_FILENAME)[0]
    search_pattern = os.path.join(MASTER_DIR, f"{base_name_no_ext}*.xlsx")
    files = glob.glob(search_pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def generate_columns():
    file_path = get_latest_master_file()
    if not file_path:
        print(f"Error: No master file found in {MASTER_DIR}")
        return

    print(f"Reading columns from: {file_path}")
    
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        
        if "Price, Duration, Projects" not in wb.sheetnames:
            print("Error: 'Price, Duration, Projects' sheet not found in master file.")
            wb.close()
            return
        
        ws = wb["Price, Duration, Projects"]
        columns = []
        
        # Read row 1 to get column titles (read up to max_column)
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=1, column=col_idx)
            if cell.value:
                columns.append(str(cell.value).strip())
            else:
                columns.append(None)  # Keep track of empty columns too
        
        wb.close()
        
        # Filter out None values for cleaner output
        columns_clean = [col for col in columns if col is not None]
        
        with open(OUTPUT_JSON_PATH, 'w') as f:
            json.dump(columns_clean, f, indent=4)
            
        print(f"Successfully generated {OUTPUT_JSON_PATH} with {len(columns_clean)} columns.")
        print(f"Columns: {columns_clean}")
        
    except Exception as e:
        print(f"Error processing Excel: {e}")

if __name__ == "__main__":
    generate_columns()

