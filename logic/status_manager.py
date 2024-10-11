"""
Status Manager: A caching silo for "What is going on?" with this server.  We allow insights into the operations of this server here.
"""

import threading
import time

from logic.log import LOG


class StatusManager():
  """Holds all our status objects, so we can look at what is going on inside our system"""

  def __init__(self, config):
    # Store our config, everything uses it
    self.config = config

    # These are all the items we have
    self.items = {}

    # If we are making changes to the items, use the lock so we dont crash
    self.items_lock = threading.Lock()
  

  def AddItem(self, key, item):
    """Safely add this item to our list"""
    # timestamp = timestamp
    timestamp = time.time()

    key = str(key)

    with self.items_lock:
      # Ensure the timestamp exists as a dict
      if timestamp not in self.items:
        self.items[timestamp] = {}
      
      # Set the item at the key
      self.items[timestamp][key] = item

      LOG.debug(f'Add Status Item: {timestamp}: {key}: {item}')
  

  def GetCurrentItems(self):
    """Returns a copy of all our items, in reverse order so newest is first."""
    # Make sure we dont go crazy here, keep purging
    self.PurgeOlderThan()

    keys = list(self.items.keys())
    keys.sort()
    keys.reverse()

    items = []
    for key in keys:
      data = {
        'time': key, 
        'data': self.items[key]
        }
      items.append(data)

    return items


  def PurgeOlderThan(self, seconds=1200):
    """Default purge time is 20 minutes, adjust as needed"""
    #TODOD: Move the defalt purge time to the YAML config?  Probably
    cur_time = int(time.time())

    # Loop over all our top level item times, and purge them if they are too old
    for item_time in list(self.items.keys()):
      if item_time + seconds < cur_time:
        del self.items[item_time]



