import streamlit as st
import pandas as pd
import os
import logging
import time
import urllib.parse
from utils.extraction import extract_from_pdf, extract_from_url
from utils.ai_engine import analyze_topics, extract_price_duration_info, PriceDurationExtractionError
from utils.excel_handler import load_master_topics, update_excel_with_analysis, get_price_duration_columns
from dotenv import load_dotenv

load_dotenv()

import sys
import json

# Configure logging - Force to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CompetitorIQ",
    layout="wide"
)

# ... (CSS was removed in previous step, we can leave this section cleaner or empty) ...

import hashlib

# ... (Previous imports)

# --- AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            if "passwords" not in st.secrets:
                st.error("❌ 'passwords' section not found in secrets.toml.")
                return

            # Robust Check: Hash input and compare with ALL stored hashes
            input_pwd = st.session_state["password"].strip()
            if not input_pwd:
                st.error("Please enter a password.")
                return
                
            input_hash = hashlib.sha256(input_pwd.encode()).hexdigest()
            
            # Iterate over all configured users
            # Iterate over all configured users
            for user, stored_hash in st.secrets["passwords"].items():
                if input_hash == stored_hash:
                    st.session_state["password_correct"] = True
                    st.session_state["user_role"] = user # Store 'admin' or 'user'
                    # Optional: clear password from session state for security
                    st.session_state["password"] = "" 
                    return
            
            # If we get here, no match found
            st.session_state["password_correct"] = False
            st.error("😕 Password incorrect")
            
        except Exception as e:
            st.error(f"Authentication Error: {e}")

    if "password_correct" not in st.session_state:
        # First run, show input
        # Show Hero Image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
             if os.path.exists("src/assset/hero_img.png"):
                 st.image("src/assset/hero_img.png", use_container_width=True)
             st.text_input(
                "Please enter the access password", type="password", on_change=password_entered, key="password"
            )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
             if os.path.exists("src/assset/hero_img.png"):
                 st.image("src/assset/hero_img.png", use_container_width=True)
             st.text_input(
                "Please enter the access password", type="password", on_change=password_entered, key="password"
            )
             st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# --- ADMIN DASHBOARD ---
