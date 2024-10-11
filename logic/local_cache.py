#!/usr/bin/env python3

"""
Simple library to cache data, and check if the cache exists.  We use JSON to cache.
"""


import os
import sys
import json
import time
import pprint


def SaveJson(path, data):
    with open(path, 'w') as fp:
        content = json.dumps(data)
        fp.write(content)


def Get(path_raw):
    path = os.path.expanduser(path_raw)

    try:
        with open(path) as fp:
            wrapped_data = json.load(fp)
            return wrapped_data

    except FileNotFoundError as e:
        return None


def Set(path_raw, data):
    """Put the data in this cache, at the path specified.  Will save the time and time cache was cleared"""
    path = os.path.expanduser(path_raw)

    # Ensure the directory exists
    dir_path = os.path.dirname(path)
    if not os.path.isdir(dir_path):
        print(f'Creating cache directory: {dir_path}')
        os.makedirs(dir_path)

    # Wrap our data so it can be tested as cache, and marked as cleared
    wrapped_data = {
        'time': time.time(),
        'cleared': 0,
        'data': data,
    }

    SaveJson(path ,wrapped_data)


def Clear(path_raw, destroy=False):
    """Clear the cache path, we will just delete this file"""
    path = os.path.expanduser(path_raw)

    # If we dont want to destroy it, just set it as cleared and save it again
    if not destroy:
        wrapped_data = Get(path_raw)

        # Only clear if we got it
        if wrapped_data != None:
            wrapped_data['cleared'] = time.time()

            SaveJson(path, wrapped_data)

    # Else, we do want to destroy it, so delete it
    else:
        try:
            os.remove(path)
        except Exception as e:
            pass



def Error(text, status_code=1):
    """We failed, report it and exit non-zero"""
    sys.stderr.write(f'error: {text}\n\n')
    sys.stderr.write(f'usage: {sys.argv[0]} <command> <path>\n\n')
    sys.exit(status_code)


def Main(args=None):
    if not args:
        args = []

    if len(args) < 2:
        Error('Mush have 2 arguments, the command and path')
        sys.exit(1)

    command = args[0]
    path = args[1]

    # Get existing cache
    if command == 'get':
        result = Get(path)

        if result == None:
            Error(f'File not found: {path}')

        if 'time' in result and 'data' in result:
            duration = int(time.time() - result['time'])
            if result['cleared'] == 0:
                print(f'Cached data for {duration} seconds:')
            else:
                cleared = int(time.time() - result['cleared'])
                print(f'Cached data for {duration} seconds, cleared {cleared} seconds ago:')

            pprint.pprint(result['data'])
        else:
            print('Not cache packed JSON, just regular JSON, so no information on duration:')
            pprint.pprint(result)

    # Set the cache
    elif command == 'set':
        # Try to load the data from input
        print('Enter 1 line of JSON data now from STDIN:')
        raw_data = input()
        try:
            data = json.loads(raw_data)
            Set(path, data)
        except json.decoder.JSONDecodeError as e:
            Error(f'Input JSON data is invalid: {e}')

    # Clear the cache (set cleared time)
    elif command == 'clear':
        Clear(path, False)

    # Destroy the cache (delete path)
    elif command == 'destroy':
        Clear(path, True)

    # Error: Unknown command
    else:
        Error(f'Invalid command "{command}", available commands: get, set, clear, destroy')


if __name__ == '__main__':
    Main(sys.argv[1:])

