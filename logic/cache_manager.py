"""
Cache Manager: This is the generic place to store all data.

There will be locking once you are into a bucket, so we have locks, but can also work faster than globally locking all changes.

This can be backed with DBs or other persistent storage (file system), or run just in memory.  The Bundle specifies how to store the cache values.
"""

import threading
import statistics
import re

from logic.log import LOG

from logic import thread_manager
from logic import utility
from logic import local_cache


# Default max queue size
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

    # Load the Cache files
    cache_glob = bundle_data['path']['cache'].replace('{key}', '*')
    paths = utility.Glob(cache_glob)
    for path in paths:
      path_key = utility.GlobReverse(cache_glob, path)
      # LOG.info(f'Loaded Cache Path Key: {cache_glob} -> {path} -> {path_key}')

      cache_value = local_cache.GetData(path)

      self.Set(bundle_name, path_key, cache_value, set_all_data=True, save=True)

    # Load the Summary files
    cache_glob = bundle_data['path']['summary'].replace('{key}', '*')
    paths = utility.Glob(cache_glob)
    for path in paths:
      path_key = utility.GlobReverse(cache_glob, path)
      # LOG.info(f'Summary Path Key: {cache_glob} -> {path} -> {path_key}')

      summary_fields = local_cache.GetData(path)

      # If we got the cache value, and we have this bundle to lock (since we are doing things directly, check)
      if summary_fields and bundle_name in self.lock_bundles_each:
        with self.lock_bundles_each[bundle_name]:
          # Set all the `summary_fields` into this bundle cache data
          self.bundles[bundle_name].update(summary_fields)
    
    # Load the static content
    if 'static' in bundle_data:
      for item_key, item_path in bundle_data['static'].items():
        static_key = f'static.{item_key}'
        cache_value = utility.LoadYaml(item_path)
        LOG.info(f'Static set: {static_key}  Value: {cache_value}')
        self.Set(bundle_name, static_key, cache_value, set_all_data=True, save=True)


  def GetBundleAndCacheInfo(self, bundle_name, name):
    """Returns a tuple of (bundle_info, cache_info)"""
    bundles = thread_manager.BUNDLE_MANAGER.GetBundles()
    bundle_info = bundles[bundle_name]

    (cache_info, base_cache_key) = self.GetCacheInfo(bundle_info, name)

    return (bundle_info, cache_info, base_cache_key)


  def GetCacheInfo(self, bundle_info, cache_key):
    """From the Bundle Info spec: Get the spec for this `cache_key`, because its strictly-named, we can reverse it.
    
    Returns tuple: (dict, str): (cache_info, base_cache_key) or (None, None) if not found
    """
    part_cache_key = cache_key
    
    # Schedule Job keys
    if part_cache_key.startswith('schedule.'):
      part_cache_key = part_cache_key.replace('schedule.', '', 1)

      # Periodic job keys
      if part_cache_key.startswith('period.'):
        part_cache_key = part_cache_key.replace('period.', '', 1)

        if 'schedule' in bundle_info and 'period' in bundle_info['schedule'] and part_cache_key in bundle_info['schedule']['period']:
          return (bundle_info['schedule']['period'][part_cache_key], f'schedule.period.{part_cache_key}')

    # Execute
    elif part_cache_key.startswith('execute.'):
      part_cache_key = part_cache_key.replace('execute.', '', 1)

      # Periodic job keys
      if part_cache_key.startswith('api.'):
        part_cache_key = part_cache_key.replace('api.', '', 1)

        # If we have this entire remaining key, return the Cache Info
        if 'execute' in bundle_info and 'api' in bundle_info['execute'] and part_cache_key in bundle_info['execute']['api']:
          return (bundle_info['execute']['api'][part_cache_key], f'execute.api.{part_cache_key}')

        # Else, we didnt find it
        else:
          # Check if this is a `unique_key` by splitting off the first dotted section and testing it
          prefix_cache_key = part_cache_key.split('.', 1)[0]
          if 'execute' in bundle_info and 'api' in bundle_info['execute'] and prefix_cache_key in bundle_info['execute']['api']:
            return (bundle_info['execute']['api'][prefix_cache_key], f'execute.api.{prefix_cache_key}')

    # Static
    elif part_cache_key.startswith('static.'):
      part_cache_key = part_cache_key.replace('static.', '', 1)
      return (bundle_info['static'][part_cache_key], cache_key)

    return (None, None)


  def SaveBundle(self, bundle_name, cache_key, bundle_info=None, cache_info=None):
    """Save whatever is in the current bundle.  Isolating this makes other logic simpler."""
    bundle = self._GetBundleSilo(bundle_name)

    # If we werent given these, get them
    if not bundle_info or not cache_info:
      (bundle_info, cache_info, _) = self.GetBundleAndCacheInfo(bundle_name, cache_key)

    # If we couldnt get them, fail
    if not bundle_info: 
      LOG.error(f'Couldnt get our Bundle or Cache data for: {bundle_name}  Key: {cache_key}\nBundle Data: {bundle_info}')
      return

    # Get the path, using the base cache key
    path = bundle_info['path']['cache'].replace('{key}', cache_key)

    # LOG.debug(f'Save Bundle: {bundle_name}   Key: {cache_key}  Path: {path}')

    # Store the data into the cache
    local_cache.Set(path, bundle[cache_key])


  def _GetBundleSilo(self, bundle_name):
    """Returns the entire Bundle dict, with all items inside the bundle.  Bundle is created if doesnt exist yet, so always returns real dict"""
    with self.lock_bundles_all:
      # Ensure we have a dictionary to store the Bundle data, and a lock for each
      if bundle_name not in self.bundles:
        self.bundles[bundle_name] = {}
        self.lock_bundles_each[bundle_name] = threading.Lock()
      
      return self.bundles[bundle_name]


  def Get(self, bundle_name, cache_key, default=None):
    # Get the bundle, so we have direct access
    bundle = self._GetBundleSilo(bundle_name)

    # print('------------START----------------')
    # import pprint
    # pprint.pprint(bundle)
    # print('------------STOP----------------')

    """Returns a single Bundle dict item.  If not found, returns `default`.  If `single`==True will only return 1 value, otherwise the raw values"""
    #TODO(geoff): Do I need to lock all?  I think I do because things could be changing, and Im working through indexing.  So I should switch to silo mode, and verify I can write to it
    #   or write a new GetWritableSilo() func so I can write into it without using the global lock, because the get-by-itself is safe
    with self.lock_bundles_each[bundle_name]:
      # If this is not a glob, then return the key or default
      if '*' not in cache_key:
        return bundle.get(cache_key, default)
      
      # Else, this is a glob, so return all the matching records as a dict of dicts
      else:
        data = {}

        key_regex = utility.GlobToRegex(cache_key)
        key_regex_compiled = re.compile(key_regex)
        for (key, value) in bundle.items():
          if key_regex_compiled.match(key):
            data[key] = value

        LOG.info(f'Found glob data: {data}')

        return data


  def Set(self, bundle_name, cache_key, value, set_all_data=False, save=True):
    """Returns a single Bundle dict item.  If not found, returns `default`.  If `single`==True will only return 1 value, otherwise the raw values"""
    # Get the bundle, so we have direct access
    bundle = self._GetBundleSilo(bundle_name)

    (bundle_info, cache_info, base_cache_key) = self.GetBundleAndCacheInfo(bundle_name, cache_key)

    # Fail if we cant get this
    if not bundle_info or not cache_info:
      raise Exception(f'Failed to get Bundle or Cache Info: Bundle: {bundle_info}   Cache: {cache_info}:  Cache Key: {cache_key}')


    # If the cache_data has a `unique_key`
    if 'unique_key' in cache_info and cache_key == base_cache_key:
      unique_key = utility.FormatTextFromDictKeys(cache_info['unique_key'], value)

      if unique_key and '{' not in unique_key:
        # Suffix the unique key to the cache_key
        cache_key = f'''{cache_key}.{unique_key}'''
      else:
        raise Exception(f'''Unique Key didnt format properly, failing: {bundle_name}  Key: {cache_key}  Unique Key: {unique_key}  Cache Info: {cache_info}  Value: {value}''')


    with self.lock_bundles_each[bundle_name]:
      # If this is static data, just set it
      if cache_key.startswith('static.'):
        bundle[cache_key] = value
        
      # If Single value storage.  This is the default if nothing is specified
      elif cache_info.get('store', 'single') == 'single':
        bundle[cache_key] = value
        # LOG.debug(f'Set Cache: {cache_key}')
      
      # Else, if Queue storage
      elif cache_info.get('store', None) == 'queue':
        # Ensure we have our list
        if cache_key not in bundle: bundle[cache_key] = []
        
        # Append the item
        if not set_all_data:
          # LOG.debug(f'Set Cache: Appended to Queue: {cache_key}')
          bundle[cache_key].append(value)

        # Else, set all the data at once
        else:
          # LOG.debug(f'Set Cache: Set All Queue: {cache_key}')
          bundle[cache_key] = value

        # Test for max and crop
        max_queue_size = cache_info.get('max', DEFAULT_MAX_QUEUE_SIZE)

        if max_queue_size < len(bundle[cache_key]):
          # Slice to crop queue, we always chop from the 0 side because we append new items
          bundle[cache_key] = bundle[cache_key][-max_queue_size:]
          # LOG.debug(f'Reduced queue length: {bundle_name}: {name}: {len(bundle[name])}')
        
        else:
          # LOG.debug(f'Queue length: {bundle_name}: {cache_key}: {len(bundle[cache_key])}')
          pass

        # If this key is in our `summary` system
        self.ProcessSummary(bundle_info, bundle_name, bundle, cache_key, bundle[cache_key])
    
      # Else, unknown data type
      else:
        LOG.error(f'''Unknown data type for caching: {bundle_name}   Key: {cache_key}  Cache Data: {cache_info}''')

    # If we want to save this.  Normally we do, but when we are initially loading values, we dont  
    if save:
      self.SaveBundle(bundle_name, cache_key)


  def ProcessSummary(self, bundle_data, bundle_name, bundle, bundle_key, raw_data):
    # If this key is in our `summary` system
    if not bundle_data.get('summary', {}) or not bundle_data['summary'].get(bundle_key, None): return

    summary_data = bundle_data['summary'][bundle_key]

    for (suffix_field, field_list) in summary_data['fields'].items():
      summary_key = f'summary.{bundle_key}.{suffix_field}'

      values = []

      # Walk the fields to get to our data
      for item in raw_data:
        # Start at the root of each item
        cur_data = item

        # Walk the field list to get to our desired data
        for field in field_list:
          cur_data = cur_data[field]

        # Float
        if summary_data.get('type', 'float') == 'float':
          #TODO(g): Handle other cases than Float
          value = float(cur_data)
          values.append(value)
        
        else:
          LOG.error(f'''Summary has unknown type: {summary_data['type']} for {bundle_name} key {bundle_key}''')
    
      # We have all the values, so now we can get our summaries.  `stdev` requires at least 2 data points, so we will just require that for all summaries
      if len(values) > 2:
        summary_update = {}
        summary_update[f'{summary_key}.max'] = max(values)
        summary_update[f'{summary_key}.min'] = min(values)
        summary_update[f'{summary_key}.mean'] = statistics.mean(values)
        summary_update[f'{summary_key}.median'] = statistics.median(values)
        summary_update[f'{summary_key}.stdev'] = statistics.stdev(values)
        summary_update[f'{summary_key}.timeseries'] = values

        # Update the bundle with all our summary data.  Same as setting it directly, but now we can cache the summary data separately for cleanliness
        bundle.update(summary_update)

        # LOG.debug(f'''Summary: {summary_key}  Min: {bundle[f'{summary_key}.min']}  Max: {bundle[f'{summary_key}.max']}  Mean: {bundle[f'{summary_key}.mean']}''')

        summary_path = bundle_data['path']['summary'].replace('{key}', summary_key)
        local_cache.Set(summary_path, summary_update)
        # LOG.debug(f'Summary written: {summary_path}')

