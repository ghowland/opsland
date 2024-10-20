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
from logic import execute_command


def PageMissing(request, bundle, config):
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


def EnhancePagePayload(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data):
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

  payload['page_nav'] = bundle['nav']

  # Start trying to get the `page_group`, if it doesnt exist, get the page.  This is used to set the Nav Bar highlight so you know what section you are in
  payload['page'] = path_data.get('page_group', path_data.get('page', 'Unknown Page'))

  return payload


def ProcessPayloadData(config, bundle_name, bundle, path_data, payload_in, request, request_headers, request_data):
  payload = dict(payload_in)

  # Ensure we have a tables dict to store all our tables
  if 'table' not in payload: payload['table'] = {}

  # Ensure we have a graphs dict to store all our graphs
  if 'graph' not in payload: payload['graph'] = {}

  # Perform data processing
  if 'data' in path_data:
    # Process Table: Dict of Dicts
    if 'table_dict' in path_data['data']:
      for (out_table_key, table_info) in path_data['data']['table_dict'].items():
        # LOG.info(f'Processing table: Dict: {out_table_key}   Data: {table_info}')

        if table_info['cache'] not in payload:
          LOG.error(f'''Missing Data Table key: Cache: {table_info['cache']}  Key: {table_info['key']}''')#   Payload: {payload}''')
          continue

        # Get the table_data from our payload
        table_data = utility.GetDataByDictKeyList(payload[table_info['cache']], table_info['key'])
        if table_data == None:
          LOG.error(f'''Missing Data Table key: Key Lookup: {table_info['cache']}  Key: {table_info['key']}''')#   Payload: {payload}''')
          continue

        table_element = table_info.get('element', utility.GetRandomString())
        primary_field_name = table_info['name']

        no_max_height = table_info.get('no_max_height', False)

        generic_data = generic_widget.DataForTableDictOfDicts(table_data, table_element, primary_field_name, table_info['fields'], table_info['link'])
        template_result = webserver.TEMPLATES.TemplateResponse(name='includes/generic/generic_table_dict_of_dict.html.j2', 
                                                               context={'generic_table': generic_data, 'no_max_height': no_max_height}, 
                                                               request=request)
        # LOG.debug(f'Table: Dict of Dicts: {generic_data}')
        payload['table'][out_table_key] = template_result.body.decode()

    # Process Table: List of Dicts
    if 'table_list' in path_data['data']:
      for (out_table_key, table_info) in path_data['data']['table_list'].items():
        # LOG.info(f'Processing table: {out_table_key}   Data: {table_info}')

        # Skip and report problems to be solved
        if table_info['cache'] not in payload:
          LOG.error(f'''Missing Data Table cache: Cache: {table_info['cache']}''')#  Payload: {payload}''')
          continue

        # Get the table_data from our payload
        table_data = utility.GetDataByDictKeyList(payload[table_info['cache']], table_info['key'])
        if table_data == None:
          LOG.error(f'''Missing Data Table key: Key Lookup: {table_info['cache']}  Key: {table_info['key']}''')#   Payload: {payload}''')
          continue

        table_element = table_info.get('element', utility.GetRandomString())
        primary_field_name = table_info['name']

        no_max_height = table_info.get('no_max_height', False)

        generic_data = generic_widget.DataForTableListOfDicts(table_data, table_element, primary_field_name, table_info['link_field'], table_info['fields'], table_info['link'])
        # LOG.debug(f'Table: List of Dicts: {generic_data}')
        template_result = webserver.TEMPLATES.TemplateResponse(name='includes/generic/generic_table_list_of_dict.html.j2', 
                                                               context={'generic_table': generic_data, 'no_max_height': no_max_height}, 
                                                               request=request)
        payload['table'][out_table_key] = template_result.body.decode()

    # Process Graph (ex: line, scatter, bar)
    if 'graph' in path_data['data']:
      for (out_graph_key, graph_info) in path_data['data']['graph'].items():
        LOG.info(f'Processing graph: {out_graph_key}   Data: {graph_info}')

        cache_label = utility.GetDictKeyByValue(path_data['cache'], graph_info['cache'])

        # Get our cached value, which should be a timeseries (list of floats)
        graph_cache = config.cache.Get(bundle_name, cache_label)

        if not graph_cache:
          LOG.error(f'''Missing Data Graph key: Cache: {graph_info['cache']}  Result: {graph_cache}  Bundle: {config.cache.GetBundleSilo(bundle_name)}''')
          continue

        generic_data = generic_widget.DataForGraph(graph_info['label'], graph_info['element'], graph_cache)
        # LOG.debug(f'Graph: {generic_data}')
        template_result = webserver.TEMPLATES.TemplateResponse(name='includes/generic/generic_graph.html.j2', 
                                                               context={'generic_graph': generic_data}, 
                                                               request=request)
        payload['graph'][out_graph_key] = template_result.body.decode()

  return payload


def ExecuteStoredCommand(config, bundle_name, execute_name, update_data):
  """Execute a command from the Bundle Spec"""
  parts = execute_name.split('.')

  execute_data = config.data[bundle_name]['execute'][parts[1]][parts[2]]

  LOG.info(f'Exec Stored Command: {execute_name}   Data: {execute_data}')

  # Execute the command
  result = execute_command.ExecuteCommand(config, execute_data, bundle_name, execute_name, update_data=update_data)

  LOG.info(f'Exec Stored Command: {execute_name}   Result: {result}')

  return result


def RenderPathData(request, config, bundle_name, bundle, path_data, request_headers=None, request_data=None):
  """Render the Path Data"""
  # Our starting payload
  payload = {'request': {'data': {}, 'header': {}}}

  # If we have request args, assign them into the payload
  if request_data: payload['request']['data'] = request_data
  # if request_headers: payload['request']['header'] = request_headers

  # Put any cache into our payload
  for (cache_key, payload_key) in path_data.get('cache', {}).items():
    # Format the cache key with the data
    cache_key = utility.FormatTextFromDictKeys(cache_key, request_data)
    # LOG.debug(f'Get from cache_key: {cache_key}')

    payload[payload_key] = config.cache.Get(bundle_name, cache_key)

    # If this doesnt exist, try to get it directly
    if payload[payload_key] == None:
      LOG.error(f'Couldnt find cache key: Bundle: {bundle_name}  Key: {cache_key}')


  # Check if we want to execute a command directly (API)
  if 'execute' in path_data:
    exec_result = ExecuteStoredCommand(config, bundle_name, path_data['execute'], payload)
    if exec_result:
      payload[path_data['execute']] = exec_result
      LOG.info(f'''Execute Stored Command: {path_data['execute']}  Result: {exec_result}''')


  # If we have a template, then run it through Jinja
  if 'template' in path_data:
    template = path_data['template']

    payload = ProcessPayloadData(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data)

    payload = EnhancePagePayload(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data)

    return webserver.TEMPLATES.TemplateResponse(name=template, context=payload, request=request)

  # Else, just return the output  
  else:
    return Response(status_code=200, content=json.dumps(payload))
  

