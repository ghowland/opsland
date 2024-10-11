"""
Render the Webserver Requests: Keep rendering and serving logic separated for readability
"""

import json

from fastapi import Response
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from logic.log import LOG

from logic import utility
from logic import local_cache
from logic import webserver
from logic import generic_widget


def PageMissing(request, config):
  rendered_html = '404: The page you were looking for doesnt exist'
  return Response(status_code=404, content=rendered_html)


def GetLoginSessionFromRequest(config, request):
  """"Returns the user session or None, based on the session_id from the cookie `opsland_session_id`"""
  session_id = request.cookies['opsland_session_id']

  path = config.data['cache_path_format']['login_sessions']
  sessions = local_cache.GetData(path)
  if sessions == None:
    return None

  # Find the matching session and return it
  for (_, session) in sessions.items():
    # LOG.info(f'''Pre-Comparing sessions: {session}''')
    # LOG.info(f'''Comparing sessions: {session['session_id']} == {session_id}''')
    if session['session_id'] == session_id:
      session['authed'] = True
      return session
  
  return None


def EnhancePagePayload(config, path_data, payload, request):
  # Duplicate to protect top level object
  payload = dict(payload)

  # Defaults to add
  payload['auth_user'] = {'name': 'Guest', 'email': 'unknown@who.you', 'authed': False}

  # App unique overrides to the defaults
  if 'opsland_session_id' in request.cookies:
    session = GetLoginSessionFromRequest(config, request)
    if session:
      payload['auth_user'] = session
  
  # # Add the CPU Status
  # payload['cpu_status'] = f'''<span class="text-teal-600">CPU: {config.server_info.get('cpu_used', -1):.1f}%</span> Status: {thread_manager.CPU_INFO.current_info}'''

  page_name = path_data.get('page', 'Unknown Page')

  payload['breadcrumbs'] = generic_widget.DataForBreadcrumbs(page_name, path_data.get('breadcrumbs', []))

  payload['page_nav'] = config.data['nav']
  
  # Start trying to get the `page_group`, if it doesnt exist, get the page.  This is used to set the Nav Bar highlight so you know what section you are in
  payload['page'] = path_data.get('page_group', path_data.get('page', 'Unknown Page'))

  return payload


def ProcessPayloadData(config, path_data, payload_in):
  payload = dict(payload_in)


  # Perform data processing
  if 'data' in path_data:
    # Process Table: Dict of Dicts
    if 'table_dict' in path_data['data']:
      # Ensure we have a tables dict to store all our tables
      if 'tables' not in payload: payload['tables'] = {}

      for out_table_key, table_info in path_data['data']['table_dict'].items():
        LOG.info(f'Processing table: Dict: {out_table_key}   Data: {table_info}')

        if table_info['key'] not in payload:
          LOG.error(f'''Missing Data Table key: {table_info['key']}''')
          continue

        # Get the table_data from our payload
        table_data = payload[table_info['key']]
        table_element = table_info.get('element', utility.GetRandomString())
        primary_field_name = table_info['name']

        payload['tables'][out_table_key] = generic_widget.DataForTableDictOfDicts(table_data, table_element, primary_field_name, table_info['fields'], table_info['link'])

    # Process Table :List of Dicts
    if 'table_list' in path_data['data']:
      # Ensure we have a tables dict to store all our tables
      if 'tables' not in payload: payload['tables'] = {}

      for out_table_key, table_info in path_data['data']['table_list'].items():
        LOG.info(f'Processing table: List: {out_table_key}   Data: {table_info}')

        if table_info['key'] not in payload:
          LOG.error(f'''Missing Data Table key: {table_info['key']}''')
          continue

        # Get the table_data from our payload
        table_data = payload[table_info['key']]
        table_element = table_info.get('element', utility.GetRandomString())
        primary_field_name = table_info['name']

        payload['tables'][out_table_key] = generic_widget.DataForTableListOfDicts(table_data, table_element, primary_field_name, table_info['link_field'], table_info['fields'], table_info['link'])

  return payload


def RenderPathData(request, config, path_data):
  """Render the Path Data"""
  # Execute the command
  if path_data.get('command', None):
    (status, output, error) = utility.ExecuteCommand(path_data['command'])

  # Else, we dont have a command, we assume everything is empty and can still template and render
  else:
    (status, output, error) = (0, '{}', '{}')

  # If we have a template, then run it through Jinja
  if 'template' in path_data:
    # template = f'''{config.dir_path}/{path_data['template']}'''
    template = path_data['template']

    LOG.debug(f'Output before Payload: {output}')

    payload = json.loads(output)

    # LOG.debug(f'Base Payload: {payload}')

    payload = ProcessPayloadData(config, path_data, payload)

    LOG.debug(f'After Processing Payload: {payload}')

    payload = EnhancePagePayload(config, path_data, payload, request)

    return webserver.TEMPLATES.TemplateResponse(name=template, context=payload, request=request)

  # Else, just return the output  
  else:
    return Response(status_code=200, content=output)

