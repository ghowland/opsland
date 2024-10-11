"""
Problem Manager: A cache system specifically for problems we have seen.  This allows our code to report and surface problems to users, that might be hidden otherwise.

Example: Say you have 100 different CLI jobs that are running against different DBs.  2 of them may be failing, and you can put that data here to surface the problem without having to write 
    all the structure to have a full application support to show problems.  In this way, with hundreds of different things going on there is a single location to see what isn't working.
"""


from logic.log import LOG


# Different expire times
EXPIRE_MINUTE = 60
EXPIRE_DAY = 86400
EXPIRE_SHORT = 5 * EXPIRE_MINUTE
EXPIRE_LONG = 120 * EXPIRE_MINUTE
EXPIRE_NEVER = None


class ProblemManager():
  """Track and clear problems, so we can naively add them or resolve them or let them expire"""

  def __init__(self, config):
    self.config = config
    self.problems = {}

    # List of dicts about things we did recently {'timestamp':0, 'info':'What happened'}
    self.log = []
  

  def Load(self):
    """Load the problem state"""


  def Save(self):
    """Save the problem state"""


  def AddProblem(self, problem_key, info, expires=EXPIRE_NEVER):
    """Add a problem.  By default it will never expire, and has to be resolved."""
    self.problems[problem_key] = info

    LOG.info(f'Add Problem: {problem_key}  Info: {info}  Expires: {expires}')

    self.Save()
  

  def ResolveProblem(self, problem_key):
    """This problem has been resolved."""

    if problem_key in self.problems:
      LOG.info(f'Reslve Problem: {problem_key}')
      del self.problems[problem_key]

    self.Save()

