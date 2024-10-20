"""
Execute Command: One module to handle the most important thing we do, generically
"""


import json
import time

from logic import utility

from logic.log import LOG


def ExecuteCommand(config, command, bundle_name, set_cache_key, update_data=None):
  """Execute a command"""
  # Ensure we have unique input paths
  uuid = utility.GetUUID()

  # If this doesnt get set, then we dont need to remove the temporary file
  command_input_path = None

  # Create our output file, if specified
  if 'input' in command and 'input_path' in command:
    output_data = {}
    if update_data:
      output_data.update(update_data)

    for cache_key, output_spec in command['input'].items():
      cache_value = config.cache.Get(bundle_name, cache_key)

      for spec_key, field_list in output_spec.items():
        output_data[spec_key] = utility.GetDataByDictKeyList(cache_value, field_list)
    
    command_input_path = command['input_path'].replace('{uuid}', uuid)
    utility.SaveJson(command_input_path, output_data)

    LOG.debug(f'''Command Input Path: {command_input_path}''')

  command_unique = command['command'].replace('{uuid}', uuid)

  LOG.debug(f'''Execute Command Actual: {command_unique}''')

  (status, output, error) = utility.ExecuteCommand(command_unique)

  if status == 0:
    # LOG.debug(f'Output: {output}')
    pass
  else:
    LOG.debug(f'Status: {status}  Error: {error}')

  payload = json.loads(output)

  if type(payload) == dict:
    # All records get the time recorded.  We dont track creation time here, make a custom field if you want that.  But all records get a time field, as that is useful for many reasons
    payload['__time'] = time.time()

    #TODO(geoff): What authenticated user changed this record?
    pass

  config.cache.Set(bundle_name, set_cache_key, payload)

  # Remove the temp file
  utility.RemoveFilePath(command_input_path)

  return payload
