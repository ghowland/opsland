"""
Job Manager: Watch our Job specifications for changes and hot reload them
"""


import json

from logic.log import LOG

from logic import thread_base
from logic import utility
from logic import thread_manager


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

    (status, output, error) = utility.ExecuteCommand(task['data']['command'])

    LOG.debug(f'Output: {output}')
    LOG.debug(f'Status: {status}  Error: {error}')
    payload = json.loads(output)

    self._config.cache.SetBundleKeyData(task['bundle'], task['key'], payload)



