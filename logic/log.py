"""
Logging to STDERR:  Always go to STDERR to avoid any other content.  

Errors only isnt enough, better stuff all logs on stderr.
"""


import logging
import sys


# Logging singleton
LOG = logging.getLogger('infratool')

# Minimum log level to emit to logs, change with SetLogLevelMinimum()
LOG_LEVEL = logging.INFO

# Logging format
LOG_FORMAT = '%(levelname)s: %(message)s'

# Create these are the global level, on import phase
LOG_HANDLER = logging.StreamHandler(sys.stderr)
LOG_FORMATTER = logging.Formatter(LOG_FORMAT)

# Set these at the import phase
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOG.addHandler(LOG_HANDLER)


def SetLogLevel(level):
  """Set the global minimum log level to emit logs.  This is the one you want to set when changing log levels."""
  global LOG_LEVEL

  # Enforce that level is an integer, or fail
  LOG_LEVEL = int(level)

  # If the LOG was already created, set it.  Otherwise it will set it next time we log
  # if LOG != None:
  LOG.setLevel(LOG_LEVEL)
  LOG_HANDLER.setLevel(LOG_LEVEL)


# -- Start with initial log level --
SetLogLevel(LOG_LEVEL)


# -- Additional functions related to logging --
def LogToSyslogFile(path, message):
  """Appends a log to a file, for syslog to consume"""
  with open(path, 'a') as stream:
    stream.write(message + '\n')

