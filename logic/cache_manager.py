"""
Cache Manager: This is the generic place to store all data.

There will be locking once you are into a bucket, so we have locks, but can also work faster than globally locking all changes.

This can be backed with DBs or other persistent storage (file system), or run just in memory.  The Bundle specifies how to store the cache values.
"""

import threading

from logic.log import LOG


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
  

  def GetBundleSilo(self, name):
    """Returns the Bundle dict"""
    with self.lock_bundles_all:
      # Ensure we have a dictionary to store the Bundle data, and a lock for each
      if name not in self.bundles:
        self.bundles[name] = {}
        self.lock_bundles_each[name] = threading.Lock()
      
      return self.bundles[name]


  def GetBundleKeyData(self, bundle_name, name, default=None):
    """Returns the Bundle dict"""
    bundle = self.GetBundleSilo(bundle_name)

    with self.lock_bundles_each[bundle_name]:
      return bundle.get(name, default)


  def SetBundleKeyData(self, bundle_name, name, value):
    """Set the value of the bundle cache"""
    bundle = self.GetBundleSilo(bundle_name)

    with self.lock_bundles_each[bundle_name]:
      bundle[name] = value

