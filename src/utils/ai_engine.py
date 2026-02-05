import google.generativeai as genai
import json
import os
import re
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

# --- Helpers for pricing/duration parsing ---
def _parse_price_amount(price_text):
    """
    Extracts numeric amount and currency symbol (if present) from a price string.
    Returns (amount_float, currency_prefix_or_empty).
    """
    if not price_text:
        return None, ""
    # Capture currency symbol (common ones) and number with optional commas/decimals
    match = re.search(r'(?P<currency>[$€£₹]?)\s*(?P<amount>[0-9][0-9,]*\.?[0-9]*)', price_text)
    if not match:
        return None, ""
    currency = match.group("currency") or ""
    amount_str = match.group("amount").replace(",", "")
    try:
        return float(amount_str), currency
    except ValueError:
        return None, currency

def _find_price_in_text(text):
    """
    Heuristic extraction of a course-fee-like token directly from raw text when the LLM
    fails to return one. We try to prioritize amounts near fee/price/enroll sections
    and avoid contest prizes, cookie text, etc.
    """
    if not text:
        return None

    # First, narrow down to regions likely to mention fees/pricing
    # e.g. around words like "Fee", "Fees", "Price", "Pricing", "Enroll Now"
    keyword_pattern = re.compile(
        r'(.{0,300}(fee|fees|price|pricing|program fee|course fee|enroll now).{0,300})',
        re.IGNORECASE | re.DOTALL,
    )
    price_pattern = re.compile(
        r'([₹$€£]\s?\d[\d,]*(?:\.\d+)?|\bINR\s?\d[\d,]*(?:\.\d+)?)',
        re.IGNORECASE,
    )

    for match in keyword_pattern.finditer(text):
        window = match.group(1)
        price_match = price_pattern.search(window)
        if price_match:
            return price_match.group(1).strip()

    # Fallback: search entire text if nothing found near fee/price-related keywords
    global_match = price_pattern.search(text)
    if global_match:
        return global_match.group(1).strip()
    return None

def _parse_duration_weeks(duration_text):
    """
    Parses duration text and attempts to convert to number of weeks.
    - If weeks specified, use directly.
    - If months specified, convert using 4 weeks per month.
    - If hours specified, approximate weeks assuming 10 hours/week.
    Returns float or None if not parseable.
    """
    if not duration_text:
        return None
    # weeks
    match_week = re.search(r'(\d+(\.\d+)?)\s*week', duration_text, re.IGNORECASE)
    if match_week:
        return float(match_week.group(1))
    # months -> 4 weeks each
    match_month = re.search(r'(\d+(\.\d+)?)\s*month', duration_text, re.IGNORECASE)
    if match_month:
        return float(match_month.group(1)) * 4
    # hours -> assume 10 hours per week
    match_hours = re.search(r'(\d+(\.\d+)?)\s*hour', duration_text, re.IGNORECASE)
    if match_hours:
        hours = float(match_hours.group(1))
        return hours / 10.0
    return None

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

