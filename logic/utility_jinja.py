"""
Utilities for Jinja

We want to make filters and functions for Jinja and put them here, so they can be added to the Jinja environment
"""

from jinja2 import Environment, Template, FileSystemLoader, select_autoescape, pass_context


# Define a custom filter to render the variable as a template
@pass_context
def RenderAsTemplate(ctx, template_str):
  """Render variables in Jinja as if it's a template, so we can use embedded variables"""
  env = Environment()
  tmpl = env.from_string(template_str)
  return tmpl.render(ctx)


def DataDottedKeyGet(input_data, dotted_keys, missing_value='Missing', return_errors=False):
  """Takes the input_dict as and extracts data out of it using the dotted keys as a list of keys or indexes"""
  keys = dotted_keys.split('.')

  value = input_data
  for key in keys:
    if type(value) in [list, tuple]:
      try:
        value = int(key)
      except:
        if return_errors:
          return f'Failed to access sequence:  Key: {key}: {value}'
        else:
          return missing_value
    elif type(value) == dict:
      if key in value:
        value = value[key]
      else:
        if return_errors:
          return f'Missing key:  Key: {key}: {value}'
        else:
          return missing_value
    else:
      if return_errors:
        return f'Cant index value type:  Key: {key}: {value} {type(value)}'
      else:
        return missing_value
  
  # Return the final value
  return value


def AddJinjaUtilities(templates):
  """Add all the global functions and """
  # Add all our Filter funcitons
  templates.env.filters['dotted_get'] = DataDottedKeyGet
  templates.env.filters['render'] = RenderAsTemplate

  #TOOD(g): How to add Functions:
  # jinja_env.globals['function_name'] = FunctionName

