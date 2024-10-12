"""
Thread Base: ThreadBase is meant to be used as a parent class to implement different threaded objects.
"""


import threading
import traceback
import time

from logic.log import LOG


# Seconds to sleep at a time.  This way we are fairly responsive to shutdown requests
SLEEP_STEP_DURATION = 0.5


class ThreadBase(threading.Thread):
  """Task Manager Thread.  Get given tasks, and execute them serially.  Meant to be overriden on 1 function: ExecuteTask()"""

  def __init__(self, name, config, data=None, sleep_duration=2, remove_task=True):
    # Initialize this as a Thread
    threading.Thread.__init__(self)

    self.name = name

    # This is how most task managers will set up their Init() configuration
    self._data = data

    # Save the config
    self._config = config
    self._sleep_duration = sleep_duration
    # By default we remove tasks, making this a normal task add/remove system.  But we can also just add 1 task and never remove it, so it runs on sleep delay
    self._remove_task = remove_task

    # Internals
    self._shutdown = False
    self._tasks = []
    self._lock = threading.Lock()

    # Call the overloaded Init method, so classes dont have to override __init__, even though that is common, it requires more Python knowledge with super, etc
    self.Init()


  def Init(self):
    """TODO: Override this, for your derived class setup.  Use `self._data` to populate configuration information here"""
    LOG.debug('Init base thread needs to be overriden.  You should do this even if you dont need it.  Just leave it empty with docstring.')

  
  def run(self):
    """Once start() is called, this function is executed, which is the thread's
    run function.
    """
    
    # Loop forever, or until we quit, whichever comes first
    while not self._shutdown:
      # Set the time to awake from sleep before we execute, and now the time will always be correct.  If it's too short, we spin loop
      time_to_awake = time.time() + self._sleep_duration

      try:
        if self._tasks:
          current_task = self.GetNextTask()
          self._ExecuteTask(current_task)
        
      # Log and ignore
      except Exception as e:
        exception_output = traceback.format_exc()
        LOG.error('TaskManagerThread: Unhandled exception:\n%s' % exception_output)

      # Give back to the system as we spin loop.  We wait for our duration, but we only sleep for a short period of time
      while time.time() < time_to_awake:
        time.sleep(SLEEP_STEP_DURATION)
        if self._shutdown:
          break
    
    LOG.info(f'{self.name}: Finished: {self.name}')


  def Shutdown(self):
    """Tell this thread to shut down"""
    LOG.info(f'{self.name}: Task Shutdown: {self.name}')
    self._shutdown = True


  def _ExecuteTask(self, task, log=False):
    """This is the shadow ExecuteTask() which calls the overridable"""
    if log: LOG.info(f'{self.name}: Starting task: {task}')

    self.ExecuteTask(task)

    if log: LOG.info(f'{self.name}: Completed task: {task}')

    # Normally, we want to remove tasks when they are done.  But we allow a permanent task so we just do 1 thing forever
    if self._remove_task:
      self.RemoveTask(task)


  def ExecuteTask(self, task):
    """YOU: Override This: Execute this task, in whatever way the inheritor of this base class wants.  This is where the action will be."""
    LOG.info(f'{self.name}: Execute Task: {task}')
  

  def ListTasks(self):
    """Return a copy of our tasks, thread safe with locking"""
    with self._lock:
      # Get the tasks
      current_tasks = list(self._tasks)

    return current_tasks


  def GetNextTask(self):
    """Gets the oldest task in the list, thread safe with locking"""
    with self._lock:
      # Get the first task (oldest).  We verify that we have a task before we call this
      task = self._tasks[0]

      return task


  def AddTask(self, task):
    """Add specified task to tasks, thread safe with locking"""
    with self._lock:
      # Append
      self._tasks.append(task)
      # LOG.debug(f'{self.name}: Added task: {task}')
    

  def RemoveTask(self, task):
    """Remove specified task from tasks, thread safe with locking"""
    with self._lock:
      # Remove
      self._tasks.remove(task)
      # LOG.debug(f'{self.name}: Removed task: {task}')
    

class ExampleThread(ThreadBase):
  """Example override"""

  def Init(self):
    """We dont need to init anything for this thead, but the practice is to have it exist in case we need something everyone knows this is where it goes"""

    # Use `self._data` to populate configuration information here
    pass


  def ExecuteTask(self, task):
    """Example override task.  Everything else is the same, but we just do this one thing differently.  Easy to make new tasks"""
    LOG.error(task)

