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
