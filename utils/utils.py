import json


def clean_json(text):
    if isinstance(text, dict):
        return text  # Already a dictionary, return as is
    if isinstance(text, str):
        text = text.strip()
        # Remove Markdown code block markers if present
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except Exception:
            return text  # If not valid JSON, return as is
    return text
