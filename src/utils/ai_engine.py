import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

import typing_extensions as typing

class TopicAnalysis(typing.TypedDict):
    topic: str
    decision: str
    reasoning: str

import time

class AIAnalysisError(Exception):
    """Custom exception for AI analysis failures after retries."""
    pass

class PriceDurationExtractionError(Exception):
    """Custom exception for price/duration extraction failures."""
    pass

def analyze_topics(topics, context, api_key, model_name=None, log_callback=None):
    """
    Analyzes topics against competitor context using Gemini with Structured Output.
    Returns a dictionary mapping Topic Name to {"decision": "Yes/No", "reasoning": "..."}
    Retries 3 times on failure.
    
    Args:
        log_callback (callable, optional): function(str) to log messages to UI.
    """
    genai.configure(api_key=api_key)
    
    if not log_callback:
        log_callback = lambda x: None # No-op
    
    # Priority: Model arg > Env PRO > Env LITE > Default
    if not model_name:
        model_name = os.getenv("GEMINI_PRO")
        if not model_name:
            model_name = os.getenv("GEMINI_LITE", "gemini-2.5-flash")
        
    logger.info(f"Using Gemini Model: {model_name}")
    log_callback(f"🤖 Using Model: **{model_name}**")
    
    model = genai.GenerativeModel(model_name)
    
    topics_json = json.dumps(topics)
    
    prompt = f"""
    ## SYSTEM
    You are an expert technical curriculum analyst specializing in enterprise AI and software training programs.

### Context
You are given a list of technical topics and a competitor’s program content.
### Task
For EACH topic in the provided list, decide whether the competitor’s content:

- explicitly covers the topic, OR
- clearly and unambiguously implies the same concept using different terminology.
Your decision must be one of:
Yes, No, or Unsure.
---
### Important interpretation rules

1. Mark **"Yes"** ONLY if the topic is:
   - directly mentioned, OR
   - described in a way that uniquely maps to that topic and would be understood by a technical professional as that topic.

2. Mark **"No"** ONLY if:
   - there is no reference to the topic or its equivalent concept in the content, OR
   - the content only contains generic or high-level terms such as
     "AI", "ML", "GenAI", "automation", "analytics", "cloud", "modern platforms", or similar wording that does not indicate this specific topic.

3. Mark **"Unsure"** ONLY if:
   - there is some partial or indirect signal related to the topic,
   - but the content is ambiguous, vague, or insufficient to confidently decide Yes or No,
   - and determining coverage would require assumptions or interpretation beyond what is explicitly written.
4. Do NOT infer subtopics from broader topics unless the subtopic is clearly described.
5. You must evaluate **EVERY topic** in the list.  
   Do not skip any topic.
6. If the match is based on implication rather than an explicit quote, explicitly state in the reasoning that it is an *implied* match.
7. **CRITICAL**: 
- If the decision is **"YES"**, the reasoning must clearly state that the topic is explicitly mentioned or implied.
- If the decision is **"No"**, the reasoning must clearly state that no relevant mention was found or explain why the wording is too generic.
- If the decision is **"Unsure"**, the reasoning must clearly state what weak or ambiguous signal caused the uncertainty.
---

    ### Output rules

    1. Output MUST be a valid JSON List of objects.
    
    2. Each object must follow this schema:
    
    ```json
    {{
      "topic": "Topic Name",
      "decision": "Yes, No, or Unsure",
      "reasoning": "Concise justification..."
    }}
    ```

    3. The "topic" field must match the input topic exactly.

    4. Do not add, remove, rename, normalize, or merge any topic names.

    5. Do not introduce topics that are not present in the Topics List.

    ---
    Competitor Content:
    {context}
    
    Topics List:
    {topics_json}
    """
    
    max_retries = 2
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Analysis Attempt {attempt + 1}/{max_retries}")
            log_callback(f"🔄 Analysis Attempt {attempt + 1}/{max_retries}...")
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # --- TRACE LOGGING ---
            try:
                trace_dir = "llm-trace"
                os.makedirs(trace_dir, exist_ok=True)
                
                with open(os.path.join(trace_dir, "llm_prompt.md"), "w", encoding="utf-8") as f:
                    f.write(prompt)
                    
                with open(os.path.join(trace_dir, "llm_output.json"), "w", encoding="utf-8") as f:
                    f.write(response.text)
                    
                log_callback(f"📁 Trace saved to {trace_dir}/")
            except Exception as trace_e:
                logger.warning(f"Failed to write trace logs: {trace_e}")
            # ---------------------

            # Parse Validation
            raw_data = json.loads(response.text)
            log_callback(f" Raw AI Response (First 3 items): {str(raw_data)[:300]}...")
            
            # Convert List[TopicAnalysis] -> Dict[Topic, Result]
            sanitized_data = {}
            
            # Create Fuzzy Map for matching
            # Map normalized string -> Original Exact String from Input
            topic_map = {t.strip().lower(): t for t in topics}
            
            # Pre-fill default "No"
            for t in topics:
                sanitized_data[t] = {"decision": "No", "reasoning": "No analysis returned."}
                
            matched_count = 0
            for item in raw_data:
                topic_name = item.get("topic", "")
                decision = item.get("decision", "No").capitalize() 
                if decision not in ["Yes", "No", "Unsure"]:
                    decision = "No"
                reasoning = item.get("reasoning", "")
                
                # Matching Logic
                target_key = None
                
                # 1. Exact Match
                if topic_name in sanitized_data:
                    target_key = topic_name
                # 2. Fuzzy Match (Case/Whitespace)
                elif topic_name.strip().lower() in topic_map:
                    target_key = topic_map[topic_name.strip().lower()]
                
                if target_key:
                    sanitized_data[target_key] = {
                        "decision": decision,
                        "reasoning": reasoning
                    }
                    matched_count += 1
                else:
                    logger.warning(f"Unmatched topic from AI: '{topic_name}'")
            
            log_callback(f"✅ Matched {matched_count}/{len(topics)} topics successfully.")
            return sanitized_data
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            last_exception = e
            
            # Check for Quota Limit (429) - Fail Fast? Or Retry? 
            # Usually Quota limits need a wait. Let's wait.
            if "429" in str(e) or "Quota exceeded" in str(e):
                 logger.error("Quota exceeded. Waiting before retry...")
                 time.sleep(5) # Wait longer for quota
            else:
                 time.sleep(2) # Standard backoff
                 
    # If we exit the loop, we failed all retries
    error_msg = f"Analysis failed after {max_retries} attempts. Last error: {last_exception}"
    
    # Check for Quota specifically to give the friendly message
    if last_exception and ("429" in str(last_exception) or "Quota exceeded" in str(last_exception)):
         friendly_msg = (
             f"**Gemini Quota Exceeded for {model_name}**\n\n"
             "You have hit the free tier limit. Please:\n"
             "1. Wait a a minute and try again.\n"
             "2. Switch to **gemini-2.5-flash** (it has higher limits).\n"
             "3. Or use a paid API key."
         )
         raise AIAnalysisError(friendly_msg) from last_exception
         
    raise AIAnalysisError(error_msg) from last_exception

