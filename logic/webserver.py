"""
Webserver using FastAPI

This module starts and stops the webserver, and so it also invokes ShutdownThreads().
"""

import pprint

# FastAPI
from typing import Union

import uvicorn
import os, signal

# We import these here, but all the child modules can use them through their `parent` reference
from fastapi import FastAPI, Request, Response, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import RedirectResponse

import shutil
import secrets
from typing import List

from pydantic import BaseModel

# Jinja direct
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2_fragments import render_block

# OpsLand
from logic.log import LOG
from logic import utility_jinja

# This is where we render the pages
from logic import webserver_render

from logic import utility
from logic import jinja_extension


# Globals to connect to other OpsLand components
THREAD_MANAGER = None
CONFIG = None
SERVER = None


SESSION_GLOBAL = {}
# store app state and code verifier in session
SESSION_GLOBAL['app_state'] = secrets.token_urlsafe(64)
SESSION_GLOBAL['code_verifier'] = secrets.token_urlsafe(64)

# Generate a Nonce value for OIDC
NONCE = secrets.token_urlsafe()

# Create the Jinja2 environment, which we use to template, since we use jinja2_partials which is not included in FastAPI
ENVIRONMENT = Environment(loader=FileSystemLoader("web/template"), 
                          autoescape=select_autoescape(("html", "jinja2", "j2")),
                          extensions=[])

# Jinja template path
TEMPLATES = Jinja2Templates(directory="web/template", context_processors=None, env=ENVIRONMENT)
TEMPLATES.env.globals['from_json'] = jinja_extension.from_json
TEMPLATES.env.globals['content_search_single'] = jinja_extension.content_search_single


# Add custom functions and filters to our Jinja
utility_jinja.AddJinjaUtilities(TEMPLATES)

# Create the FastAPI server here, so we can add routes using decorators
APP = FastAPI()
APP.mount("/static", StaticFiles(directory="web/static"), name="static")
APP.mount("/uploads", StaticFiles(directory="../uploads/"), name="uploads")
APP.mount("/content", StaticFiles(directory="../content/"), name="content")
APP.mount("/derived", StaticFiles(directory="../derived/"), name="derived")

# Number of Async thread works for FastAPI
NUM_WORKERS = 4


def Start(thread_manager, config):
  """Webserver: Called from the opsland.Main(), this brings up the Uvicorn server as the primary process thread and blocks"""
  global THREAD_MANAGER, CONFIG, SERVER
  THREAD_MANAGER = thread_manager
  CONFIG = config

  # Start the server
  config = uvicorn.Config("logic.webserver:APP", host="0.0.0.0", port=CONFIG.port, log_level="info", workers=NUM_WORKERS)
  SERVER = uvicorn.Server(config)
  SERVER.run()

  # Once we get here, the server has shutdown gracefully
  pass

  # Shutdown threads.  This reaches back into the OpsLand system to shut things down, then we terminate
  THREAD_MANAGER.ShutdownThreads(CONFIG)


def Shutdown():
  """Webserver: Shut it all down cleanly.  Ignore if this is not in development mode"""
  # Shutdown threads.  This reaches back into the OpsLand system to shut things down, then we terminate
  THREAD_MANAGER.ShutdownThreads(CONFIG)

  global SERVER
  SERVER.shutdown()

  # Uvicorn needs to die
  os.kill(os.getpid(), signal.SIGTERM)


