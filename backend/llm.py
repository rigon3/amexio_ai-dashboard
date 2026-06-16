"""
llm.py — View-aware natural-language summaries via Ollama.

Each dashboard view (training_budget, employees, home, sick_leave) has its own
system prompt and a context builder that turns aggregated data into the user
message. generate_summary() dispatches on `view` and returns {brief, standard}.
"""

import json
import re

import ollama

from data import aggregate_training_budget, aggregate_employees

MODEL = "llama3.1:8b"


# ─────────────────────────────────────────────────────────────────────────────
# System prompts (per view)
# ─────────────────────────────────────────────────────────────────────────────

TRAINING_BUDGET_PROMPT = """You are an HR analytics assistant. Your job is to write concise, professional natural language summaries of training budget data.

## Output format rules

- Word count: 70–150 words for the standard summary; 1–2 sentences for the brief summary
- Sentences: 3–5 for standard; exactly 2 for brief
- Paragraphs: 1–3 for standard
- Structure model: inverted pyramid (most important first)

## Sentence roles (standard summary, in order)

S1 — Overview: total budget, total spent, overall utilisation %, scope (all departments)
S2 — Primary finding: the department with the HIGHEST utilisation %. Use a causal verb. Include absolute spent, utilisation %, and its share of total expenditure.
S3 — Supporting findings: every department that is NOT the highest and NOT the lowest utilisation. Group them where rates are similar. Include specific numbers. Do NOT mention the lowest utilisation department here — it belongs only in S4.
S4 — Exception: the single department with the LOWEST utilisation % only. Neutral tone, no negative judgment. Do not include other departments here.
S5 — Context (optional): explains WHY the exception occurred

The brief summary is EXACTLY two sentences: S1 (overview) then S2 (highest utilisation department). Do not stop after one sentence. Do not add a third sentence.

## Rules

- Open with an overview sentence before any detail
- Cover ALL departments, not just the dominant one
- Never ignore outliers
- Vary vocabulary — do not repeat words like "utilised" or "spent"
- Include both absolute values and percentages where possible
- One analytical insight explaining WHY is allowed, but not required

## Important: data shape

The data is a UTILISATION SNAPSHOT for the stated period — not a period-over-period comparison. There is no "growth" or "increase". The fields are:
- total_budget: the full allocated training budget
- total_spent: how much has been used so far
- total_remaining: unspent budget
- utilisation_pct: spent / budget * 100
Do NOT describe this as a rise or increase over time. Describe it as utilisation of an allocated budget.

## Critical rule on department names

Use ONLY the exact "name" values from the by_department array in the data. Never substitute, invent, or reuse names from anywhere else.

## Response format

Respond with ONLY a JSON object in this exact shape — no markdown, no explanation:
{"standard": "<full S1–S5 here>"}
"""


EMPLOYEES_PROMPT = """You are an HR analytics assistant. Your job is to write concise, professional natural language summaries of workforce composition data.

## Output format rules

- Word count: 70–150 words for the standard summary; 1–2 sentences for the brief summary
- Sentences: 3–5 for standard; exactly 2 for brief
- Structure model: inverted pyramid (most important first)

## Sentence roles (standard summary, in order)

S1 — Overview: total headcount, how many are active, and the number of departments.
S2 — Primary finding: the LARGEST department by headcount. Include its count and its share of total headcount.
S3 — Supporting findings: the middle departments (NOT the largest and NOT the smallest). Group where similar. Include counts. Do NOT mention the smallest department here — it belongs only in S4.
S4 — Exception: the single SMALLEST department by headcount only. Neutral tone, no negative judgment.
S5 — Context (optional): the full-time/part-time split or the gender balance.

The brief summary is EXACTLY two sentences: S1 (overview) then S2 (largest department). Do not stop after one sentence. Do not add a third sentence.

## Rules

- Open with an overview sentence before any detail
- Cover ALL departments, not just the largest
- Never ignore the smallest department
- Vary vocabulary — do not repeat words like "department" or "employees" excessively
- Include both absolute counts and percentages where possible

## Important: data shape

This is a CURRENT WORKFORCE SNAPSHOT — not a change over time. Describe composition (how many, where), not growth.

## Critical rule on department names

Use ONLY the exact "name" values from the by_department array in the data. Never substitute, invent, or reuse names from anywhere else.

## Response format

Respond with ONLY a JSON object in this exact shape — no markdown, no explanation:
{"standard": "<full S1–S5 here>"}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Shared Ollama call + response parsing
# ─────────────────────────────────────────────────────────────────────────────

def _run_chat(system_prompt: str, user_message: str) -> dict:
    """Call the model, parse the JSON 'standard' field, derive the brief."""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        options={"temperature": 0.3},
    )

    standard = _parse_standard(response.message.content)

    # Brief = first two sentences of the standard
    sentences = [s.strip() for s in standard.split(". ") if s.strip()]
    brief = ". ".join(sentences[:2])
    if not brief.endswith("."):
        brief += "."

    return {"brief": brief, "standard": standard}


def _parse_standard(raw: str) -> str:
    """Extract the standard summary text. Tries strict JSON first, then falls
    back to grabbing the text after "standard": — the 8B model sometimes emits
    the value unquoted with raw newlines, which is not valid JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    text = None
    try:
        text = json.loads(raw)["standard"]
    except Exception:
        m = re.search(r'"standard"\s*:\s*(.*)', raw, re.DOTALL)
        text = m.group(1) if m else raw
        text = text.strip().rstrip("}").strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

    return re.sub(r"\s+", " ", text).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Per-view context builders → (system_prompt, user_message)
