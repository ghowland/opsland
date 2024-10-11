#!/usr/bin/python3.12

"""
OpsLand: Full web, cache, threaded job execution using CLI programs to separate logic and server.

Requirements:
  pip3.12 install -r requirements.txt
"""


import argparse
import signal
import sys

from logic import cache_manager
from logic import status_manager
from logic import problem_manager
from logic import test_manager

from logic import utility

from logic import log
from logic.log import LOG

from logic import webserver
from logic import thread_manager


# Default listening port
DEFAULT_PORT = 4040


def SignalHandler_SIGINT(sig, frame):
  """We ignore this, but FastAPI's Uvicorn HTTP server will process it to quit quickly."""
  pass


def Main(config):
  if config.debug:
    log.SetLogLevel(log.logging.DEBUG)
    LOG.debug('Log level: Debug')

  # Capture the path, so we know the directory
  config.exec_path = __file__

  # Load our configuration data, or fail
  config.data = utility.LoadYaml(config.data_path)

  # In charge of storing all our data and making it available.  CLI program results are ephemeral, and this makes them persist
  config.cache = cache_manager.CacheManager(config)

  # What is going on with our server?  Information about the status of things can be kept here
  config.status = status_manager.StatusManager(config)

  # Similar to Status, but a different domain.  We track things that are not going well here, so they can be isolated and highlighted.  Special cache data
  config.problems = problem_manager.ProblemManager(config)

  # If we want to perform a test, then run that and exit.  We dont want to run the server, just a test
  if config.test:
    test_manager.ExecuteTest(config)
    sys.exit(0)
  
  # Start all our background threads.  This is where all the non-HTTP serving work gets done
  thread_manager.StartThreads(config)

  # Ignore SIGINT
  signal.signal(signal.SIGINT, SignalHandler_SIGINT)  #test, moved beneath FastAPI from before

  # Start FastAPI
  webserver.Start(thread_manager, config)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    prog='OpsLand',
    description='A CLI-extensible web, cache and threaded job server.',
    epilog='Do all the hard things easy.')

  parser.add_argument('-d', '--debug', default=False, action='store_true', help='Debug logging')
  parser.add_argument('-p', '--port', default=DEFAULT_PORT, type=int, help='Listening port')

  # Testing
  parser.add_argument('--test-list', default=None, type=str, help='List the tests available')
  parser.add_argument('-T', '--test', default=None, type=str, help='Execute one of the available tests')
  parser.add_argument('-D', '--test-data', default=None, type=str, help='Test data.  Whatever is required to help the test, paths, commands, etc')

  parser.add_argument('data_path', help='Configuration path')
  args = parser.parse_args()
  Main(args)