def GetBundlePathData(method, path, domain=None, domain_path=None):
  """Returns a dict with the path_data, or None of not found for this method and path"""
  global CONFIG

  # LOG.debug(f'Get Bundle Path: {method}  Path: {path}')
  
  for bundle_path, bundle in CONFIG.data.items():
    # Skip this path if it doesnt match the bundle root
    #TODO(geoff): Need to strip off leading "/" for the root, but I'm being naive here to start and just making it an empty string to make the code simpler.  Fix
    # LOG.info(f'''{bundle_path}: Root: {path}  Starts with: "{bundle['root']}"''')
    if not path.startswith(bundle['root']):
      continue
    else:
      # This is the path we test with, which we remove the root mount path
      test_path = path.replace(bundle['root'], '', 1)

    # Look for static Method/URI below
    http_data_methods = bundle['http']

    # Skip because we dont have the method
    if method not in http_data_methods:
      continue
    
    http_data = http_data_methods[method]

    # Skip because we dont have the path, but check if it's a dynamic page first
    if test_path not in http_data:
      # Look to see if this is a dynamic domain page
      for config_domain_name, config_domain_data in bundle['domain_dynamic_config'].items():
        # LOG.info(f'Testing: {config_domain_name} == {domain}')
        if config_domain_name == domain:
          
          # #TODO: Check the domain paths from our cache for this domain, and see if there is a match.  If not, return /404 page info
          all_domains = CONFIG.cache.Get(bundle_path, 'execute.api.site_domain')

          LOG.info(f'Domain matched: {config_domain_name}: Path: {domain_path}')#  Data Domains: {all_domains}')

          # Clone the dict, so we dont change the original
          return_data = dict(config_domain_data)
          return_data['cache'] = dict(return_data['cache'])

          # Replace page key
          if 'execute.api.space_page_data.{current_page}' in return_data['cache']:
            # Change the page name
            # page_key = f'''execute.api.space_page_data.{domain.replace('.', '__')}_{domain_path.replace('/', '__')}'''

            # Make the wonkey Domain/Path key we use to lookup now on First Load, which we also use on API, making them match
            page_cache_key = webserver_render.EnhanceUriWithDomain(test_path, domain, domain_path)

            page_key = f'''execute.api.space_page_data.{page_cache_key}'''

            page_data = CONFIG.cache.Get(bundle_path, page_key)

            LOG.info(f'Found page key: {page_key}')#  Page Data: {pprint.pformat(page_data)}')

            # Sets a dict that maps variable names to a `key_list`, which is a Python data search sequence-walker
            return_data['cache'][page_key] = return_data['cache']['execute.api.space_page_data.{current_page}']
            
            # Delete the old one
            del return_data['cache']['execute.api.space_page_data.{current_page}']

          # LOG.info(f'Domain matched: {config_domain_name}: Path: {domain_path}  Value: {pprint.pformat(return_data)}')

          # We matched, so dont check any more domains
          return (bundle_path, bundle, return_data)
      
      # We didnt find the page, and we dont have dynamic matches, so skip this bundle now
      continue

    # Return the static path
    return (bundle_path, bundle, http_data[test_path])

  # Couldnt find a Bundle for a page
  return (None, None, None)


# OpsLand Cache Data printed out for manual inspection
@APP.get("/opsland/data", response_class=HTMLResponse)
async def Web_GET(request: Request):
  """Returns all the data for the Bundles"""

  data = {'bundles': CONFIG.cache.bundles}

  return TEMPLATES.TemplateResponse(name='pages/opsland_data.html.j2', context=data, request=request)


# OpsLand Cache Data printed out for manual inspection
@APP.get("/opsland/pages", response_class=HTMLResponse)
async def Web_GET(request: Request):
  """Returns all the data for the Bundles"""

  data = {'pages':CONFIG.data}

  return TEMPLATES.TemplateResponse(name='pages/opsland_pages.html.j2', context=data, request=request)


