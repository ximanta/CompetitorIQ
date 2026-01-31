import pandas as pd
import json
import os
import glob

# Constants
OUTPUT_JSON_PATH = "src/data/topics.json"
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

def generate_topics():
    file_path = get_latest_master_file()
    if not file_path:
        print(f"Error: No master file found in {MASTER_DIR}")
        return

    print(f"Reading topics from: {file_path}")
    
    try:
        df = pd.read_excel(file_path, sheet_name='Comparison')
        # Assuming 'Topic' logic from excel_handler
        # Logic: Column B or named 'Topic'
        if 'Topic' in df.columns:
            series = df['Topic']
        else:
            # Fallback to column B (index 1)
            series = df.iloc[:, 1]
            
        # Filter logic: Stop at "TOPIC END"
        valid_topics = []
        for item in series:
            # Normalize check
            val = str(item).strip()
            # Debug check
            if "TOPIC" in val.upper():
                print(f"Debug: Found potential marker '{repr(val)}'")
                
            if val.upper() == "TOPIC END":
                print("Stopping at TOPIC END marker.")
                break
            
            # Fallback: Stop if we hit the summary section
            if val.upper().startswith("ESSENTIAL YES") or val.upper().startswith("ESSENTIAL NO"):
                print(f"Stopping at summary section: {val}")
                break
                
            if pd.notna(item) and val:
                valid_topics.append(val)
        
        # Unique while preserving order (using dict)
        topics = list(dict.fromkeys(valid_topics))
            
        with open(OUTPUT_JSON_PATH, 'w') as f:
            json.dump(topics, f, indent=4)
            
        print(f"Successfully generated {OUTPUT_JSON_PATH} with {len(topics)} topics.")
        
    except Exception as e:
        print(f"Error processing Excel: {e}")

if __name__ == "__main__":
    generate_topics()
