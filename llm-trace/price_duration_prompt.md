
## SYSTEM
You are an expert at extracting structured information from course/educational program websites.

### Context
You are given website content from a competitor's course/educational program page. The website URL is: https://dfl.iiit.ac.in/programs/cert/aai
The specific program/course to focus on is: "Engineering Agentic AI Systems: From Concepts to Practice" (if mentioned on the page).

### Task
Extract specific information for EACH column listed below from the provided website content.

### Columns to Extract
["Price", "Duration", "Price/Week", "Projects", "Additional Services", "Eligibility Criteria"]

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
{
  "Price": "$999, INR 82,000, ₹82,000",
  "Duration": "6 months (self-paced, typically 3-6 months)",
  "Price/Week": "$166.50",
  "Projects": "5 hands-on capstone projects + 10 mini-projects",
  "Additional Services": "Career support, 1-on-1 mentorship, Resume review, Interview preparation, Job placement assistance",
  "Eligibility Criteria": "Basic programming knowledge required. No prior AI experience needed. Suitable for beginners."
}

### Website Content:
Agentic AI: From Concepts to Practice - IIIT Hyderabad Certificate Course By IIIT Hyderabad Engineering Agentic AI Systems: From Concepts to Practice A focused, engineering-first curriculum with hands-on labs and practical application. Apply Now Watch Overview 12 Weeks 4 Modules 100% Online Program Outcomes Design and architect production-ready Agentic AI systems from scoping to deployment Implement and integrate autonomous agents using engineering best practices and modern toolchains Deploy, monitor and maintain agentic systems with observability, testing and operations Work through end-to-end case studies solving real-world scenarios and evaluating trade-offs Deadline extended till January 12, 2026 Why This Program A focused, engineering-first curriculum that teaches you how to build, test and run agentic AI systems in production. Use-case Driven Learning Approach Hands-on, example-led modules that focus on real-world agentic AI use cases and their engineering implications. Industry-Relevant Tools & Frameworks Training with modern toolchains and frameworks used in production agentic systems. Complete Engineering Lifecycle Coverage Covering design, implementation, testing, deployment, and operations - the full engineering lifecycle. Course Structure Comprehensive curriculum designed to take you from fundamentals to advanced implementation of agentic AI architectures 12 Weeks Total duration 4 Modules 1 Foundations of Agentic AI Overview of AI-enabled systems Architecting AI-enabled systems Essentials of LLMs, Prompting and Retrieval Augmented Generation Understanding the agentic paradigm: autonomy, reasoning, and planning 2 Designing Agentic AI Systems Architectural patterns for Agentic AI Quality attributes and trade-offs in Agentic AI systems Orchestration and coordination strategies for multi-agent workflow Industrial Case study of designing an Agentic AI system 3 Agent Engineering and Implementation The agentic reasoningplanningaction loop Function calling, Tool use and Memory: MCP, A2A and beyond Frameworks and tools for implementing Agentic AI systems Practical Implementation Strategies through real-world examples 4 Evaluation, Deployment and Ops Testing, benchmarking, and evaluation of Agentic AI systems Deployment and Monitoring Production Ready Agents: AgentOps and Maintainability Emerging trends, best practices and Opportunities Course Instructor Karthik Vaidhyanathan Assistant Professor SERC, IIIT Hyderabad, India PhD from Gran Sasso Science Institute, Italy, postdoc at University of L'Aquila. His main research interests lie in the intersection of Software Engineering and AI, with a specific focus on using AI in particularly Generative and Agentic AI, for improving Software Engineering practices as well as on Engineering Sustainable AI-enabled systems Prof. Karthik Vaidhyanathan brings over five years of industry experience and leads a research lab that produces world-class publications in AI and Software Engineering. He currently serves as Associate Editor for IEEE Software. Profile Contact Areas of Expertise Software Architecture Agentic AI Generative AI Self-Adaptive Systems AI-Enabled Systems Eligibility Criteria This course is open to everyone interested in learning about Agentic AI Age Requirement 18+ years old Programming Skills Basic programming knowledge is compulsory. Basic Mathematics Comfortable with basic mathematics. Commitment Able to dedicate 12 hours per week for the 12-week duration Note: Background in basic mathematics (functions and their plots) and experience with computer programming (iteration, function calls) is must. Program Outcomes Design Agentic AI systems considering different trade-offs Design Agentic AI systems considering different trade-offs Build Production-Ready Agentic AI Systems from Scratch Build Production-Ready Agentic AI Systems from Scratch Learn Deployment and Operations for AI Agents Learn Deployment and Operations for AI Agents Understand Testing and Evaluation Frameworks Understand Testing and Evaluation Frameworks Ready to Transform Your AI Career? Join our comprehensive Agentic AI program and become a leader in the next generation of artificial intelligence. Apply Now Start Your Journey Course Fees Invest in your future with comprehensive Agentic AI training Indian Residents 56,640 (48,000 + 18% GST) International Students $1,440 SAARC Students $720 What's Included Access to all course materials and recordings Hands-on labs and coding assignments Professional certificate from IIIT Hyderabad Access to course community and forums Re-examination Fees If you don't pass the final exam on the first attempt, you can retake it after a week for the following fee Indian Residents 2,360 (2,000 + 18% GST) International Students $60 SAARC Students $30 Important Dates Event Date Applications Open November 14, 2025 Applications Close January 12, 2026 Course Start Date January 19, 2026 Frequently Asked Questions What are the prerequisites for this course? Programming experience (preferably Python) and basic mathematics (understanding of functions and plots) are required. Familiarity with basic machine learning concepts such as classification, regression, and neural networks is a plus but not required. How is the course delivered? The course is delivered 100% online with pre-recorded video lectures. What is the time commitment required? Plan to dedicate 12 hours per week for 12 weeks. This includes watching lectures (4-6 hours), completing assignments, and working on projects. Do I need a GPU or any dedicated hardware for this course? No GPU is required for the course assignments, as you can complete all work using Google Colab for free with a Gmail account. For exploratory work beyond the assignments, GPU hardware remains optional; you can instead use free API keys, run local models via Ollama, or purchase API credits from model providers, meaning a local GPU is only necessary if you specifically wish to run models directly on your laptop. What level of technical depth and academic rigor can I expect from this course? The course maintains the same rigor as IIIT Hyderabad's on-campus courses. Assignments and exams are intentionally challenging not as a barrier, but to ensure genuine learning. The course progresses from foundations to production-ready systems, covering both practical implementation and cutting-edge research perspectives. What are the passing requirements? You must pass the final exam to receive a completion certificate. You can take the exam at most two times. What kinds of applications can I build with what I learn? Adopting a use-case driven approach, you will learn to build applications ranging from simple automated trip planners that book flights and generate tickets to complex software systems that automate entire lifecycles. The course covers essential architectural patterns such as sequential agent chains, master-slave hierarchies, and collaborative structures while teaching you how to evaluate cost-performance trade-offs and implement "human-in-the-loop" designs for scenarios requiring oversight. What will I receive on course completion? Upon completion, you receive a completion certificate from IIIT Hyderabad and 5 academic credits that accrue to your Academic Bank of Credits (ABC) if you provide your ABC ID. These credits may also be applied towards degrees or diplomas at other universities depending upon the specific university's requirements. For example, some universities may recognize this as a 5-credit course, while others may recognize this as a course with fewer credits. That depends entirely on the university recognizing the course. IIIT has no control over course credit policies of other universities. If you don't meet the passing requirements, you receive a participation certificate instead of a completion certificate, without the 5 credits. What kind of placement or career support is provided? Currently, we do not have an official placement or career support mechanism in place for online students. This may, however, change in the future. Students will be informed of the changes, if any. What is the refund policy? Course fee needs to be paid in entirety as a necessary condition for admission to the program. Once paid, the fee cannot be refunded. When will the final exam be held? This edition of the program officially starts on 19th January 2026 and runs for 11 weeks. The final exam will be in the 12th week, i.e., week of 6th April 2026. For those who missed the final exam, or wish to re-take it, they can do so for a fee. The re-exam will be held 1 week after the first final exam, i.e., week of 13th April 2026. How long will the course material be available? All the course material will be available till the conducting of the re-exam. Who should I contact for questions? You can email us at ask@dfl.iiit.ac.in to open Gmail compose. Apply Now
