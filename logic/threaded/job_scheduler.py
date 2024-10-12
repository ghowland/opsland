"""
Job Scheduler: Watch our Job specifications for changes and hot reload them
"""


import time

from logic.log import LOG

from logic import thread_base
from logic import utility

from logic import thread_manager


class JobScheduler(thread_base.ThreadBase):
  """Will loop in it's own thread, checking out the Job files for changes"""

  def Init(self):
    """Save our _data to vars"""
    # Memory of what we have done, so we can schedule jobs properly
    self.history = {}

    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.debug(f'{self.name} Started')


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    # LOG.debug(f'{self.name}: Updated')

    bundles = thread_manager.BUNDLE_MANAGER.GetBundles()
    for bundle_path, bundle in bundles.items():
      # Skip bundles without schedules
      if 'schedule' not in bundle: continue

      # Schedule Periodic tasks
      for period_key, period_data in bundle['schedule'].get('period', {}).items():
        period = utility.ConvertStringDurationToSeconds(period_data['period'])
        key = f'schedule.period.{period_key}'

        # If we havent run this task before, or it's been over the period time since last run, schedule it to be run
        if key not in self.history or self.history[key] + period < time.time():
          task = {
            'bundle': bundle_path,
            'key': key,
            'data': period_data,
          }
          thread_manager.JOB_MANAGER.AddTask(task)

          # Save that we schedule it, so we wait until the period to do it again
          self.history[key] = time.time()

