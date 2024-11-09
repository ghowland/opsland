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

  # Get the URI from this request, dont include leading slash to match our bundle config
  payload['uri'] = request.url.path[1:]

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

        generic_data = generic_widget.DataForTableDictOfDicts(table_data, table_element, primary_field_name, table_info['fields'], table_info['link'], table_info.get('key_field', None))
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
        # LOG.info(f'Processing graph: {out_graph_key}   Data: {graph_info}')

        # Get the graph data directly from our cache assignment
        graph_cache = payload[graph_info['cache']]

        if not graph_cache:
          LOG.error(f'''Missing Data Graph key: Cache: {graph_info['cache']}''')#  Result: {graph_cache}  Bundle: {config.cache._GetBundleSilo(bundle_name)}''')
          continue

        generic_data = generic_widget.DataForGraph(graph_info['label'], graph_info['element'], graph_cache)
        # LOG.debug(f'Graph: {generic_data}')
        template_result = webserver.TEMPLATES.TemplateResponse(name='includes/generic/generic_graph.html.j2', 
                                                               context={'generic_graph': generic_data}, 
                                                               request=request)
        payload['graph'][out_graph_key] = template_result.body.decode()

  return payload


def ExecuteStoredCommand(config, bundle_name, bundle, execute_name, update_data):
  """Execute a command from the Bundle Spec"""
  parts = execute_name.split('.')

  execute_data = config.data[bundle_name]['execute'][parts[1]][parts[2]]

  # LOG.info(f'Exec Stored Command: {execute_name}   Data: {execute_data}')

  # Execute the command
  result = execute_command.ExecuteCommand(config, execute_data, bundle_name, bundle, execute_name, update_data=update_data)

  # LOG.info(f'Exec Stored Command: {execute_name}   Result: {result}')

  return result


def EnsureBaseDotToUnderscore(payload):
  """Returns a new dict, where any keys in the root of the dict get dots converted to underscores so jinja can access them easily.  Work around."""
  payload = dict(payload)

  for key in list(payload.keys()):
    if '.' in key:
      new_key = key.replace('.', '_')
      
      payload[new_key] = payload[key]

  return payload


def GetAuthSession(request, config, bundle_name, bundle, headers):
  """"""
  session = {}

  if headers.get('cookie', None):
    # LOG.info(f'''Perform auth check: {headers.get('cookie', None)}''')

    cookie_data = utility.ParseCookieData(headers['cookie'])

    # Get the variable strings we use for the username and token.  It could be something non-default, but we default to username/token in our cached data
    var_username = bundle['auth']['cookie'].get('username', 'username')
    var_token = bundle['auth']['cookie'].get('token', 'token')

    # Return early if we dont have this cookie variable
    if cookie_data.get(var_username, None) == None:
      LOG.info(f'Cant auth.  Username not found in cookie data: {var_username}  Cookie: {cookie_data}')
      return session

    format_cache_key = bundle['auth']['cookie']['cache'].replace('{session.username}', cookie_data.get(var_username, None))

    user_auth_data = config.cache.Get(bundle_name, format_cache_key)
    if user_auth_data:
      tokens_match = user_auth_data[var_token] == cookie_data[var_token]
    else:
      tokens_match = False

    # LOG.info(f'''Perform auth check: {cookie_data}  Cache Key: {format_cache_key}  User Auth: {user_auth_data}  Matched: {tokens_match}''')

    # If this is a valid user session, pack the session data
    if tokens_match:
      session['username'] = cookie_data[var_username]

      if bundle['auth']['cookie'].get('session', None):
        for (cache_key, session_data) in bundle['auth']['cookie']['session'].get('cache', {}).items():
          cache_key = cache_key.replace('{session.username}', cookie_data.get(var_username, None))

          # Process each of our items
          for (session_key, data_key_list) in session_data.items():

            data_value = config.cache.Get(bundle_name, cache_key)
            session[session_key] = utility.GetDataByDictKeyList(data_value, data_key_list)

  # if session:
  #   LOG.info(f'User Session: {session}')

  return session


def RenderPathData(request, config, bundle_name, bundle, path_data, request_headers=None, request_data=None):
  """Render the Path Data"""
  # Our starting payload
  payload = {'request': {}, 'header': {}, 'session': {}}

  # Check if this user is authed, if our bundle has auth
  if 'auth' in bundle and 'cookie' in bundle['auth']:
    payload['session'] = GetAuthSession(request, config, bundle_name, bundle, request_headers)

  # If we have request args, assign them into the payload
  if request_data: payload['request'] = request_data
  # if request_headers: payload['header'] = request_headers

  # Put any cache into our payload
  for (cache_key, payload_data) in path_data.get('cache', {}).items():
    # Format the cache key with the data
    cache_key = utility.FormatTextFromDictKeys(cache_key, request_data)
    LOG.debug(f'Get from cache_key: {cache_key}')

    # payload[payload_key] = config.cache.Get(bundle_name, cache_key)

    # Process each of our items
    for (payload_key, data_key_list) in payload_data.items():
      data_value = config.cache.Get(bundle_name, cache_key)
      payload[payload_key] = utility.GetDataByDictKeyList(data_value, data_key_list)

    
      # If this doesnt exist, try to get it directly
      if payload[payload_key] == None:
        LOG.error(f'Couldnt find cache key: Bundle: {bundle_name}  Key: {cache_key}')

  # import pprint
  # pprint.pprint(payload, indent=2)

  # Check if we want to execute a command directly (API)
  if 'execute' in path_data:
    exec_result = ExecuteStoredCommand(config, bundle_name, bundle, path_data['execute'], payload)
    if exec_result:
      payload[path_data['execute']] = exec_result
      # LOG.info(f'''Execute Stored Command: {path_data['execute']}  Result: {exec_result}''')


  # If we have a template, then run it through Jinja
  if 'template' in path_data:
    template = path_data['template']

    payload = ProcessPayloadData(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data)

    payload = EnhancePagePayload(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data)

    payload = EnsureBaseDotToUnderscore(payload)

    return webserver.TEMPLATES.TemplateResponse(name=template, context=payload, request=request)

  # Else, just return the output  
  else:
    return Response(status_code=200, content=json.dumps(payload))
  

