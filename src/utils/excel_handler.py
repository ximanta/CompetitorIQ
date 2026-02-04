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
from openpyxl.styles import PatternFill, Font
from copy import copy

def copy_cell_style(source_cell, target_cell):
    """
    Copies all formatting from source_cell to target_cell.
    This includes fill, font, border, alignment, number_format, protection, etc.
    """
    if source_cell.has_style:
        target_cell.font = copy(source_cell.font)
        target_cell.border = copy(source_cell.border)
        target_cell.fill = copy(source_cell.fill)
        target_cell.number_format = source_cell.number_format
        target_cell.protection = copy(source_cell.protection)
        target_cell.alignment = copy(source_cell.alignment)

def update_excel_with_analysis(source_file_path, analysis_results, competitor_name):
    """
    Updates the Excel file with analysis results using openpyxl to preserve existing comments and formatting.
    Returns the saved workbook as bytes.
    """
    # Load the workbook (data_only=False ensures we keep formulas/comments if any, though we want structure)
    wb = openpyxl.load_workbook(source_file_path)
    
    if "Comparison" not in wb.sheetnames:
        raise ValueError("Sheet 'Comparison' not found in Master Excel.")
        
    ws = wb["Comparison"]
    
    # 1. Determine Target Column (Update existing or Append new)
    target_col_idx = None
    is_new_column = False
    
    # Check if header already exists (Row 1)
    for cell in ws[1]:
        if cell.value == competitor_name:
            target_col_idx = cell.column
            break
            
    # If not found, append to end
    if not target_col_idx:
        target_col_idx = ws.max_column + 1
        is_new_column = True
    
    # 2. Find reference columns to copy styles from
    # For headers: use any competitor column (they all have orange header)
    # For data cells: use column 4 (first competitor column) which has no fill
    header_reference_col_idx = None
    data_reference_col_idx = None
    
    # Find a competitor column (columns 4+) for both header and data cell style
    for check_col in range(max(4, target_col_idx - 1), 2, -1):
        if check_col < target_col_idx:  # Don't check our own column
            test_cell = ws.cell(row=1, column=check_col)
            if test_cell.has_style:
                header_reference_col_idx = check_col
                data_reference_col_idx = check_col
                break
    
    # Fallback: use column 4 if available, otherwise column 3, then column 1
    if data_reference_col_idx is None:
        if ws.max_column >= 4:
            data_reference_col_idx = 4
            if header_reference_col_idx is None:
                header_reference_col_idx = 4
        elif ws.max_column >= 3:
            data_reference_col_idx = 3
            if header_reference_col_idx is None:
                header_reference_col_idx = 3
        else:
            header_reference_col_idx = 1
            data_reference_col_idx = 1
    
    # 3. Write Header (only needed if new, but harmless to overwrite)
    # Row 1 is header
    header_cell = ws.cell(row=1, column=target_col_idx)
    
    # If it's a new column, copy style from reference column before setting value
    if is_new_column and header_reference_col_idx > 0:
        reference_header = ws.cell(row=1, column=header_reference_col_idx)
        copy_cell_style(reference_header, header_cell)
    # If updating existing column, preserve its existing style (don't overwrite)
    
    header_cell.value = competitor_name
    
    # 4. Iterate rows and populate data
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
        
        # Copy base style from reference column's corresponding row (only for new columns)
        if is_new_column and data_reference_col_idx > 0:
            reference_cell = ws.cell(row=row_idx, column=data_reference_col_idx)
            copy_cell_style(reference_cell, target_cell)
        # If updating existing column, preserve its existing style (don't overwrite)
        
        target_cell.value = decision
        
        # Apply conditional fill and font colors based on decision value
        # Colors match column 4:
        # Yes: fill=c6efce (green), font=006100 (dark green)
        # No: fill=ffc7ce (red), font=9c0006 (dark red)
        # Unsure/Maybe: fill=f5f19f (yellow), font=61540c (dark yellow/brown)
        decision_lower = str(decision).strip().lower()
        
        # Preserve existing font properties and only update color
        current_font = target_cell.font if target_cell.font else Font()
        
        if decision_lower == "yes":
            target_cell.fill = PatternFill(start_color="c6efce", end_color="c6efce", fill_type="solid")
            target_cell.font = Font(
                name=current_font.name,
                size=current_font.size,
                bold=current_font.bold,
                italic=current_font.italic,
                underline=current_font.underline,
                color="006100"
            )
        elif decision_lower == "no":
            target_cell.fill = PatternFill(start_color="ffc7ce", end_color="ffc7ce", fill_type="solid")
            target_cell.font = Font(
                name=current_font.name,
                size=current_font.size,
                bold=current_font.bold,
                italic=current_font.italic,
                underline=current_font.underline,
                color="9c0006"
            )
        elif decision_lower in ["unsure", "maybe"]:
            target_cell.fill = PatternFill(start_color="f5f19f", end_color="f5f19f", fill_type="solid")
            target_cell.font = Font(
                name=current_font.name,
                size=current_font.size,
                bold=current_font.bold,
                italic=current_font.italic,
                underline=current_font.underline,
                color="61540c"
            )
        
        # Write Comment
        if reasoning:
            # Note: openpyxl comments need an Author.
            target_cell.comment = Comment(reasoning, "AgenticAI")
            
    # 5. Save to Bytes
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
