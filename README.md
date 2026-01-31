# Agentic Competitor Analysis 

Automate curriculum gap analysis using Gemini 2.0 Flash with interactive Excel validation.

## Prerequisites
- **Python 3.12+**
- **uv** (Project manager)

## Quick Start

### Installation
1. Clone the repository.
2. Initialize environment:
   ```bash
   uv sync
   ```
3. Set up `.env` with your `GEMINI_KEY`.

## Managing Topics
The application reads topics from `src/data/master/Agentic AI Course Content Competition Analysis.xlsx`.

### Important Rules
- **TOPIC END Marker**: The system reads topics from the "Topic" column until it encounters the text `TOPIC END`. Any rows below this marker will be ignored (useful for excluding summary stats).
- **Structure**: Ensure your topics are in the `Topic` column.

### Updating Topics
If you modify the Master Excel file, you must regenerate the cached topic list for the changes to take effect:

```bash
# Run from the project root
uv run python src/utils/generate_topics_json.py
```

## Usage

### 1. Configure API Key
Copy `.env.example` to `.env` and add your `GEMINI_KEY` (or use the UI input).

### 2. Run Application
```bash
uv run streamlit run src/app.py
```
### 3. Access at http://localhost:8501/ 
---
Note: AI can make mistakes. 

## Features
- **Multi-Source Input**: Upload PDF brochures, provide website URLs, or directly paste curriculum text.
- **AI-Powered Gap Analysis**: Uses Gemini 2.0 Flash to map topics against master taxonomy.
- **Excel Cell Comments**: Hover over "Yes/No" cells in the download file to see AI's reasoning/evidence.
- **Full Logging**: Terminal logs provide real-time updates on extraction and analysis phases.

## Structure
- `src/app.py`: Streamlit frontend with premium UI.
- `src/utils/extraction.py`: Text extraction logic (PDF & Web).
- `src/utils/ai_engine.py`: Gemini integration with batch reasoning.
- `src/utils/excel_handler.py`: Excel generation with `xlsxwriter` comments.
