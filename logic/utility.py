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
import re

import yaml
import humanize
import random
import string

from logic.log import LOG

from logic import local_cache

# from logic import thread_manager


class MissingCachePath(Exception):
  """We are missing the class path"""


def ExecuteCommand(execute_script, input='', debug=False, set_cwd=None):
  """Run a command and return tuple: status (int), output (string), error (string).  `set_cwd` will set the CWD if not None"""
  if debug: LOG.debug(f'Execute Command: {execute_script}')

  # Execute the script
  args = shlex.split(execute_script)
  pipe = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=set_cwd)
  output, error = pipe.communicate(input)
  status = pipe.returncode

  return (status, output, error)


def GetPathModifiedTime(path):
  """Gets the mtime for a path, or None if the file doesnt exist"""
  if os.path.isfile(path):
    stat = os.stat(path)
    return stat.st_mtime
  else:
    return None


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


def SaveJson(path_raw, data, create_dirs=True):
  """Save YAML data to a path"""
  path = os.path.expanduser(path_raw)

  if create_dirs:
    EnsureDirectoryExists(path)

  with open(path, 'w') as stream:
    json.dump(data, stream)


def EnsureDirectoryExists(path):
  """Gets the directory of this path, and ensures it exists"""
  dir_name = os.path.dirname(path)

  if not os.path.exists(dir_name):
    LOG.info(f'Created directory: {dir_name}')
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


def GlobReverse(glob, text):
  """Returns the data from a glob as text"""
  glob = os.path.expanduser(glob)
  glob_parts = glob.split('*')

  for part in glob_parts:
    text = text.replace(part, '')
  
  return text


def GetDataByDictKeyList(source_data, key_list=None, missing_value=None):
  """Can take a few different options to get the data.

  If `key_list`==None, then the entire `source_data` is returned.
  If `key_list` is a string, then it will return the index of that string in the `source_data`.
  If `key_list` is list, then each field will be used to navigate deeper.  Can be string or int for arrays, can single slice.
  """
  # LOG.debug(f'Get Data by Dict Key List: {key_list}')

  if key_list == None or not key_list:
    return source_data
  
  if type(key_list) == str:
    return source_data[key_list]
  
  if type(key_list) in (list, tuple, dict):
    # try:
      cur_data = source_data
      for key in key_list:
        # LOG.info(f'Cur Key: {key}  Data: {cur_data}')
        if cur_data:
          cur_data = cur_data[key]
        else:
          LOG.error(f'Failed to traverse key list: {key_list} in source_data: {source_data}  Missing on key: {key}')
          return missing_value
      
      return cur_data
    
    # except Exception as e:
    #   LOG.error(f'Failed to traverse key list: {key_list} in source_data: {source_data}  Failure: {e}')
    #   return missing_value
  
  else:
    LOG.error(f'Couldnt find key_list: {key_list} in source_data: {source_data}')
    return missing_value


def GetDictKeyByValue(data, value):
  """Returns the first key that matchies this value.  Uniqueness and order is not guaranteed"""
  for key, key_value in data.items():
    if value == key_value:
      return key
  
  return None


def FormatTextFromDictKeys(text, data):
  """Replace text from a dictionary using {name} formatting"""
  for (key, value) in data.items():
    if f'{{{key}}}' in text:
      # Must enforce replace gets a string value
      text = text.replace(f'{{{key}}}', str(value))
  
  return text


def FormatTextFromDictDeep(text, data):
  """Replace text from a dictionary using {key.name} formatting"""
  deep_replaces = re.findall('{(.*?)}', text)

  # LOG.info(f'Format deep: {data}')

  for deep_replace in deep_replaces:
    try:
      parts = deep_replace.split('.')

      cur_value = data
      parts_remain = parts
      while parts_remain:
        # LOG.info(f'Parts Remain: {parts_remain}  Cur Value: {cur_value}')
        try:
          index = int(parts_remain[0])
          cur_value = cur_value[index]
        except ValueError as e:
          cur_value = cur_value[parts_remain[0]]
        
        # Drop the first element
        parts_remain = parts_remain[1:]
      
      # Replace the text with the value we navigated to
      text = text.replace(f'{{{deep_replace}}}', cur_value)
    except Exception as e:
      LOG.debug(f'Couldnt format text deep: Key: {deep_replace}   Error: {e}')
  
  return text


