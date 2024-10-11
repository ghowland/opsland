"""
Utility helper functions
"""

import shlex
import subprocess
import json
import uuid
import datetime as dt
import os
import time
import glob

import yaml
import humanize
import random
import string

from logic.log import LOG

from logic import local_cache

# from logic import thread_manager


class MissingCachePath(Exception):
  """We are missing the class path"""


def ExecuteCommand(execute_script, input='', debug=False):
  """Run a command and return tuple: status (int), output (string), error (string)"""
  if debug: LOG.debug(f'Execute Command: {execute_script}')

  args = shlex.split(execute_script)
  pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  output, error = pipe.communicate(input)
  status = pipe.returncode

  return (status, output, error)


def Glob(glob_path):
  path = os.path.expanduser(glob_path)

  return glob.glob(path)


def LoadYaml(path):
  """Load YAML data from path"""
  path = os.path.expanduser(path)

  with open(path, 'r') as stream:
    data = yaml.safe_load(stream)
    return data


def SaveYaml(path_raw, data, create_dirs=True):
  """Save YAML data to a path"""
  path = os.path.expanduser(path_raw)

  if create_dirs:
    EnsureDirectoryExists(path)

  with open(path, 'w') as stream:
    yaml.dump(data, stream, default_flow_style=False)


def EnsureDirectoryExists(path):
  """Gets the directory of this path, and ensures it exists"""
  dir_name = os.path.basename(path)

  if not os.path.exists(dir_name):
    os.makedirs(dir_name)


def LoadJson(path):
  """Load JSON data from path"""
  path = os.path.expanduser(path)
  
  with open(path, 'r') as stream:
    data = json.load(stream)
    return data


def LoadJsonFromString(text):
  """Load JSON data from string"""
  try:
    data = json.loads(text)
  
    return data
  
  except json.decoder.JSONDecodeError as e:
    LOG.error(f'Failed to load JSON: {e}  Input: \n\n{text}')
    raise e


def LoadText(path):
  """Load JSON data from path"""
  path = os.path.expanduser(path)
  
  with open(path, 'r') as stream:
    data = stream.read()
    return data
  

def SaveText(path_raw, data, create_dirs=True):
  """Save YAML data to a path"""
  path = os.path.expanduser(path_raw)

  if create_dirs:
    EnsureDirectoryExists(path)

  with open(path, 'w') as stream:
    stream.write(data)


def GetUUID():
  """Generate a new UUID.  If return_hex==True, we get a string hex version.  Else, we get the int version"""
  return uuid.uuid4().hex


def IsDataEqual(a, b):
  """Uses JSON to ensure any data type that is serializable can be compared"""
  a_json = json.dumps(a)
  b_json = json.dumps(b)

  # Return if they are equal
  return a_json == b_json


def FormatCachePath(config, task_type, commit_hash):
  """Returns string with the path to the local_cache for a given repo and commit"""
  path = config.data['cache_path_format']['cache_format']
  path = path.replace('{type}', task_type)
  path = path.replace('{commit}', commit_hash)

  return path


def TruncateText(text, size):
  """Truncate with ellipsis"""
  if len(text) > size:
    return text[:size] + '...'
  
  return text[:size]


def ConvertStringDurationToSeconds(text):
  """Returns int in seconds, using the 5s, 10m, 2h Go-lang style durations.  Handles seconds, minutes, hours and day durations"""
  # If we somehow got a raw number, just return it as-is
  try:
    return float(text)
  except ValueError as e:
    pass

  text = text.strip()

  value = int(text[:-1])
  counter = text[-1]

  if counter == 's':
    return value
  elif counter == 'm':
    return value * 60
  elif counter == 'h':
    return value * 60 * 60
  elif counter == 'd':
    return value * 60 * 60 * 24
  else:
    raise Exception(f'Unknown time duration format: {text}')


def IsPastDuration(initial_time, duration, cur_time):
  """From an initial time.time(), uses duration in seconds and returns bool if cur_time is past duration"""
  test_time = initial_time + duration

  if cur_time >= test_time:
    return True
  else:
    return False


def ShortenString(text, max_length):
  """Shorten a string to a maximum length and add ellipsis if needs cropping"""
  if len(text) <= max_length:
    return text
  else:
    return text[:max_length] + '...'


def JoinAndWrapStrings(text_list, separator=', ', wrapper_format="`%s`"):
  """Join the list of strings using the separator, but also wrap them with this format"""
  new_text_list = []
  for text in text_list:
    new_text_list.append(wrapper_format % text)
  
  return separator.join(new_text_list)


def HumanizeTimestamp(timestamp, markup_html=False):
  """Make a timestamp"""
  # Unknown timestamp
  if timestamp == None:
    return 'Unknown'

  since_raw = time.time() - timestamp
  
  since = humanize.naturaltime(dt.datetime.fromtimestamp(timestamp))

  if since_raw > 86400:
    output = dt.datetime.fromtimestamp(timestamp).strftime("%Y/%m/%d %H:%M:%S")
  else:
    output = dt.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

  result = f'{output} ({since})'
  
  return result


