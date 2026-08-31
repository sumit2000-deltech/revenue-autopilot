import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"


def diagnose_opportunity(evidence: dict) -> dict:
    """
    Takes an evidence bundle (from get_opportunity_details) and returns
    a diagnosis + candidate actions, grounded only in the given evidence.
    """
    prompt = f"""You are analyzing a single abandoned checkout for an online audio-accessories merchant.

Evidence (this is the ONLY information you may use — do not invent any numbers or facts):
{json.dumps(evidence, indent=2)}

Based ONLY on this evidence, respond with a JSON object in this exact shape:
{{
  "diagnosis": "one or two sentences on why this customer likely abandoned, grounded in the evidence",
  "candidate_actions": [
    {{"action": "short name", "reasoning": "why this could work, grounded in evidence"}},
    {{"action": "short name", "reasoning": "..."}}
  ]
}}

Return ONLY valid JSON, no other text."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    return json.loads(raw)


if __name__ == "__main__":
    from app.data.analytics import get_abandoned_orders, get_opportunity_details

    sample_order = get_abandoned_orders()[0]
    evidence = get_opportunity_details(sample_order.id)

    print("Evidence given to the LLM:")
    print(json.dumps(evidence, indent=2))

    result = diagnose_opportunity(evidence)

    print("\nLLM diagnosis:")
    print(json.dumps(result, indent=2))