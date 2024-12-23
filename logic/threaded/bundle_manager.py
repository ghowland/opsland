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
      self.LoadBundle(bundle_path, load_cache=True)
    
    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.debug(f'{self.name} Started')


  def LoadBundle(self, path, load_cache=False):
    """Load this bundle and update the timestamp"""
    bundle_data = utility.LoadYaml(path)

    with self._lock:
      # Process the Bundle, then store it
      self._ProcessBundleData(bundle_data)
      self._config.data[path] = bundle_data
      self.timestamps[path] = time.time()

    LOG.debug(f'Loaded Bundle: {path}')

    # If this is the first time, we want to load cache off storage so we start with the last data.  Allows smooth restarts
    if load_cache:
      self._config.cache.LoadInitialBundleCache(path, self.GetBundles())


  def _ProcessBundleData(self, bundle_data):
    """Go through the bundle data, and perform any processing steps.  ex: `_import_static_data`"""
    for method_key, method_data in bundle_data['http'].items():
      for endpoint_uri, endpoint_data in method_data.items():
        if '_import_static_data' in endpoint_data:
          for static_import in endpoint_data['_import_static_data']:
            found_static = bundle_data['static_data'].get(static_import, None)

            # If we dont have this, its a configuration error
            if found_static == None:
              LOG.error(f'Missing Static Data import: {static_import}')
              continue

            # Else, update our dictionary with it
            else:
              LOG.info(f'Bundle: Import Static Data: {method_key}: {endpoint_uri}: {', '.join([x.replace('execute.api.', '') for x in list(found_static['cache'].keys())])}')

              #TODO: Merge the dictionaries per level.  For now just straigth update which blows away peer data in deeper areas, so its not an nice overlay
              endpoint_data.update(found_static)


  def ExecuteTask(self, task):
    """Proess the task data dict"""
    # LOG.debug(f'{self.name}: Updated')

    for bundle_path in self._config.data:
      stat_result = os.stat(bundle_path)
      
      # If this file is newer, try to reload it
      if stat_result.st_ctime > self.timestamps[bundle_path]:
        self.LoadBundle(bundle_path, load_cache=True)
      
      # Load any new static content
      self._config.cache.LoadStaticImports()
  

  def GetBundles(self):
    """Returns a new dictionary that will not cause problems with threaded updates, so we can run without worry"""
    bundles = {}

    # Recreate the top 2 levels of our bundles with new dicts, so that threaded changes will do nothing for any execution
    with self._lock:
      for bundle in self._config.data:
        bundles[bundle] = dict(self._config.data[bundle])

    return bundles
