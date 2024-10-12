"""
Bundle Manager: Watch our Bundle specifications for changes and hot reload them
"""


import time
import os

from logic.log import LOG

from logic import thread_base
from logic import utility
from logic import thread_manager


class BundleManager(thread_base.ThreadBase):
  """Will loop in it's own thread, checking out the bundle files for changes"""

  def Init(self):
    """Save our _data to vars"""
    # Latest bundle timestamps of when we last loaded it.  If the bundle is updated, load it again
    self.timestamps = {}

    for bundle_path in self._config.bundles:
      self.LoadBundle(bundle_path, load_cache=True)
    
    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.debug(f'{self.name} Started')


  def LoadBundle(self, path, load_cache=False):
    """Load this bundle and update the timestamp"""
    bundle_data = utility.LoadYaml(path)

    with self._lock:
      self._config.data[path] = bundle_data
      self.timestamps[path] = time.time()

    LOG.debug(f'Loaded Bundle: {path}')

    # If this is the first time, we want to load cache off storage so we start with the last data.  Allows smooth restarts
    if load_cache:
      self._config.cache.LoadInitialBundleCache(path, self.GetBundles())


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    # LOG.debug(f'{self.name}: Updated')

    for bundle_path in self._config.data:
      stat_result = os.stat(bundle_path)
      
      # If this file is newer, try to reload it
      if stat_result.st_ctime > self.timestamps[bundle_path]:
        self.LoadBundle(bundle_path)
  

  def GetBundles(self):
    """Returns a new dictionary that will not cause problems with threaded updates, so we can run without worry"""
    bundles = {}

    # Recreate the top 2 levels of our bundles with new dicts, so that threaded changes will do nothing for any execution
    with self._lock:
      for bundle in self._config.data:
        bundles[bundle] = dict(self._config.data[bundle])

    return bundles