def UpdateLoginSessions(config, session_id, data):
  """Update the Login Sessions"""
  
  path = config.data['cache_path_format']['login_sessions']

  sessions = local_cache.GetData(path)
  if sessions == None:
    sessions = {}
  
  sessions[session_id] = data

  local_cache.Set(path, sessions)


def ConvertPathSpecialChars(path):
  """Converts any special characters in a string into text"""
  path = path.replace('*', '_STAR_')
  path = path.replace('?', '_QUEST_')
  path = path.replace('\'', '_QUOT1_')
  path = path.replace('"', '_QUOT2_')
  path = path.replace('[', '_BR1_')
  path = path.replace(']', '_BR2_')
  path = path.replace('{', '_BR3_')
  path = path.replace('}', '_BR4_')
  path = path.replace('<', '_BR5_')
  path = path.replace('>', '_BR6_')
  path = path.replace('(', '_PAREN1_')
  path = path.replace(')', '_PARENT2_')
  path = path.replace('@', '_AT_')
  path = path.replace(':', '_COLON_')
  path = path.replace(';', '_SEMI_')
  path = path.replace(',', '_COMMA_')
  path = path.replace('&', '_AND_')
  path = path.replace('$', '_DOL_')
  path = path.replace('#', '_HASH_')
  path = path.replace('!', '_BANY_')
  path = path.replace('^', '_CAR_')
  path = path.replace('^', '_CAR_')
  path = path.replace('|', '_PIPE_')
  path = path.replace('\\', '_BACK_')
  path = path.replace('/', '_SLASH_')
  path = path.replace('`', '_TICK_')
  path = path.replace('~', '_TILDE_')

  return path


def GetBoolHtml(value, tooltip=None):
  tooltip_str = ''
  tooltip_div = ''
  if tooltip:
    uuid = GetUUID()
    tooltip_str = f'data-tooltip-target="tooltip-{uuid}"'
    tooltip_div = f'''
    <div id="tooltip-{uuid}" role="tooltip" class="absolute z-10 invisible inline-block px-3 py-2 text-sm font-medium text-white transition-opacity duration-300 bg-gray-900 rounded-lg shadow-sm opacity-0 tooltip dark:bg-gray-700">
    {tooltip}
    <div class="tooltip-arrow" data-popper-arrow></div>
    </div>
    '''

  if value:
    return f'''
      <svg {tooltip_str} class="w-6 h-6 text-green-800 dark:text-green" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
          <path fill="currentColor" d="m18.774 8.245-.892-.893a1.5 1.5 0 0 1-.437-1.052V5.036a2.484 2.484 0 0 0-2.48-2.48H13.7a1.5 1.5 0 0 1-1.052-.438l-.893-.892a2.484 2.484 0 0 0-3.51 0l-.893.892a1.5 1.5 0 0 1-1.052.437H5.036a2.484 2.484 0 0 0-2.48 2.481V6.3a1.5 1.5 0 0 1-.438 1.052l-.892.893a2.484 2.484 0 0 0 0 3.51l.892.893a1.5 1.5 0 0 1 .437 1.052v1.264a2.484 2.484 0 0 0 2.481 2.481H6.3a1.5 1.5 0 0 1 1.052.437l.893.892a2.484 2.484 0 0 0 3.51 0l.893-.892a1.5 1.5 0 0 1 1.052-.437h1.264a2.484 2.484 0 0 0 2.481-2.48V13.7a1.5 1.5 0 0 1 .437-1.052l.892-.893a2.484 2.484 0 0 0 0-3.51Z"/>
          <path fill="#fff" d="M8 13a1 1 0 0 1-.707-.293l-2-2a1 1 0 1 1 1.414-1.414l1.42 1.42 5.318-3.545a1 1 0 0 1 1.11 1.664l-6 4A1 1 0 0 1 8 13Z"/>
      </svg>
      {tooltip_div}
      '''
  else:
    return f'''
      <svg {tooltip_str} class="w-6 h-6 text-red-800 dark:text-red" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 22 21">
        <path stroke="currentColor" stroke-linecap="round" stroke-width="2" d="M7.24 7.194a24.16 24.16 0 0 1 3.72-3.062m0 0c3.443-2.277 6.732-2.969 8.24-1.46 2.054 2.053.03 7.407-4.522 11.959-4.552 4.551-9.906 6.576-11.96 4.522C1.223 17.658 1.89 14.412 4.121 11m6.838-6.868c-3.443-2.277-6.732-2.969-8.24-1.46-2.054 2.053-.03 7.407 4.522 11.959m3.718-10.499a24.16 24.16 0 0 1 3.719 3.062M17.798 11c2.23 3.412 2.898 6.658 1.402 8.153-1.502 1.503-4.771.822-8.2-1.433m1-6.808a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/>
      </svg>
      {tooltip_div}
      '''


def GetLinkHtml(url, name=None):
  """Create an HTML URL"""
  if not name:
    name = url

  link = f'''<a href="{url}" class="font-medium text-blue-600 dark:text-blue-500 hover:underline">{name}</a>'''
  
  return link


def GetRandomString(length=10):
  """Returns a randown string of characters, with the length specified"""
  letters = string.ascii_lowercase
  return ''.join(random.choice(letters) for i in range(length))