class PriceDurationExtractionError(Exception):
    """Custom exception for price/duration extraction failures."""
    pass

def extract_price_duration_info(website_url, website_content, columns, api_key, model_name=None, log_callback=None):
    """
    Extracts price, duration, projects, and other information from website content using Gemini.
    Returns a dictionary mapping column names to extracted values.
    
    Args:
        website_url: The URL of the website
        website_content: The scraped text content from the website
        columns: List of column names to extract (e.g., ['Price', 'Duration', 'Projects', ...])
        api_key: Gemini API key
        model_name: Optional model name override
        log_callback: Optional callback function for logging
    
    Returns:
        Dictionary mapping column names to extracted values
    """
    genai.configure(api_key=api_key)
    
    if not log_callback:
        log_callback = lambda x: None # No-op
    
    # Priority: Model arg > Env PRO > Env LITE > Default
    if not model_name:
        model_name = os.getenv("GEMINI_PRO")
        if not model_name:
            model_name = os.getenv("GEMINI_LITE", "gemini-2.5-flash")
    
    logger.info(f"Using Gemini Model: {model_name} for price/duration extraction")
    log_callback(f"🔍 Extracting information using **{model_name}**")
    
    model = genai.GenerativeModel(model_name)
    
    # Filter out Provider, Course Name, Website Link from extraction (these are user inputs)
    columns_to_extract = [col for col in columns if col.lower() not in ['provider', 'course name', 'website link', 'remarks']]
    columns_json = json.dumps(columns_to_extract)
    
    prompt = f"""
## SYSTEM
You are an expert at extracting structured information from course/educational program websites.

### Task
Extract specific information from the provided website content. The website URL is: {website_url}

### Columns to Extract
{columns_json}

### Instructions
1. Extract information for each column listed above.
2. For "Price": Look for course fees, pricing, cost, subscription fees, etc. Include currency if mentioned.
3. For "Duration": Look for course duration, length, time to complete, hours, weeks, months, etc.
4. For "Projects": Look for number of projects, capstone projects, hands-on projects, assignments, etc.
5. For "Additional Services": Look for career support, mentorship, certification, job assistance, etc.
6. For "Eligibility Criteria": Look for prerequisites, requirements, eligibility, who can enroll, etc.
7. If information is not found for a column, use "Not specified" or "N/A".
8. Be precise and extract exact values when possible (e.g., "$999", "6 months", "5 projects").

### Output Format
Output MUST be a valid JSON object where keys are column names and values are the extracted information.

Example:
{{
  "Price": "$999 or INR 82,000",
  "Duration": "6 months",
  "Projects": "5 hands-on projects",
  "Additional Services": "Career support, 1-on-1 mentorship",
  "Eligibility Criteria": "Basic programming knowledge required"
}}

### Website Content:
{website_content[:10000]}  # Limit content to avoid token limits
"""
    
    max_retries = 2
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Price/Duration Extraction Attempt {attempt + 1}/{max_retries}")
            log_callback(f"🔄 Extraction Attempt {attempt + 1}/{max_retries}...")
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse JSON response
            extracted_data = json.loads(response.text)
            log_callback(f"✅ Successfully extracted information for {len(extracted_data)} fields")
            
            # Ensure all requested columns are present (fill with "Not specified" if missing)
            result = {}
            for col in columns_to_extract:
                result[col] = extracted_data.get(col, "Not specified")
            
            return result
            
        except Exception as e:
            logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
            last_exception = e
            
            if "429" in str(e) or "Quota exceeded" in str(e):
                logger.error("Quota exceeded. Waiting before retry...")
                time.sleep(5)
            else:
                time.sleep(2)
    
    # If we exit the loop, we failed all retries
    error_msg = f"Price/Duration extraction failed after {max_retries} attempts. Last error: {last_exception}"
    
    if last_exception and ("429" in str(last_exception) or "Quota exceeded" in str(last_exception)):
        friendly_msg = (
            f"**Gemini Quota Exceeded for {model_name}**\n\n"
            "You have hit the free tier limit. Please:\n"
            "1. Wait a minute and try again.\n"
            "2. Switch to **gemini-2.5-flash** (it has higher limits).\n"
            "3. Or use a paid API key."
        )
        raise PriceDurationExtractionError(friendly_msg) from last_exception
    
    raise PriceDurationExtractionError(error_msg) from last_exception
