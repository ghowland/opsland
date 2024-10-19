"""
Execute Command: One module to handle the most important thing we do, generically
"""


import json

from logic import utility

from logic.log import LOG


def ExecuteCommand(config, command, bundle_name, set_cache_key, update_data=None):
  """Execute a command"""
  # Create our output file, if specified
  if 'input' in command and 'input_path' in command:
    output_data = {}
    if update_data:
      output_data.update(update_data)

    for cache_key, output_spec in command['input'].items():
      cache_value = config.cache.GetBundleKeyDirect(bundle_name, cache_key)

      for spec_key, field_list in output_spec.items():
        output_data[spec_key] = utility.GetDataByDictKeyList(cache_value, field_list)
    
    utility.SaveJson(command['input_path'], output_data)
    LOG.debug(f'''Command Output Path: {command['input_path']}''')


  (status, output, error) = utility.ExecuteCommand(command['command'])

  if status == 0:
    LOG.debug(f'Output: {output}')
  else:
    LOG.debug(f'Status: {status}  Error: {error}')

  payload = json.loads(output)

  config.cache.SetBundleKeyData(bundle_name, set_cache_key, payload)

  return payload



