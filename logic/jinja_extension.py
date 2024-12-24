"""
Jinja Extensions
"""

import json

from logic.log import LOG


def from_json(text_json):
  """Converts a JSON string to a Python object."""
  try:
    return json.loads(text_json)
  
  except json.JSONDecodeError as e:
    return f"Invalid JSON: {e}"


def content_search_single(all_content, search_data):
  """Returns a single search result."""
  if 'uuid' in search_data:
    return all_content[search_data['uuid'][0]]

  elif 'label' in search_data:
    for key, item in all_content.items():
      if key.startswith('_'): continue

      if search_data['label'] in item['labels']:
        return item
  
  # Return empty data, to be less Jinja-broken if no data
  return {}

