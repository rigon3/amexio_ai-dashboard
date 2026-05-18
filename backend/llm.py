import json
import ollama

MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are an HR analytics assistant. Your job is to write concise, professional natural language summaries of training budget data.

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

The data is a UTILISATION SNAPSHOT — not a period-over-period comparison. There is no "growth" or "increase". The fields are:
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


def generate_summary(data: dict) -> dict:
    departments = data["by_department"]
    primary = departments[0]["name"]
    exception = departments[-1]["name"]
    supporting = [d["name"] for d in departments[1:-1]]

    user_message = (
        "Generate a training budget utilisation summary using the rules above.\n\n"
        f"Data:\n{json.dumps(data, indent=2)}\n\n"
        "Currency: euros (€). Period: 2026. "
        "This is a utilisation snapshot — describe how much of the budget has been used, not growth over time. "
        f"S2 must be about {primary} (highest utilisation). "
        f"S3 must mention ALL of these departments — do not skip any: {', '.join(supporting)}. "
        f"S4 must be about {exception} (lowest utilisation). "
        "Return only the JSON object as specified."
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        options={"temperature": 0.3},
    )

    raw = response.message.content.strip()

    # Strip markdown code fences if the model added them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    parsed = json.loads(raw)
    standard = parsed["standard"]

    # Derive brief from the first two sentences of the standard
    sentences = [s.strip() for s in standard.replace("  ", " ").split(". ") if s.strip()]
    brief = ". ".join(sentences[:2])
    if not brief.endswith("."):
        brief += "."

    return {"brief": brief, "standard": standard}