# ─────────────────────────────────────────────────────────────────────────────

def _build_training_budget(period: str = "monthly", month: str | None = None):
    data = aggregate_training_budget(period=period, month=month)
    departments = data["by_department"]
    primary = departments[0]["name"]
    exception = departments[-1]["name"]
    supporting = [d["name"] for d in departments[1:-1]]

    user_message = (
        "Generate a training budget utilisation summary using the rules above.\n\n"
        f"Data:\n{json.dumps(data, indent=2)}\n\n"
        f"Currency: euros (€). Period: {data['period_label']}. "
        "This is a utilisation snapshot — describe how much of the budget has been used, not growth over time. "
        f"S2 must be about {primary} (highest utilisation). "
        f"S3 must mention ALL of these departments — do not skip any: {', '.join(supporting)}. "
        f"S4 must be about {exception} (lowest utilisation). "
        "Return only the JSON object as specified."
    )
    return TRAINING_BUDGET_PROMPT, user_message


def _build_employees(period: str = "monthly", month: str | None = None):
    # Employees has no time dimension — period/month are ignored.
    data = aggregate_employees()
    departments = data["by_department"]
    primary = departments[0]["name"]
    smallest = departments[-1]["name"]
    middle = [d["name"] for d in departments[1:-1]]

    user_message = (
        "Generate a workforce composition summary using the rules above.\n\n"
        f"Data:\n{json.dumps(data, indent=2)}\n\n"
        "This is a current workforce snapshot — describe composition, not growth over time. "
        f"S2 must be about {primary} (largest department). "
        f"S3 must mention ALL of these departments — do not skip any: {', '.join(middle)}. "
        f"S4 must be about {smallest} (smallest department). "
        "Return only the JSON object as specified."
    )
    return EMPLOYEES_PROMPT, user_message


# view -> builder. Add home / sick_leave here as their data lands.
VIEW_BUILDERS = {
    "training_budget": _build_training_budget,
    "employees": _build_employees,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

# Views whose data source isn't connected yet. These return a friendly
# placeholder (no LLM call). To make one real: write a context builder, add it
# to VIEW_BUILDERS, and remove the entry here.
STUB_VIEWS = {
    "home": "The HR overview summary will be available once the Home page data source is connected.",
    "sick_leave": "The sick leave summary will be available once the absence data source is connected.",
}


def generate_summary(view: str = "training_budget", period: str = "monthly", month: str | None = None) -> dict:
    if view in STUB_VIEWS:
        msg = STUB_VIEWS[view]
        return {"brief": msg, "standard": msg}

    builder = VIEW_BUILDERS.get(view)
    if builder is None:
        raise ValueError(
            f"Unknown view '{view}'. Available: {', '.join(VIEW_BUILDERS)} "
            f"(stubbed: {', '.join(STUB_VIEWS)})"
        )
    system_prompt, user_message = builder(period=period, month=month)
    return _run_chat(system_prompt, user_message)
