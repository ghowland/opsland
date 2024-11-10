"""
Execute Command: One module to handle the most important thing we do, generically
"""


import json
import time
import os

from logic import utility

from logic.log import LOG


def ExecuteCommand(config, command, bundle_name, bundle, set_cache_key, update_data=None):
  """Execute a command"""
  # Ensure we have unique input paths
  uuid = utility.GetUUID()

  # If this doesnt get set, then we dont need to remove the temporary file
  command_input_path = None

  # Create our output file, if specified
  if 'input' in command and 'input_path' in command:
    input_data = {}
    if update_data:
      input_data.update(update_data)

    for cache_key, output_spec in command['input'].items():
      # If we have formatting in our cache key
      before_cache_key = cache_key
      cache_key = utility.FormatTextFromDictDeep(cache_key, input_data)
      # LOG.info(f'Cache Key format: Before {before_cache_key}  After: {cache_key}')

      cache_value = config.cache.Get(bundle_name, cache_key)

      for spec_key, field_list in output_spec.items():
        input_data[spec_key] = utility.GetDataByDictKeyList(cache_value, field_list)
    
    command_input_path = command['input_path'].replace('{uuid}', uuid)
    utility.SaveJson(command_input_path, input_data)

    # LOG.debug(f'''Command Input Path: {command_input_path}''')

  command_unique = command['command'].replace('{uuid}', uuid)

  LOG.debug(f'''Execute Command Actual: {command_unique}''')

  # Set the CWD for the command
  running_cwd = config.directory_origin
  running_cwd = bundle['path']['default_execute_dir']
  if 'dir' in command:
    running_cwd = command['dir']
  
  # Execute the command
  (status, output, error) = utility.ExecuteCommand(command_unique, set_cwd=running_cwd)


  if status == 0:
    # LOG.debug(f'Output: {output}')
    pass
  else:
    LOG.debug(f'Status: {status}  Error: {error}')

  # If we got any output, parse it
  if output:
    payload = json.loads(output)
  # Else, we didnt, so just give an empty string
  else:
    LOG.info(f'No output available.  Returning empty string: {output}  Command: {command_unique}')
    payload = {}

  if type(payload) == dict:
    # All records get the time recorded.  We dont track creation time here, make a custom field if you want that.  But all records get a time field, as that is useful for many reasons
    payload['__time'] = time.time()

    #TODO(geoff): What authenticated user changed this record?
    pass

  config.cache.Set(bundle_name, set_cache_key, payload)

  # # Remove the temp file
  # if command_input_path:
  #   utility.RemoveFilePath(command_input_path)

  return payload
