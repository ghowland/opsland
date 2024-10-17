"""
Thread Manager
"""


import threading

from logic.threaded import bundle_manager
from logic.threaded import job_manager
from logic.threaded import job_scheduler
from logic.threaded import git_manager


# Keep our Bundles hot loaded
BUNDLE_MANAGER = None

# Job manager.  Execute queued jobs
JOB_MANAGER = None

# Job Scheduler.  Periodically add new jobs to the Job Manager queue
JOB_SCHEDULER = None

# Sync Git Repos that we want to ensure are up to date with our Bundles specification, so we have fresh data
GIT_MANAGER = None


def StartThreads(config):
  """Start all our background threads"""
  # Create lock for synchronizing threads.  Add this into our config we pass around everywhere
  config.lock_all = threading.Lock()

  # Bundle Manager: Hot reload any bundle changes
  global BUNDLE_MANAGER
  BUNDLE_MANAGER = bundle_manager.BundleManager('Bundle Manager', config, {}, sleep_duration=10, remove_task=False)
  BUNDLE_MANAGER.start()

  # Job Manager: Process jobs in the queue
  global JOB_MANAGER
  JOB_MANAGER = job_manager.JobManager('Job Manager', config, {}, sleep_duration=3)
  JOB_MANAGER.start()

  # Job Schedule: Add new jobs to Job Manager queue
  global JOB_SCHEDULER
  JOB_SCHEDULER = job_scheduler.JobScheduler('Job Scheduler', config, {}, sleep_duration=3, remove_task=False)
  JOB_SCHEDULER.start()

  # Git Manager: Sync repos we care about, to keep our scripts and data fresh
  global GIT_MANAGER
  GIT_MANAGER = git_manager.GitManager('Git Manager', config)
  GIT_MANAGER.start()


def ShutdownThreads(config):
  """Shut it all down"""
  BUNDLE_MANAGER.Shutdown()
  JOB_MANAGER.Shutdown()
  JOB_SCHEDULER.Shutdown()
  GIT_MANAGER.Shutdown()

