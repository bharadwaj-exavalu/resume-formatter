import boto3
import json
import re

# -----------------------------
# AWS Bedrock Setup
# -----------------------------
bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

SKILL_FIELDS = [
    "programming_languages_and_frameworks",
    "web_services_and_integrations",
    "cms_platforms",
    "commerce_platforms",
    "databases",
    "crm_and_marketing_tools",
    "search_and_query_tools",
    "it_service_management_tools",
    "domain_knowledge",
    "other_skills",
]


# -----------------------------
# SAFE JSON PARSER (truncation-resilient)
# -----------------------------
def safe_json_load(text: str):
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output")

    json_str = match.group()
    json_str = re.sub(r'(?<!\\)\n', ' ', json_str)
    json_str = re.sub(r'[\x00-\x1F]+', ' ', json_str)

    # First attempt: parse as-is
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Second attempt: heal truncated JSON by closing unclosed brackets
    healed = heal_truncated_json(json_str)
    if healed:
        try:
            return json.loads(healed)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON even after healing. Raw snippet: {json_str[:200]}")


def heal_truncated_json(json_str: str) -> str:
    """
    Recovers a truncated JSON string by trimming back to the last complete
    item and closing all unclosed brackets/braces.
    """
    open_brackets = []
    in_string = False
    escape_next = False

    for ch in json_str:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            open_brackets.append(ch)
        elif ch in ('}', ']'):
            if open_brackets:
                open_brackets.pop()

    if not open_brackets:
        return json_str  # Already balanced

    trimmed = json_str.rstrip()
    trimmed = re.sub(r',\s*$', '', trimmed.rstrip())

    closing = ''
    for bracket in reversed(open_brackets):
        closing += ']' if bracket == '[' else '}'

    return trimmed + closing


# -----------------------------
# GENERIC LLM CALL
# -----------------------------
def call_llm(prompt: str, max_tokens=1000):
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    )

    result = json.loads(response["body"].read())
    text = result["content"][0]["text"].strip()

    print("\n🔍 LLM OUTPUT:\n", text)

    return safe_json_load(text)


