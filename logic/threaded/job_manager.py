"""
Job Manager: Watch our Job specifications for changes and hot reload them
"""


import json

from logic.log import LOG

from logic import thread_base
from logic import execute_command


class JobManager(thread_base.ThreadBase):
  """Will loop in it's own thread, checking out the Job files for changes"""

  def Init(self):
    """Save our _data to vars"""
    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.debug(f'{self.name} Started')


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    LOG.info(f'{self.name}: Executing Task: {task}')

    # Skip initial empty task
    if 'data' not in task:
      LOG.error(f'Cant execute this task, skipping: {task}')
      return

    # Execute this command.  We wrap it here so we can call this from mutliple paths and all are handled the same
    execute_command.ExecuteCommand(self._config, task)

    # # Create our output file, if specified
    # if 'input' in task['data'] and 'input_path' in task['data']:
    #   output_data = {}
    #   for cache_key, output_spec in task['data']['input'].items():
    #     cache_value = self._config.cache.GetBundleKeyDirect(task['bundle'], cache_key)

    #     for spec_key, field_list in output_spec.items():
    #       output_data[spec_key] = utility.GetDataByDictKeyList(cache_value, field_list)
      
    #   utility.SaveJson(task['data']['input_path'], output_data)
    #   LOG.debug(f'''Command Output Path: {task['data']['input_path']}''')


    # (status, output, error) = utility.ExecuteCommand(task['data']['command'])

    # LOG.debug(f'Output: {output}')
    # LOG.debug(f'Status: {status}  Error: {error}')
    # payload = json.loads(output)

    # self._config.cache.SetBundleKeyData(task['bundle'], task['key'], payload)



