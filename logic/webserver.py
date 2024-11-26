"""
Webserver using FastAPI

This module starts and stops the webserver, and so it also invokes ShutdownThreads().
"""


# FastAPI
from typing import Union

import uvicorn
import os, signal

# We import these here, but all the child modules can use them through their `parent` reference
from fastapi import FastAPI, Request, Response, Depends, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import RedirectResponse

import shutil
import secrets

from pydantic import BaseModel

# Jinja direct
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2_fragments import render_block

# OpsLand
from logic.log import LOG
from logic import utility_jinja

# This is where we render the pages
from logic import webserver_render


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

TEMPLATES = Jinja2Templates(directory="web/template", context_processors=None, env=ENVIRONMENT)

# Add custom functions and filters to our Jinja
utility_jinja.AddJinjaUtilities(TEMPLATES)

# Create the FastAPI server here, so we can add routes using decorators
APP = FastAPI()
APP.mount("/static", StaticFiles(directory="web/static"), name="static")

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


def GetBundlePathData(method, path):
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

    http_data_methods = bundle['http']

    if method not in http_data_methods:
      continue
    
    http_data = http_data_methods[method]

    if test_path not in http_data:
      continue
    
    return (bundle_path, bundle, http_data[test_path])

  # Couldnt find a Bundle for a page
  return (None, None, None)


# OpsLand Cache Data printed out for manual inspection
@APP.get("/opsland/data", response_class=HTMLResponse)
async def Web_GET(request: Request):
  """Returns all the data for the Bundles"""

  data = {'bundles': CONFIG.cache.bundles}

  return TEMPLATES.TemplateResponse(name='pages/opsland_data.html.j2', context=data, request=request)


# UPLOAD: Multiple Files
@APP.post("/upload_multi")
async def Upload_CreateUploadFileMulti(files: list[UploadFile]):
  # with open("destination.png", "wb") as buffer:
  #   shutil.copyfileobj(file.file, buffer)
  return {"filenames": [file.filename for file in files]}


# UPLOAD: Single File
@APP.post("/upload_single")
async def Upload_CreateUploadFile(file: UploadFile = File(...)):
   with open("destination.png", "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)
   return {"filename": file.filename}



# -- Handle Every HTTP Method and all paths with per-method handler --
#       We route internally after this, and dont use FastAPI/Starlette routing, because they are code based and we want data based

# GET
@APP.get("/{full_path:path}", response_class=HTMLResponse)
async def Web_GET(request: Request, full_path: str):
  """Matches all paths for Method GET, and then we route ourselves"""
  (bundle_name, bundle, path_data) = GetBundlePathData('get', full_path)
  if path_data == None: return webserver_render.PageMissing(request, bundle, CONFIG)

  data = dict(request.query_params._dict)
  headers = dict(request.headers)

  LOG.debug(f'GET: {full_path}  Args: {data}')#  Headers: {headers}')

  return webserver_render.RenderPathData(request, CONFIG, full_path, bundle_name, bundle, path_data, request_headers=headers, request_data=data)


# POST
@APP.post("/{full_path:path}", response_class=HTMLResponse)
async def Web_POST(request: Request, full_path: str):
  """Matches all paths for Method POST, and then we route ourselves"""
  request_data = dict(await request.form())
  request_headers = dict(request.headers)

  (bundle_name, bundle, path_data) = GetBundlePathData('post', full_path)
  if path_data == None: return Response(status_code=404, content={'error': 'URI not found'})

  # LOG.debug(f'POST: {full_path}  Data: {request_data}')#  Headers: {request_headers}')

  return webserver_render.RenderPathData(request, CONFIG, full_path, bundle_name, bundle, path_data, request_data=request_data, request_headers=request_headers)


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
