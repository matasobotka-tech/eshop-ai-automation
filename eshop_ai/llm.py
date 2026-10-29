"""One place that talks to Claude: a request with a JSON schema, a checked answer back.

Every feature (product copy, inbox triage) goes through `ask_json`, so retries, refusals
and validation behave the same everywhere.
"""
import json
import os

DEFAULT_MODEL = "claude-opus-5-5"


class LLMError(Exception):
    """The model could not produce a usable answer (refusal, cut off, invalid JSON)."""


def ask_json(client, system, prompt, schema, max_tokens=4096, effort="low"):
    response = client.beta.messages.create(
        model=os.environ.get("ESHOP_AI_MODEL") or DEFAULT_MODEL,
        max_tokens=max_tokens,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise LLMError("model refused the request")
    if response.stop_reason == "max_tokens":
        raise LLMError("answer was cut off (max_tokens)")
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"invalid JSON from model: {e}") from e
    missing = [k for k in schema.get("required", []) if k not in data]
    if missing:
        raise LLMError(f"answer is missing fields: {', '.join(missing)}")
    return data


def obj(properties, required=None):
    """JSON-schema object helper: every field required, nothing extra allowed."""
    return {"type": "object", "properties": properties,
            "required": required or list(properties), "additionalProperties": False}