def extract_price_duration_info(website_url, website_content, columns, api_key, model_name=None, log_callback=None, course_name=None):
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
    
    # Filter out Provider, Course Name, Website Link, Remarks from extraction (these are user inputs or optional)
    columns_to_extract = [col for col in columns if col.lower() not in ['provider', 'course name', 'website link', 'remarks']]
    columns_json = json.dumps(columns_to_extract)
    
    prompt = f"""
## SYSTEM
You are an expert at extracting structured information from course/educational program websites.

### Context
You are given website content from a competitor's course/educational program page. The website URL is: {website_url}
The specific program/course to focus on is: "{course_name}" (if mentioned on the page).

### Task
Extract specific information for EACH column listed below from the provided website content.

### Columns to Extract
{columns_json}

### Important Extraction Rules

1. **Price**:
   - Extract ONLY the total course price (full amount). Avoid per-month/per-week-only amounts unless that is explicitly the total.
   - Look for: course fees, total pricing, total cost, tuition, enrollment fees, payment plans, discounts, scholarships.
   - Include currency symbols and amounts (e.g., "$999", "INR 82,000", "€899").
   - If multiple total prices exist (tiers), include all totals (e.g., "Basic: $999; Premium: $1,499").
   - If payment plans are mentioned, include details (e.g., "$999 or 3 installments of $333") but the **Price** field must still contain the total amount.
   - If price is "Free" or "Free with conditions", extract exactly as stated.
   - Ignore contest prize amounts, salary figures, or monetary values related to hackathons, rewards, or marketing campaigns.
   - Ignore monetary values that appear in cookie policy text, generic site banners, or unrelated site sections.
   - If no total price for this specific program is found, use "Not specified".

2. **Duration**:
   - Look for: course duration, length, time to complete, hours, weeks, months, program length, study hours
   - Extract exact timeframes (e.g., "6 months", "12 weeks", "120 hours", "3-6 months")
   - If self-paced, mention it (e.g., "Self-paced (typically 3-6 months)")
   - If multiple duration options exist, include all (e.g., "Full-time: 3 months, Part-time: 6 months")
   - If no duration is found, use "Not specified"

3. **Projects**:
   - Look for: number of projects, capstone projects, hands-on projects, assignments, real-world projects, portfolio projects
   - Extract exact numbers when mentioned (e.g., "5 hands-on projects", "10 real-world projects")
   - Include project types if specified (e.g., "5 capstone projects + 10 mini-projects")
   - If projects are mentioned but count is not specified, describe what's available (e.g., "Multiple hands-on projects")
   - If no projects are mentioned, use "Not specified"

4. **Additional Services**:
   - Look for: career support, mentorship, certification, job assistance, placement support, resume review, interview prep, networking opportunities, community access, live sessions, Q&A sessions, office hours
   - Extract all services mentioned, separated by commas or semicolons
   - Be comprehensive - include any value-added services beyond the core curriculum
   - If no additional services are mentioned, use "Not specified"

5. **Eligibility Criteria**:
   - Look for: prerequisites, requirements, eligibility, who can enroll, background needed, educational requirements, experience level, technical skills required
   - Extract all eligibility requirements mentioned
   - Include both educational and technical prerequisites
   - If "No prerequisites" or "Beginner-friendly" is stated, extract that
   - If no eligibility criteria are mentioned, use "Not specified"

### Critical Guidelines

1. **Extract EVERY column** listed above. Do not skip any column.
2. **Be precise**: Extract exact values, numbers, and text as they appear on the website when possible.
3. **Be comprehensive**: If multiple values exist for a field, include all of them.
4. **Preserve formatting**: Keep currency symbols, units (months, weeks, hours), and special formatting.
5. **Use "Not specified"** ONLY when information is genuinely not found in the content.
6. **Do not infer or assume**: Only extract information that is explicitly stated or clearly implied in the content.
7. **Handle variations**: Recognize different phrasings (e.g., "course fee" = "price", "program length" = "duration").
8. **Extract from multiple sections**: Information may be scattered across different parts of the page (header, pricing section, curriculum section, etc.).

### Output Format

Output MUST be a valid JSON object where:
- Keys are the exact column names from the list above
- Values are the extracted information as strings
- ALL columns must be present in the output

Example Output:
{{
  "Price": "$999, INR 82,000, ₹82,000",
  "Duration": "6 months (self-paced, typically 3-6 months)",
  "Price/Week": "$166.50",
  "Projects": "5 hands-on capstone projects + 10 mini-projects",
  "Additional Services": "Career support, 1-on-1 mentorship, Resume review, Interview preparation, Job placement assistance",
  "Eligibility Criteria": "Basic programming knowledge required. No prior AI experience needed. Suitable for beginners."
}}

### Website Content:
{website_content[:25000]}
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
            
            # --- TRACE LOGGING ---
            try:
                trace_dir = "llm-trace"
                os.makedirs(trace_dir, exist_ok=True)
                
                with open(os.path.join(trace_dir, "price_duration_prompt.md"), "w", encoding="utf-8") as f:
                    f.write(prompt)
                    
                with open(os.path.join(trace_dir, "price_duration_output.json"), "w", encoding="utf-8") as f:
                    f.write(response.text)
                    
                log_callback(f"📁 Extraction trace saved to {trace_dir}/")
            except Exception as trace_e:
                logger.warning(f"Failed to write trace logs: {trace_e}")
            # ---------------------
            
            # Parse JSON response
            extracted_data = json.loads(response.text)
            log_callback(f"✅ Successfully extracted information for {len(extracted_data)} fields")
            
            # Ensure all requested columns are present (fill with "Not specified" if missing)
            result = {}
            for col in columns_to_extract:
                result[col] = extracted_data.get(col, "Not specified")
            
            # Heuristic fallback for Price if LLM missed it
            if result.get("Price") in ["Not specified", None, ""]:
                fallback_price = _find_price_in_text(website_content)
                if fallback_price:
                    result["Price"] = fallback_price
                    log_callback(f"Filled Price from heuristic: {fallback_price}")
            
            # Compute Price/Week if possible
            price_text = result.get("Price", extracted_data.get("Price"))
            duration_text = result.get("Duration", extracted_data.get("Duration"))
            amount, currency = _parse_price_amount(price_text)
            weeks = _parse_duration_weeks(duration_text)
            if amount is not None and weeks and weeks > 0:
                per_week = amount / weeks
                prefix = currency if currency else ""
                result["Price/Week"] = f"{prefix}{per_week:,.2f}"
            else:
                result["Price/Week"] = extracted_data.get("Price/Week", "Not specified")
            
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
