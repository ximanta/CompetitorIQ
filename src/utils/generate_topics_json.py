import pandas as pd
import json
import os
import glob

# Constants
# OUTPUT_JSON_PATH = "src/data/topics.json" # DEPRECATED: Now per folder
MASTER_DIR = "src/data/master"
# BASE_MASTER_FILENAME = "Agentic AI Course Content Competition Analysis.xlsx" # DEPRECATED: searching for *any* xlsx

def get_latest_master_file_in_folder(folder_path):
    """Finds the latest version of the master file based on modification time in a specific folder."""
    # Search for ANY .xlsx file in this folder
    search_pattern = os.path.join(folder_path, "*.xlsx")
    files = glob.glob(search_pattern)
    
    # Filter out temp files (starting with ~$)
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def generate_topics_for_folder(folder_path):
    file_path = get_latest_master_file_in_folder(folder_path)
    if not file_path:
        print(f"Skipping {folder_path}: No .xlsx file found.")
        return

    print(f"Processing {folder_path}...")
    print(f"  Reading topics from: {os.path.basename(file_path)}")
    
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
            # if "TOPIC" in val.upper():
            #     print(f"Debug: Found potential marker '{repr(val)}'")
                
            if val.upper() == "TOPIC END":
                # print("Stopping at TOPIC END marker.")
                break
            
            # Fallback: Stop if we hit the summary section
            if val.upper().startswith("ESSENTIAL YES") or val.upper().startswith("ESSENTIAL NO"):
                # print(f"Stopping at summary section: {val}")
                break
                
            if pd.notna(item) and val:
                valid_topics.append(val)
        
        # Unique while preserving order (using dict)
        topics = list(dict.fromkeys(valid_topics))
        
        output_path = os.path.join(folder_path, "topics.json")
        with open(output_path, 'w') as f:
            json.dump(topics, f, indent=4)
            
        print(f"  ✅ Generated topics.json defined with {len(topics)} topics.")
        
    except Exception as e:
        print(f"  ❌ Error processing {os.path.basename(file_path)}: {e}")

def generate_topics():
    # Iterate over all subdirectories in MASTER_DIR
    if not os.path.exists(MASTER_DIR):
        print(f"Error: {MASTER_DIR} does not exist.")
        return

    items = os.listdir(MASTER_DIR)
    subfolders = [os.path.join(MASTER_DIR, item) for item in items if os.path.isdir(os.path.join(MASTER_DIR, item))]
    
    print(f"Found {len(subfolders)} track folders in {MASTER_DIR}")
    
    for folder in subfolders:
        generate_topics_for_folder(folder)
        
    print("\nGlobal generation complete.")

if __name__ == "__main__":
    generate_topics()