# UPLOAD: Multiple Files
@APP.post("/upload_multi")
def Upload_CreateUploadFileMulti(files: List[UploadFile] = File(...)):
  #TODO:HARDCODE: Put into config and use from there
  UPLOAD_PATH = '/mnt/d/_OpsLand/uploads/'

  for file in files:
    try:
      # For now, we will allow only unique names, and we will overwrite on getting them again, so it is just a file system storage
      #TODO: Figure out the best way to manage this, we want controls and audits on the files
      #TODO: Could AI to classify the images, and there should be services for that
      save_path = UPLOAD_PATH + file.filename

      # Dont allow backwards movement
      while '/../' in save_path: save_path = save_path.replace('/../', '')

      with open(save_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    except Exception:
      raise HTTPException(status_code=500, detail='Upload failed')
    finally:
      file.file.close()

  return {"filenames": [file.filename for file in files]}  


# UPLOAD: Single File
@APP.post("/upload_single")
async def Upload_CreateUploadFile(file: UploadFile = File(...)):
  #TODO:HARDCODE: Put into config and use from there
  UPLOAD_PATH = '/mnt/d/_OpsLand/uploads/'

  # For now, we will allow only unique names, and we will overwrite on getting them again, so it is just a file system storage
  #TODO: Figure out the best way to manage this, we want controls and audits on the files
  #TODO: Could AI to classify the images, and there should be services for that
  save_path = UPLOAD_PATH + file.filename

  with open(save_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)

  return {"filename": file.filename}


# UPLOAD: Single File - Derived (Cropped)
@APP.post("/upload_single_derived")
async def Upload_CreateUploadFile(file: UploadFile = File(...)):
  #TODO:HARDCODE: Put into config and use from there
  UPLOAD_PATH = '/mnt/d/_OpsLand/derived/'

  # filename = file.filename
  filename = f'{file.filename}__{utility.GetUUID()}.png'

  # For now, we will allow only unique names, and we will overwrite on getting them again, so it is just a file system storage
  #TODO: Figure out the best way to manage this, we want controls and audits on the files
  #TODO: Could AI to classify the images, and there should be services for that
  # save_path = UPLOAD_PATH + file.filename
  save_path = UPLOAD_PATH + filename

  with open(save_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)

  return {"filename": filename}


# -- Handle Every HTTP Method and all paths with per-method handler --
#       We route internally after this, and dont use FastAPI/Starlette routing, because they are code based and we want data based

def GetDomainAndPath(request):
  """"""
  domain = str(request.base_url)
  domain_path = str(request.url.path)

  # Clean up the domain, strip off any port, and the protocol
  domain = domain.replace('https://', '').replace('http://', '').replace('/', '')
  if ':' in domain: domain = domain.split(':')[0]

  LOG.info(f'Domain: {domain}  Path: {domain_path}')

  return (domain, domain_path)

# GET
@APP.get("/{full_path:path}", response_class=HTMLResponse)
async def Web_GET(request: Request, full_path: str):
  """Matches all paths for Method GET, and then we route ourselves"""
  (domain, domain_path) = GetDomainAndPath(request)

  # Get the bundle match
  (bundle_name, bundle, path_data) = GetBundlePathData('get', full_path, domain, domain_path)
  if path_data == None: return webserver_render.PageMissing(request, bundle, CONFIG)

  data = dict(request.query_params._dict)
  headers = dict(request.headers)

  LOG.debug(f'GET: {full_path}  Args: {data}')#  Headers: {headers}')

  return webserver_render.RenderPathData(request, CONFIG, full_path, bundle_name, bundle, path_data, domain, domain_path, request_headers=headers, request_data=data)


# POST
@APP.post("/{full_path:path}", response_class=HTMLResponse)
async def Web_POST(request: Request, full_path: str):
  """Matches all paths for Method POST, and then we route ourselves"""
  (domain, domain_path) = GetDomainAndPath(request)

  request_data = dict(await request.form())
  request_headers = dict(request.headers)

  (bundle_name, bundle, path_data) = GetBundlePathData('post', full_path)
  if path_data == None: return Response(status_code=404, content={'error': 'URI not found'})

  # LOG.debug(f'POST: {full_path}  Data: {request_data}')#  Headers: {request_headers}')

  return webserver_render.RenderPathData(request, CONFIG, full_path, bundle_name, bundle, path_data, domain, domain_path, request_data=request_data, request_headers=request_headers)


# PUT
@APP.put("/{full_path:path}", response_class=HTMLResponse)
async def Web_PUT(request: Request, full_path: str):
  """Matches all paths for Method PUT, and then we route ourselves"""
  data = dict(await request.form())
  headers = dict(request.headers)

  rendered_html = f'PUT: {full_path}  Data: {data}'#  Headers: {headers}'
  return Response(status_code=200, content=rendered_html)


# PATCH
@APP.patch("/{full_path:path}", response_class=HTMLResponse)
async def Web_PATCH(request: Request, full_path: str):
  """Matches all paths for Method PATCH, and then we route ourselves"""
  data = dict(await request.form())
  headers = dict(request.headers)

  rendered_html = f'PATCH: {full_path}  Data: {data}'#  Headers: {headers}'
  return Response(status_code=200, content=rendered_html)


# DELETE
@APP.delete("/{full_path:path}", response_class=HTMLResponse)
async def Web_DELETE(request: Request, full_path: str):
  """Matches all paths for Method DELETE, and then we route ourselves"""
  data = dict(await request.form())
  headers = dict(request.headers)

  rendered_html = f'DELETE: {full_path}  Data: {data}'#  Headers: {headers}'
  return Response(status_code=200, content=rendered_html)