# -----------------------------
# PROJECT CONTEXT EXTRACTOR
# -----------------------------
def extract_project_context(resume_text: str, search_term: str, window=1500) -> str:
    if not search_term:
        return resume_text[:window]

    idx = resume_text.lower().find(search_term.lower())

    if idx == -1:
        return resume_text[:window]

    start = max(0, idx - window // 2)
    end = min(len(resume_text), idx + window)

    return resume_text[start:end]


# -----------------------------
# PROMPTS
# -----------------------------
def profile_prompt(text):
    return f"""
Extract profile details.

Output:
{{ "profile": {{ "name": "", "current_title": "", "summary": [] }} }}

Rules:
- Max 5 summary bullets

Resume:
{text}
"""


def skills_prompt(text):
    return f"""
Extract technical skills.

Output:
{{ "technical_skills": {{
    "programming_languages_and_frameworks": [],
    "web_services_and_integrations": [],
    "cms_platforms": [],
    "commerce_platforms": [],
    "databases": [],
    "crm_and_marketing_tools": [],
    "search_and_query_tools": [],
    "it_service_management_tools": [],
    "domain_knowledge": [],
    "other_skills": []
}} }}

Rules:
- Always return every field, even if empty — use [] never null

Resume:
{text}
"""


def projects_prompt(text):
    return f"""
Extract ALL projects from this resume, including roles/positions at companies and standalone projects.

Output:
{{ "projects": [ {{ "company": "", "title": "" }} ] }}

Rules:
- If the work was done at a company/employer, set "company" to that company or client name (e.g. "Infosys", "TCS")
- "title" is the project or role name within that company
- If there is no associated company, leave "company" as empty string
- IMPORTANT: Group all work at the same company into ONE entry — do not create a separate entry per task or responsibility
- A person who worked at 3 companies should produce at most 3-6 entries total, not 15+

Resume:
{text}
"""


def project_detail_prompt(project_title: str, company_name: str, text: str):
    if company_name:
        title_instruction = f'Use "{company_name}" as the project_title.'
    else:
        title_instruction = 'Generate a concise, descriptive project_title from the work described.'

    return f"""
Extract FULL details for this project.
{title_instruction}
It is critical to extract and populate the project_description field with a clear summary of what the project does/did.
Output duration only if you have both start and end dates.

Project: {project_title}
Company: {company_name or "N/A"}

Output:
{{
  "project_title": "",
  "client_domain": "",
  "project_description": "",
  "designation": "",
  "duration": {{ "start": "", "end": "" }},
  "environment": [],
  "roles_and_responsibilities": []
}}

Rules:
- project_description must always be filled — describe the purpose and scope of the project
- environment and roles_and_responsibilities must always be lists, never null
- Max 4-5 responsibilities
- Keep concise

Resume:
{text}
"""


def education_prompt(text):
    return f"""
Extract education.

- Include all degrees (Bachelors, Masters, etc.)
- Extract degree name (e.g., B.Tech, M.Sc)
- Extract field of study
- Extract institution name
- Extract year or duration if available
- If not present, return empty list []

Output:
{{ "education": [ {{ "degree": "", "field_of_study": "", "institution": "", "year": "" }} ] }}

Resume:
{text}
"""


def cert_prompt(text):
    return f"""
Extract certifications from the resume.

Output:
{{ "certifications": [ {{ "name": "" }} ] }}

Rules:
- Each certification must be an object with a "name" field
- If no certifications are found, return an empty list: {{ "certifications": [] }}

Resume:
{text}
"""


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def extract_structured_data(resume_text: str) -> dict:

    data = {}

    # -----------------------------
    # PROFILE
    # -----------------------------
    data.update(call_llm(profile_prompt(resume_text)))

    # -----------------------------
    # SKILLS
    # -----------------------------
    data.update(call_llm(skills_prompt(resume_text)))

    # -----------------------------
    # PROJECT TITLES
    # -----------------------------
    projects_data = call_llm(projects_prompt(resume_text), max_tokens=800)
    project_list = projects_data.get("projects", [])

    projects = []

    # -----------------------------
    # PROJECT DETAILS
    # -----------------------------
    for proj_obj in project_list:
        try:
            if isinstance(proj_obj, dict):
                title = proj_obj.get("title", "")
                company = proj_obj.get("company", "")
            else:
                title = str(proj_obj)
                company = ""

            search_term = company or title
            context = extract_project_context(resume_text, search_term)

            proj = call_llm(
                project_detail_prompt(title, company, context),
                max_tokens=600
            )

            # Fallback: ensure project_title is always set
            if not proj.get("project_title"):
                proj["project_title"] = company or title

            # Fallback: ensure project_description is never empty
            if not proj.get("project_description"):
                proj["project_description"] = f"Project at {company}" if company else title

            # Fallback: ensure list fields are never None
            proj["environment"] = proj.get("environment") or []
            proj["roles_and_responsibilities"] = proj.get("roles_and_responsibilities") or []

            projects.append(proj)

        except Exception as e:
            print(f"⚠️ Project failed ({company or title}): {e}")

    data["project_history"] = projects

    # -----------------------------
    # EDUCATION
    # -----------------------------
    data.update(call_llm(education_prompt(resume_text)))

    # -----------------------------
    # CERTIFICATIONS (with string normalization)
    # -----------------------------
    raw_certs = call_llm(cert_prompt(resume_text)).get("certifications", [])
    data["certifications"] = [
        {"name": c} if isinstance(c, str) else c
        for c in raw_certs
    ]

    # -----------------------------
    # DEFAULT SAFETY
    # -----------------------------
    data.setdefault("education", [])
    data.setdefault("certifications", [])
    data.setdefault("technical_skills", {})

    # Sanitize all technical_skills fields — replace None/missing with []
    # Prevents Jinja2 | join() from crashing when LLM returns null
    for field in SKILL_FIELDS:
        if not data["technical_skills"].get(field):
            data["technical_skills"][field] = []

    # Sanitize all string values for XML safety
    # Raw & < > characters in LLM output (e.g. "AT&T", "R&D") break lxml
    return sanitize_for_xml(data)


def sanitize_for_xml(obj):
    """
    Recursively walks the data structure and escapes characters that would
    break XML parsing when injected into the docx template.
    """
    if isinstance(obj, str):
        return (
            obj
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    elif isinstance(obj, dict):
        return {k: sanitize_for_xml(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_xml(i) for i in obj]
    return obj