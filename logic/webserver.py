"""
Webserver using FastAPI

This module starts and stops the webserver, and so it also invokes ShutdownThreads().
"""


# FastAPI
from typing import Union

import uvicorn
import os, signal

# We import these here, but all the child modules can use them through their `parent` reference
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import RedirectResponse

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


def GetPathData(method, path):
  """Returns a dict with the path_data, or None of not found for this method and path"""
  global CONFIG
  
  http_data_methods = CONFIG.data['http']

  if method not in http_data_methods:
    return None
  
  http_data = http_data_methods[method]

  if path not in http_data:
    return None
  
  return http_data[path]


# -- Handle Every HTTP Method and all paths with per-method handler --
#       We route internally after this, and dont use FastAPI/Starlette routing, because they are code based and we want data based

@APP.get("/{full_path:path}", response_class=HTMLResponse)
async def Web_Overview(request: Request, full_path: str):
  """Matches all paths for Method GET, and then we route ourselves"""
  path_data = GetPathData('get', full_path)
  if path_data == None: return webserver_render.PageMissing(request, CONFIG)

  return webserver_render.RenderPathData(request, CONFIG, path_data)


@APP.post("/{full_path:path}", response_class=HTMLResponse)
async def Web_Overview(request: Request, full_path: str):
  """Matches all paths for Method POST, and then we route ourselves"""
  rendered_html = f'POST: {full_path}'
  return Response(status_code=200, content=rendered_html)


@APP.put("/{full_path:path}", response_class=HTMLResponse)
async def Web_Overview(request: Request, full_path: str):
  """Matches all paths for Method PUT, and then we route ourselves"""
  rendered_html = f'PUT: {full_path}'
  return Response(status_code=200, content=rendered_html)


@APP.patch("/{full_path:path}", response_class=HTMLResponse)
async def Web_Overview(request: Request, full_path: str):
  """Matches all paths for Method PATCH, and then we route ourselves"""
  rendered_html = f'PATCH: {full_path}'
  return Response(status_code=200, content=rendered_html)


@APP.delete("/{full_path:path}", response_class=HTMLResponse)
async def Web_Overview(request: Request, full_path: str):
  """Matches all paths for Method DELETE, and then we route ourselves"""
  rendered_html = f'DELETE: {full_path}'
  return Response(status_code=200, content=rendered_html)