def admin_dashboard():
    if st.session_state.get("user_role") == "admin":
        with st.sidebar:
            st.divider()
            st.subheader("🛡️ Admin Panel")
            
            with st.expander("File Manager"):
                master_dir = "src/data/master"
                if os.path.exists(master_dir):
                    files = [f for f in os.listdir(master_dir) if f.endswith(".xlsx")]
                    
                    if files:
                        st.write(f"Found {len(files)} files:")
                        for file in files:
                            c1, c2 = st.columns([3, 1])
                            c1.font_size = "small"
                            c1.caption(file)
                            if c2.button("🗑️", key=f"del_{file}", help=f"Delete {file}"):
                                try:
                                    os.remove(os.path.join(master_dir, file))
                                    st.toast(f"Deleted {file}")
                                    time.sleep(0.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    else:
                        st.info("No files found.")
                else:
                    st.error("Start Analysis first to create the data folder.")

admin_dashboard()

# --- APP LAYOUT ---
# Main Header
if os.path.exists("src/assset/hero_img.png"):
    # Optional: Small logo or just text if image has heading
    # st.image("src/assset/hero_img.png", width=150)
    pass

st.markdown('<div style="text-align: center; color: #666;">CompetitorIQ</div>', unsafe_allow_html=True)
st.markdown("---")

# --- SESSION STATE INITIALIZATION ---
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'competitor_name' not in st.session_state:
    st.session_state.competitor_name = ""
if 'course_name' not in st.session_state:
    st.session_state.course_name = ""
if 'website_link' not in st.session_state:
    st.session_state.website_link = ""
if 'master_file_updated' not in st.session_state:
    st.session_state.master_file_updated = False

# Constant for Master File
import glob
import re

MASTER_DIR = "src/data/master"
BASE_MASTER_FILENAME = "Agentic AI Course Content Competition Analysis.xlsx"
MASTER_FILE_PATH = "src/data/master/Agentic AI Course Content Competition Analysis.xlsx"
TOPICS_JSON_PATH = "src/data/topics.json"
COLUMNS_JSON_PATH = "src/data/price_duration_columns.json"

def get_latest_master_file():
    """Finds the latest version of the master file based on modification time."""
    base_name_no_ext = os.path.splitext(BASE_MASTER_FILENAME)[0]
    search_pattern = os.path.join(MASTER_DIR, f"{base_name_no_ext}*.xlsx")
    files = glob.glob(search_pattern)
    
    if not files:
        return None
        
    return max(files, key=os.path.getmtime)

def get_next_version_path(current_path):
    """Determines the next version filename."""
    base, ext = os.path.splitext(current_path)
    # Check if current path has _vX
    match = re.search(r"_v(\d+)$", base)
    if match:
        current_version = int(match.group(1))
        new_version = current_version + 1
        new_base = base[:match.start()] + f"_v{new_version}"
    else:
        # First versioning
        new_base = base + "_v1"
    
    return new_base + ext

# --- RESULTS VIEW ---
# --- RESULTS VIEW ---
if st.session_state.analysis_results:
    competitor_display = st.session_state.competitor_name
    if st.session_state.get("course_name"):
        competitor_display += f" - {st.session_state.course_name}"
    st.success(f"✅ Preparing Report for {competitor_display}")
    
    # Action Buttons (Top)
    b_col1, b_col2 = st.columns([1, 4])
    with b_col1:
        if st.button("⬅️ Start New Analysis"):
            st.session_state.analysis_results = None
            st.session_state.competitor_name = ""
            st.session_state.course_name = ""
            st.session_state.website_link = ""
            st.session_state.master_file_updated = False
            st.rerun()
            
    with b_col2:
        if st.session_state.master_file_updated:
             # Use the dynamically saved path as the TRUE source
             download_path = st.session_state.get("last_updated_master_path", MASTER_FILE_PATH)
             if os.path.exists(download_path):
                 with open(download_path, "rb") as f:
                    st.download_button(
                        label=f"📥 Download",
                        data=f,
                        file_name=os.path.basename(download_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    # 1. Prepare Data
    # Convert session state dict to list for dataframe
    results_data = []
    # Sort or keep order? topics.json order is preferred usually, but dict is insertion ordered in Py3.7+
    for topic, result in st.session_state.analysis_results.items():
        results_data.append({
            "Topic": topic,
            "Decision": result.get("decision", "No"),
            "Comment": result.get("reasoning", "")
        })
    results_df = pd.DataFrame(results_data)
    results_df.index = results_df.index + 1 # 1-based index
    
    # 2. Render Results (Custom Row-by-Row UI)
    st.subheader("Analysis Results")
    st.info("ℹ️ Click the '✏️' icon to edit a specific row. Click '💾' to save changes immediately.")
    
    # Header
    h_c1, h_c2, h_c3, h_c4 = st.columns([3, 1.5, 5, 1])
    h_c1.markdown("**Topic**")
    h_c2.markdown("**Decision**")
    h_c3.markdown("**Comment**")
    h_c4.markdown("**Action**")
    st.divider()
    
    # Init edit state if missing
    if "edit_target" not in st.session_state:
        st.session_state.edit_target = None

    # Sort topics for consistent order
    topics_list = list(st.session_state.analysis_results.keys())
    
    for idx, topic in enumerate(topics_list):
        data = st.session_state.analysis_results[topic]
        
        # Unique Keys for widgets
        row_key = f"row_{idx}"
        
        # Check if this row is being edited
        is_editing = (st.session_state.edit_target == topic)
        
        # Container for the row (adds slight spacing)
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 1.5, 5, 1])
            
            # --- EDIT MODE ---
            if is_editing:
                c1.text(topic) # Topic is immutable
                
                new_decision = c2.selectbox(
                    "Decision", 
                    options=["Yes", "No", "Unsure"],
                    index=["Yes", "No", "Unsure"].index(data.get("decision", "No")),
                    key=f"dec_{row_key}",
                    label_visibility="collapsed"
                )
                
                new_comment = c3.text_area(
                    "Comment", 
                    value=data.get("reasoning", ""),
                    height=100,
                    key=f"com_{row_key}",
                    label_visibility="collapsed"
                )
                
                # Save / Cancel Buttons in Column 4
                if c4.button("💾", key=f"save_{row_key}", help="Save Changes"):
                    # SAVE LOGIC
                    st.session_state.analysis_results[topic] = {
                        "decision": new_decision,
                        "reasoning": new_comment
                    }
                    
                    # Write to Disk
                    target_path = st.session_state.get("last_updated_master_path") or get_latest_master_file()
                    
                    if target_path:
                        try:
                            # Re-read and update
                            updated_bytes = update_excel_with_analysis(
                                target_path, 
                                st.session_state.analysis_results, 
                                st.session_state.competitor_name,
                                course_name=st.session_state.get("course_name"),
                                website_link=st.session_state.get("website_link"),
                                extracted_info=st.session_state.get("extracted_info")
                            )
                            with open(target_path, "wb") as f:
                                f.write(updated_bytes)
                                
                            print(f"[Backend] Row Update: '{topic}' saved to {target_path}")
                            st.toast(f"✅ Saved '{topic}'!")
                            st.session_state.master_file_updated = True
                        except Exception as e:
                            st.error(f"Save Failed: {e}")
                            logger.error(f"Save Error: {e}")
                    
                    # Exit Edit Mode
                    st.session_state.edit_target = None
                    time.sleep(0.5)
                    st.rerun()
                
                if c4.button("❌", key=f"cancel_{row_key}", help="Cancel Edit"):
                    st.session_state.edit_target = None
                    st.rerun()
                    
            # --- VIEW MODE ---
            else:
                c1.write(topic)
                
                # Color code decision
                dec_val = data.get("decision", "No")
                if dec_val == "Yes":
                    c2.success(dec_val)
                elif dec_val == "Unsure":
                    c2.warning(dec_val)
                else:
                    c2.error(dec_val)
                
                # Full text wrapped
                c3.write(data.get("reasoning", ""))
                
                # Edit Button
                if c4.button("✏️", key=f"edit_{row_key}", help="Edit this row"):
                    st.session_state.edit_target = topic
                    st.rerun()
            
            st.divider()
    
    # 3. Show Price / Duration / Projects sheet details (single-row view)
    if st.session_state.get("extracted_info") is not None:
        st.subheader("Price / Duration / Projects Details")
        st.info("These details come from the 'Price, Duration, Projects' sheet for this course.")
        
        price_row = {
            "Provider": st.session_state.competitor_name,
            "Course Name": st.session_state.course_name,
            "Website Link": st.session_state.website_link,
        }
        # Merge dynamic extracted fields (Price, Duration, Price/Week, Projects, etc.)
        price_row.update(st.session_state.extracted_info or {})
        
        price_df = pd.DataFrame([price_row])
        
        # Hide the CSV download toolbar for this (and any other) dataframes
        st.markdown(
            """
            <style>
            div[data-testid="stElementToolbar"] {display: none !important;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(price_df, use_container_width=True)

# --- INPUT VIEW ---
else:
    # Sidebar
    with st.sidebar:
        logger.info("Sidebar rendering...")
        st.title("Configuration")
        # API Key Strategy: User input > .env > Error
        gemini_key_input = st.text_input("Gemini API Key", type="password", placeholder="Paste key here (or leave empty to use .env)", value="")
        st.markdown("[Get a Free Key](https://ai.google.dev/gemini-api/docs/api-key)", unsafe_allow_html=True)
    
        # Model Selection
        model_options = ["gemini-2.5-flash", "gemini-2.5-pro"]
        selected_model = st.selectbox("AI Model", model_options, index=0)
    
        st.divider()
        st.markdown("""
        ### Workflow:
        
        1. Upload Competitor PDF, URL, or Paste Text
        2. Run Analysis
        3. Review, Edit, and Download Updated Excel
        4. Update Master file with competitor analysis (Manual)
        """)

    # Main Content
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="card"><h4>📁 Input Phase</h4></div>', unsafe_allow_html=True)
        
        course_name = st.text_input("Course Name", placeholder="e.g. AI Engineering Program, etc.")
        
        st.divider()
        
        evidence_type = st.radio("Competitor Evidence Source", ["PDF Brochure", "Website URL", "Paste Text"])
        
        competitor_evidence = None
        website_link = None
        
        # Validation Helper
        is_url_valid = True
        def validate_url(url):
            if url:
                parsed = urllib.parse.urlparse(url)
                if not (parsed.scheme in ['http', 'https'] and parsed.netloc):
                    st.error("Please enter a valid Website Link (must start with http:// or https://).")
                    return False
            return True

        if evidence_type == "PDF Brochure":
            website_link = st.text_input("Website Link (where you downloaded the brochure)", placeholder="https://competitor.com/course", help="Enter the website URL where you downloaded this PDF brochure")
            if not validate_url(website_link): is_url_valid = False
            competitor_evidence = st.file_uploader("Upload Competitor PDF", type=["pdf"])
        elif evidence_type == "Website URL":
            competitor_evidence = st.text_input("Enter Website URL for Content Extraction", placeholder="https://competitor.com/course")
            website_link = competitor_evidence  # For website source, the URL itself is the website link
            if not validate_url(website_link): is_url_valid = False
        else:  # Paste Text
            website_link = st.text_input("Website Link (source of this text)", placeholder="https://competitor.com/course", help="Enter the website URL where you got this text from")
            if not validate_url(website_link): is_url_valid = False
            competitor_evidence = st.text_area("Paste Competitor Content", height=200, placeholder="Paste the curriculum text here...")
    with col2:
        st.markdown('<div class="card"><h4>🛰️ Analysis Status</h4></div>', unsafe_allow_html=True)

        # State for missing-website confirmation when using PDF/Text
        if "confirm_missing_website" not in st.session_state:
            st.session_state.confirm_missing_website = False

        def perform_analysis():
            # Determine effective API Key
            gemini_key = gemini_key_input if gemini_key_input else os.getenv("GEMINI_KEY")
            
            # Dynamic Master File Check
            current_master_path = get_latest_master_file()
            
            # Extract competitor name from website URL or use course name as fallback
            competitor_name = None
            if website_link:
                try:
                    parsed_url = urllib.parse.urlparse(website_link)
                    domain = parsed_url.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    domain_parts = domain.split('.')
                    if len(domain_parts) > 0:
                        competitor_name = domain_parts[0].capitalize()
                except:
                    pass
            
            if not competitor_name:
                competitor_name = course_name if course_name else "Unknown Provider"

            with st.spinner(f"Analyzing {competitor_name}..."):
                try:
                    # 1. Load Topics from JSON (Fast)
                    logger.info("Loading topics from JSON...")
                    with open(TOPICS_JSON_PATH, 'r') as f:
                        topics = json.load(f)
                    st.success(f"Loaded {len(topics)} topics from Cache.")
                    
                    # 2. Extract Text
                    logger.info(f"Extracting content from {evidence_type}...")
                    st.info("Processing evidence...")
                    
                    extracted_text = ""
                    if evidence_type == "PDF Brochure":
                        extracted_text = extract_from_pdf(competitor_evidence)
                    elif evidence_type == "Website URL":
                        extracted_text = extract_from_url(competitor_evidence)
                    else:
                        extracted_text = competitor_evidence  # Direct text
                    
                    logger.info(f"Extracted {len(extracted_text)} characters.")
                    
                    if len(extracted_text) < 50:
                        logger.warning("Extracted text is very short.")
                        st.warning("Extracted text seems too short. Check your evidence source.")
                        st.text(f"Snippet: {extracted_text[:100]}...")
                    
                    # 3. AI Analysis
                    with st.status("Running Analysis...", expanded=True) as status:
                        st.write("Initializing AI Engine...")
                        
                        def log_callback(msg):
                            st.write(msg)
                        
                        from utils.ai_engine import AIAnalysisError
                        
                        analysis_results = analyze_topics(
                            topics,
                            extracted_text,
                            gemini_key,
                            model_name=selected_model,
                            log_callback=log_callback
                        )
                        
                        status.update(label=" Processing!", state="complete", expanded=False)
                    
                    logger.info("Gemini analysis complete.")
                    
                    # 3.5. Extract Price/Duration information from website
                    extracted_info = None
                    if website_link:
                        try:
                            with st.status("Extracting Price/Duration Information...", expanded=True) as status:
                                st.write("Loading column definitions...")
                                
                                with open(COLUMNS_JSON_PATH, 'r') as f:
                                    columns = json.load(f)
                                st.write(f"Loaded {len(columns)} column definitions.")
                                
                                st.write(f"Fetching content from {website_link}...")
                                website_content = extract_from_url(website_link)
                                
                                if len(website_content) < 50:
                                    st.warning("Website content seems too short. Extraction may be incomplete.")
                                else:
                                    st.write(f"Extracted {len(website_content)} characters from website.")
                                
                                st.write("Using AI to extract structured information...")
                                
                                def extract_log_callback(msg):
                                    st.write(msg)
                                
                                extracted_info = extract_price_duration_info(
                                    website_link,
                                    website_content,
                                    columns,
                                    gemini_key,
                                    model_name=selected_model,
                                    log_callback=extract_log_callback,
                                    course_name=course_name
                                )
                                
                                status.update(label="✅ Extraction Complete!", state="complete", expanded=False)
                                st.success(f"✅ Extracted information for {len(extracted_info)} fields")
                                
                        except PriceDurationExtractionError as e:
                            st.error(f"⚠️ Price/Duration Extraction Error: {e}")
                            logger.error(f"Price/Duration extraction failed: {e}")
                        except Exception as e:
                            st.warning(f"⚠️ Could not extract price/duration info: {e}")
                            logger.warning(f"Price/Duration extraction error: {e}")
                    
                    # 4. Prepare Download & Update
                    logger.info(f"Updating Excel file: {current_master_path}")
                    logger.info(f"extracted_info being passed: {extracted_info}")
                    
                    updated_excel_bytes = update_excel_with_analysis(
                        current_master_path,
                        analysis_results,
                        competitor_name,
                        course_name=course_name,
                        website_link=website_link,
                        extracted_info=extracted_info
                    )
                    
                    new_master_path = get_next_version_path(current_master_path)
                    
                    try:
                        with open(new_master_path, "wb") as f:
                            f.write(updated_excel_bytes)
                        
                        logger.info(f"Saved new version: {new_master_path}")
                        st.session_state.master_file_updated = True
                        st.session_state.analysis_results = analysis_results
                        st.session_state.competitor_name = competitor_name
                        st.session_state.course_name = course_name
                        st.session_state.website_link = website_link
                        st.session_state.extracted_info = extracted_info
                        st.session_state.last_updated_master_path = new_master_path
                        
                        status.update(label="Processing!", state="complete", expanded=False)
                        st.success(f"✅ Analysis Complete! Saved as: {os.path.basename(new_master_path)}")
                        st.rerun()
                    
                    except PermissionError:
                        msg = f"PERMISSION DENIED: Could not write to '{new_master_path}'. Is the file open in Excel?"
                        logger.error(msg)
                        st.error("⚠️ Permission issue encountered. Please ensure master excel is not open at your end")
                    except Exception as e:
                        logger.error(f"Failed to save Master Excel: {e}")
                        st.error(f"⚠️ Error saving file: {e}")
                
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    logger.error(f"Application Error: {e}")

        start_clicked = st.button("Start Analysis")

        # Check if this is a continuation from the Proceed button
        is_continuation = st.session_state.get("trigger_analysis_continuation", False)

        if start_clicked or is_continuation:
            # Reset the continuation flag immediately to avoid sticky state
            if is_continuation:
                st.session_state.trigger_analysis_continuation = False
                
            gemini_key = gemini_key_input if gemini_key_input else os.getenv("GEMINI_KEY")
            current_master_path = get_latest_master_file()

            if not current_master_path or not os.path.exists(current_master_path):
                st.error(f"Master file not found in {MASTER_DIR}. Please ensure '{BASE_MASTER_FILENAME}' exists.")
            elif not os.path.exists(TOPICS_JSON_PATH):
                st.error(f"Topics JSON not found at {TOPICS_JSON_PATH}. Please run regeneration script.")
            elif not os.path.exists(COLUMNS_JSON_PATH):
                st.error(f"Columns JSON not found at {COLUMNS_JSON_PATH}. Please run: uv run python src/utils/generate_columns_json.py")
            elif not course_name:
                st.error("Please enter a Course Name.")
            elif evidence_type == "Website URL" and not website_link:
                st.error("Please enter a Website Link.")
            elif not competitor_evidence:
                st.error("Please provide competitor evidence.")
            elif not gemini_key:
                st.error("Gemini API Key is required. Please paste it in the sidebar or set GEMINI_KEY in .env.")
            else:
                # If PDF/Text source and website link is empty, set confirmation flag
                # BUT skip this check if the user just clicked "Proceed" (is_continuation is True)
                if evidence_type in ["PDF Brochure", "Paste Text"] and not website_link and not is_continuation:
                    st.session_state.confirm_missing_website = True
                elif not is_url_valid:
                     st.error("Please fix the errors above before proceeding.")
                else:
                    perform_analysis()

        # Show confirmation popup when needed
        if st.session_state.confirm_missing_website:
            st.warning(
                "Currently your source website link of your PDF is empty.\n"
                "You might need to manually fill your analysis sheet with information below if empty:\n\n"
                "- Price\n"
                "- Duration\n"
                "- Price/Week\n"
                "- Projects and Additional Services\n"
                "- Eligibility Criteria"
            )

            # Use columns to position the button on the right - gave it more space [3, 1]
            _, c_right = st.columns([3, 1]) 
            with c_right:
                if st.button("Proceed", key="confirm_no_website_proceed"):
                    st.session_state.confirm_missing_website = False
                    st.session_state.trigger_analysis_continuation = True
                    st.rerun()

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888; font-size: 0.8em;'>Built by NIIT Corp IC, </p>", unsafe_allow_html=True)

