"""
NetBox: Collect and cache VMs and any other data we need
"""

import os
import time

import git

from logic.log import LOG

from logic import thread_base
from logic import local_secret


class GitManager(thread_base.ThreadBase):
  """Will sync a number of Git repos, so we can use them for templating or other data access"""

  def Init(self):
    """Save our _data to vars"""
    # self.git_repos = utility.LoadYaml(self._config.data['git_repos'])
    self.git_repos = {} #TODO(geoff): Figure out this when I get here

    # Keep the timestamps here for when each repo was last synced
    self.last_synced = {}

    # Give ourselves a single task which will never be removed and doesnt matter.  We just run forever like this.
    self.AddTask({})

    LOG.info(f'Git Repo Syncer Thread Started: {list(self.git_repos.keys())}')


  def ExecuteTask(self, task):
    # Test
    # LOG.info('Git Repo Syncer: Start the updates')

    for repo_name, repo_data in self.git_repos.items():
      # LOG.info(f'Git Repo Syncer: {repo_name}: {repo_data}')

      # Track when we last synced this repo, so we know we synced it after a request was made
      self.last_synced[repo_name] = time.time()

      # If this doesnt exist yet, build it
      if not os.path.isdir(repo_data['path']):
        self.CloneRepo(repo_name, repo_data)
      
      # Else, it already exists so just pull it
      else:
        self.PullRepo(repo_name, repo_data)


  def GetLastRepoSyncTime(self, repo_name):
    """Returns the last epoch time this repo was synced, or 0 if not found"""
    return self.last_synced.get(repo_name, 0)


  def CloneRepo(self, repo_name, repo_data):
    """"""
    # LOG.info(f'''Clone Repo: {repo_name}  Path: {repo_data['path']}''')

    problem_key = f'Git Repo Syncer: Clone: {repo_name}'

    try:
      repo_url = repo_data['repo']
      repo_url = repo_url.replace('{username}', repo_data['auth_user'])
      password = local_secret.Get(repo_data['token_path'])
      repo_url = repo_url.replace('{password}', password)

      repo = git.Repo.clone_from(repo_url, repo_data['path'])

      # Run code because our data changed
      self.RepoUpdated_Run(repo_name, repo_data)

      # LOG.info(f'''Clone Repo: {repo_name}  Result: {repo}  URL: {repo_url}''')
      self._config.problems.ResolveProblem(problem_key)
    
    except Exception as e:
      LOG.error(f'''Clone Failed: {repo_name}  Failure: {e}  URL: {repo_url}''')
      info = {'info': f'Exception: {e}'}
      self._config.problems.AddProblem(problem_key, info)


  def PullRepo(self, repo_name, repo_data):
    """"""
    # LOG.info(f'''Pull Repo: {repo_name}  Path: {repo_data['path']}''')

    problem_key = f'Git Repo Syncer: Pull: {repo_name}'

    try:
      repo = git.Repo(repo_data['path'])

      previous = repo.head.commit

      repo.remotes.origin.pull()

      # Run code because our data changed
      if previous != repo.head.commit:
        self.RepoUpdated_Run(repo_name, repo_data)

      # LOG.info(f'''Pull Repo: {repo_name}  Result: {repo}''')
      self._config.problems.ResolveProblem(problem_key)
    
    except Exception as e:
      LOG.error(f'''Pull Failed: {repo_name}  Failure: {e}''')
      info = {'info': f'Exception: {e}'}
      self._config.problems.AddProblem(problem_key, info)
  

  def RepoUpdated_Run(self, repo_name, repo_data):
    """We just had a repo change local files, so run code if we got it"""
    # Abort if we dont need to do this
    if 'run_on_update' not in repo_data: return

    # -- Hard coded tests for what to execute, because local files changed --
    # Update our Provision cache
    if repo_data['run_on_update'] == 'cache_provision':
      self._config.provision.UpdateRepoCache()

