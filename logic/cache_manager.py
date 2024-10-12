"""
Cache Manager: This is the generic place to store all data.

There will be locking once you are into a bucket, so we have locks, but can also work faster than globally locking all changes.

This can be backed with DBs or other persistent storage (file system), or run just in memory.  The Bundle specifies how to store the cache values.
"""

import threading

from logic.log import LOG

from logic import thread_manager
from logic import utility
from logic import local_cache


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
      path_data = utility.GlobReverse(cache_glob, path)

      LOG.info(f'Path Key: {cache_glob} -> {path} -> {path_data}')


  def GetBundleSilo(self, name):
    """Returns the entire Bundle dict, with all items inside the bundle"""
    with self.lock_bundles_all:
      # Ensure we have a dictionary to store the Bundle data, and a lock for each
      if name not in self.bundles:
        self.bundles[name] = {}
        self.lock_bundles_each[name] = threading.Lock()
      
      return self.bundles[name]


  def GetBundleKeyData(self, bundle_name, name, default=None):
    """Returns a single Bundle dict item"""
    bundle = self.GetBundleSilo(bundle_name)

    LOG.info(f'Get Bundle Key: {bundle_name}  Key: {name}  Bundle: {bundle}')

    with self.lock_bundles_each[bundle_name]:
      return bundle.get(name, default)


  def SetBundleKeyData(self, bundle_name, name, value):
    """Set the value of the bundle cache"""
    bundle = self.GetBundleSilo(bundle_name)

    bundles = thread_manager.BUNDLE_MANAGER.GetBundles()
    bundle_data = bundles[bundle_name]

    with self.lock_bundles_each[bundle_name]:
      bundle[name] = value

      # LOG.info(f'Bundle: {bundle_name}  Data: {bundle_data}')

      path = bundle_data['cache_path'].replace('{key}', name)

      LOG.debug(f'Set Bundle Key Data: {bundle_name}   Key: {name}  Path: {path}')

      local_cache.Set(path, value)