def ParseCookieData(cookie_text):
  """Takes `cookie_text` and parses it.  ex: 'username=george; token=b0fb805977ee4f2084e5294cbca5160a'"""
  items = cookie_text.split('; ')

  data = {}

  for item in items:
    (key, value) = item.split('=')
    data[key] = value
  
  return data


def RemoveFilePath(path):
  """Deletes the file at `path`.  Wrapping Python code for safety and repeatability.  This needs to be consistent and understood, since its only used in important cases.
  
  Returns: (bool, str) as (success, reason):  `success`: True if it removed the file, and False if it didnt.  `reason`: Only important if it didnt succeed, on success `reason`=''
  """
  if not os.path.exists(path): return (False, f'Path doesnt exist: {path}')
  if not os.path.isfile(path): return (False, f'Path is not a file: {path}  Is Dir: {os.path.isdir(path)}  Is Link: {os.path.islink(path)}  Is Mount: {os.path.ismount}')

  # Remove the path
  try:
    os.unlink(path)
  except Exception as e:
    if os.path.exists(path):
      # The path still exists, so the unlink failed
      return (False, f'Remove File Path: Failed during unlink, file still exists: {e}')
    else:
      # The file was removed, but Python reports a problem, so pass it along
      return (True, f'Remove File Path: Failed during unlink, file still exists: {e}')
  
  # Successful
  return (True, '')


def GlobToRegex(pat: str) -> str:
    """Translate a shell PATTERN to a regular expression.

    Derived from `fnmatch.translate()` of Python version 3.8.13
    SOURCE: https://github.com/python/cpython/blob/v3.8.13/Lib/fnmatch.py#L74-L128
    """

    i, n = 0, len(pat)
    res = ''
    while i < n:
        c = pat[i]
        i = i+1
        if c == '*':
            # -------- CHANGE START --------
            # prevent '*' matching directory boundaries, but allow '**' to match them
            j = i
            if j < n and pat[j] == '*':
                res = res + '.*'
                i = j+1
            else:
                res = res + '[^/]*'
            # -------- CHANGE END ----------
        elif c == '?':
            # -------- CHANGE START --------
            # prevent '?' matching directory boundaries
            res = res + '[^/]'
            # -------- CHANGE END ----------
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j+1
            if j < n and pat[j] == ']':
                j = j+1
            while j < n and pat[j] != ']':
                j = j+1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j]
                if '--' not in stuff:
                    stuff = stuff.replace('\\', r'\\')
                else:
                    chunks = []
                    k = i+2 if pat[i] == '!' else i+1
                    while True:
                        k = pat.find('-', k, j)
                        if k < 0:
                            break
                        chunks.append(pat[i:k])
                        i = k+1
                        k = k+3
                    chunks.append(pat[i:j])
                    # Escape backslashes and hyphens for set difference (--).
                    # Hyphens that create ranges shouldn't be escaped.
                    stuff = '-'.join(s.replace('\\', r'\\').replace('-', r'\-')
                                     for s in chunks)
                # Escape set operations (&&, ~~ and ||).
                stuff = re.sub(r'([&~|])', r'\\\1', stuff)
                i = j+1
                if stuff[0] == '!':
                    # -------- CHANGE START --------
                    # ensure sequence negations don't match directory boundaries
                    stuff = '^/' + stuff[1:]
                    # -------- CHANGE END ----------
                elif stuff[0] in ('^', '['):
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    
    return r'(?s:%s)\Z' % res

