"""
Job Scheduler: Watch our Job specifications for changes and hot reload them
"""


from logic.log import LOG

from logic import thread_base
from logic import local_secret


class JobScheduler(thread_base.ThreadBase):
  """Will loop in it's own thread, checking out the Job files for changes"""

  def Init(self):
    """Save our _data to vars"""
    # Memory of what we have done, so we can schedule jobs properly
    self.history = {}

    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.info(f'{self.name} Started')


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    LOG.info(f'{self.name}: Updated')

