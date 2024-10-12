"""
Cache Manager: This is the generic place to store all data.

There will be locking once you are into a bucket, so we have locks, but can also work faster than globally locking all changes.

This can be backed with DBs or other persistent storage (file system), or run just in memory.  The Bundle specifies how to store the cache values.
"""

import threading
from collections import deque

from logic.log import LOG

from logic import thread_manager
from logic import utility
from logic import local_cache


# Cannot have a queue size larger than this
DEFAULT_MAX_QUEUE_SIZE = 1000


class CacheManager():
  """This is the primary database interface.  Everything is treated as a big bucket system."""

  def __init__(self, config):
    # Store our config, everything uses it
    self.config = config

    # At the top level, all bundles will have separate data from each other
    self.bundles = {}

    # All our locks, to make sure we dont have dictionary problems
    self.lock_bundles_all = threading.Lock()

    # Every bundles cache is a Silo, and we need locks for all of them
    self.lock_bundles_each = {}


  def LoadInitialBundleCache(self, bundle_name, bundles):
    """As we load bundles for the first time, load any cached data they had as well"""
    if bundle_name not in bundles:
      LOG.error(f'Missing Bundle, cant load initial bundle cache: {bundle_name}')
      return
    
    bundle_data = bundles[bundle_name]

    cache_glob = bundle_data['cache_path'].replace('{key}', '*')
    paths = utility.Glob(cache_glob)

    for path in paths:
      path_key = utility.GlobReverse(cache_glob, path)

      # LOG.info(f'Path Key: {cache_glob} -> {path} -> {path_key}')

      cache_value = local_cache.GetData(path)

      self.SetBundleKeyData(bundle_name, path_key, cache_value, set_all_data=True)


  def GetBundleSilo(self, name):
    """Returns the entire Bundle dict, with all items inside the bundle"""
    with self.lock_bundles_all:
      # Ensure we have a dictionary to store the Bundle data, and a lock for each
      if name not in self.bundles:
        self.bundles[name] = {}
        self.lock_bundles_each[name] = threading.Lock()
      
      return self.bundles[name]


  def GetCacheDataByKey(self, bundle_name, bundle_data, cache_key):
    """Get the spec for this `cache_key`, because its strictly-named, we can reverse it"""
    part_cache_key = cache_key
    
    # Schedule Job keys
    if part_cache_key.startswith('schedule.'):
      part_cache_key = part_cache_key.replace('schedule.', '', 1)

      # Periodic job keys
      if part_cache_key.startswith('period.'):
        part_cache_key = part_cache_key.replace('period.', '', 1)

        if 'schedule' in bundle_data and 'period' in bundle_data['schedule'] and part_cache_key in bundle_data['schedule']['period']:
          return bundle_data['schedule']['period'][part_cache_key]
    
    return None


  def GetBundleKeyData(self, bundle_name, name, default=None, single=True):
    """Returns a single Bundle dict item.  If not found, returns `default`.  If `single`==True will only return 1 value, otherwise the raw values"""
    bundle = self.GetBundleSilo(bundle_name)

    # LOG.info(f'Get Bundle Key: {bundle_name}  Key: {name}')

    bundles = thread_manager.BUNDLE_MANAGER.GetBundles()
    bundle_data = bundles[bundle_name]

    cache_data = self.GetCacheDataByKey(bundle_name, bundle_data, name)
    if not cache_data: return None

    with self.lock_bundles_each[bundle_name]:
      if cache_data.get('store', 'single') == 'single':
        return bundle.get(name, default)

      elif cache_data.get('store', 'single') == 'queue':
        # If we dont have this queue yet, or it has no items
        if name not in bundle or len(bundle[name]) == 0: return None
        
        # Return the latest item
        return bundle[name][-1]


  def SetBundleKeyData(self, bundle_name, name, value, set_all_data=False):
    """Set the value of the bundle cache"""
    bundle = self.GetBundleSilo(bundle_name)

    bundles = thread_manager.BUNDLE_MANAGER.GetBundles()
    bundle_data = bundles[bundle_name]

    # LOG.info(f'Bundle: {bundle_name}  Data: {bundle_data}')

    with self.lock_bundles_each[bundle_name]:
      path = bundle_data['cache_path'].replace('{key}', name)

      # Determine the type of the value, so we know how to store it properly
      cache_data = self.GetCacheDataByKey(bundle_name, bundle_data, name)
      if not cache_data: return
      # LOG.info(f'Cache Data for Set Key: {bundle_name}  Data: {bundle_data}  Cache Key: {name}  Cache: {cache_data}')

      # If Single value storage.  This is the default if nothing is specified
      if cache_data.get('store', 'single') == 'single':
        bundle[name] = value
      
      # Else, if Queue storage
      elif cache_data.get('store', None) == 'queue':
        # Ensure we have our list
        if name not in bundle: bundle[name] = []
        
        # Append the item
        if not set_all_data:
          bundle[name].append(value)

        # Else, set all the data at once
        else:
          bundle[name] = value

        # Test for max and crop
        if cache_data.get('max', DEFAULT_MAX_QUEUE_SIZE) >= len(bundle[name]):
          # Slice to crop queue, we always chop from the 0 side because we append new items
          bundle[name] = bundle[name][-DEFAULT_MAX_QUEUE_SIZE:]
      
      # Else, unknown data type
      else:
        LOG.error(f'''Unknown data type for caching: {bundle_name}   Key: {name}  Cache Data: {cache_data}''')

      # LOG.debug(f'Set Bundle Key Data: {bundle_name}   Key: {name}  Path: {path}')

      # Store the data into the cache
      local_cache.Set(path, bundle[name])

