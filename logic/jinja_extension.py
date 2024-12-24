"""
Jinja Extensions
"""

import json

def from_json(text_json):
  """Converts a JSON string to a Python object."""
  try:
    return json.loads(text_json)
  
  except json.JSONDecodeError as e:
    return f"Invalid JSON: {e}"

