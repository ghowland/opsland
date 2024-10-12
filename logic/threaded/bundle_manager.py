"""
Bundle Manager: Watch our Bundle specifications for changes and hot reload them
"""


import time
import os

from logic.log import LOG

from logic import thread_base
from logic import utility


class BundleManager(thread_base.ThreadBase):
  """Will loop in it's own thread, checking out the bundle files for changes"""

  def Init(self):
    """Save our _data to vars"""
    # Latest bundle timestamps of when we last loaded it.  If the bundle is updated, load it again
    self.timestamps = {}

    for bundle_path in self._config.bundles:
      self.LoadBundle(bundle_path)
    
    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.debug(f'{self.name} Started')


  def LoadBundle(self, path):
    """Load this bundle and update the timestamp"""
    bundle_data = utility.LoadYaml(path)

    with self._lock:
      self._config.data[path] = bundle_data
      self.timestamps[path] = time.time()

    LOG.debug(f'Loaded Bundle: {path}')


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    # LOG.debug(f'{self.name}: Updated')

    for bundle_path in self._config.data:
      stat_result = os.stat(bundle_path)
      
      # If this file is newer, try to reload it
      if stat_result.st_ctime > self.timestamps[bundle_path]:
        self.LoadBundle(bundle_path)
