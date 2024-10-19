"""
Execute Command: One module to handle the most important thing we do, generically
"""


import json

from logic import utility

from logic.log import LOG


def ExecuteCommand(config, command):
  """Execute a command"""
  # Create our output file, if specified
  if 'input' in command['data'] and 'input_path' in command['data']:
    output_data = {}
    for cache_key, output_spec in command['data']['input'].items():
      cache_value = config.cache.GetBundleKeyDirect(command['bundle'], cache_key)

      for spec_key, field_list in output_spec.items():
        output_data[spec_key] = utility.GetDataByDictKeyList(cache_value, field_list)
    
    utility.SaveJson(command['data']['input_path'], output_data)
    LOG.debug(f'''Command Output Path: {command['data']['input_path']}''')


  (status, output, error) = utility.ExecuteCommand(command['data']['command'])

  if status == 0:
    LOG.debug(f'Output: {output}')
  else:
    LOG.debug(f'Status: {status}  Error: {error}')
    
  payload = json.loads(output)

  config.cache.SetBundleKeyData(command['bundle'], command['key'], payload)



