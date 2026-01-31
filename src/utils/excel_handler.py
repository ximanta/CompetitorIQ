import pandas as pd
import io

def load_master_topics(file):
    """
    Loads topics from the 'Comparison' sheet of the master Excel.
    Handles merged cells by dropping NaN in the Topic column.
    """
    df = pd.read_excel(file, sheet_name='Comparison')
    # Assuming 'Topic' is in a specific column or we find it
    # Based on specs, it's Column B or named 'Topic'
    if 'Topic' not in df.columns:
        # Fallback: maybe the header is on a different row or name differs
        # For now, we assume 'Topic' exists as per spec
        pass
    
    # Filter out empty topics (common with merged cells if logic relies on Column B)
    topics = df['Topic'].dropna().unique().tolist()
    return topics, df

import openpyxl
from openpyxl.comments import Comment

def update_excel_with_analysis(source_file_path, analysis_results, competitor_name):
    """
    Updates the Excel file with analysis results using openpyxl to preserve existing comments.
    Returns the saved workbook as bytes.
    """
    # Load the workbook (data_only=False ensures we keep formulas/comments if any, though we want structure)
    wb = openpyxl.load_workbook(source_file_path)
    
    if "Comparison" not in wb.sheetnames:
        raise ValueError("Sheet 'Comparison' not found in Master Excel.")
        
    ws = wb["Comparison"]
    
    # 1. Determine Target Column (Update existing or Append new)
    target_col_idx = None
    
    # Check if header already exists (Row 1)
    for cell in ws[1]:
        if cell.value == competitor_name:
            target_col_idx = cell.column
            break
            
    # If not found, append to end
    if not target_col_idx:
        target_col_idx = ws.max_column + 1
    
    # 2. Write Header (only needed if new, but harmless to overwrite)
    # Row 1 is header
    header_cell = ws.cell(row=1, column=target_col_idx)
    header_cell.value = competitor_name
    # Optional: copy style from previous header if desired, but default is fine for now
    
    # 3. Iterate rows and populate data
    # We assume Column B (index 2) contains the Topics as per spec
    # starting from row 2
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, min_col=2, max_col=2, values_only=False), start=2):
        cell = row[0]
        topic = str(cell.value).strip() if cell.value else ""
        
        # Stop at TOPIC END
        if topic == "TOPIC END":
            break
            
        if not topic:
            continue
            
        # Get Analysis
        result = analysis_results.get(topic, {})
        decision = result.get('decision', None) # Default None to leave blank if missing? Or "No"? 
        # User spec v1: "No" if missing.
        # But wait, sticking to "No" is safer unless we want to distinguish "Not Analyzed"
        if not decision:
             # If topic exists in analysis_results key but decision is empty -> No
             # If topic is NOT in analysis_results -> No (implied check)
             decision = "No"
             
        reasoning = result.get('reasoning', "No mention found.")
        
        # Write Decision
        target_cell = ws.cell(row=row_idx, column=target_col_idx)
        target_cell.value = decision
        
        # Write Comment
        if reasoning:
            # Note: openpyxl comments need an Author.
            target_cell.comment = Comment(reasoning, "AgenticAI")
            
    # 4. Save to Bytes
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
