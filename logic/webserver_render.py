"""
Render the Webserver Requests: Keep rendering and serving logic separated for readability
"""


import json
import pprint

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


def EnhancePagePayload(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data, domain, domain_path):
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
  #TODO:DUPLICATE?  Is this duped from RenderPage() down below?  I think I already set this accurately there, but here I was fixing the [1:].  Remove that one?  Maybe cleaner only here
  payload['uri'] = EnhanceUriWithDomain(request.url.path[1:], domain, domain_path)
  payload['uri_raw'] = request.url.path[1:]

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


def EnhanceUriWithDomain(uri, domain, domain_path):
  """Encode the domain and domain_path into a wonky string we use in place of the URI, which we decode with UnenhanceUriWithDomain()"""
  enhanced_uri = f'''{domain.replace('.', '__')},{domain_path.replace('/', '__')}'''

  return enhanced_uri


def UnenhanceUriWithDomain(enchanced_uri):
  """Decodes the wonkey string made by EnhanceUriWithDomain, giving us the tuple: (`domain`, `domain_path`) """
  (domain_part, path_part) = enchanced_uri.split(',')

  domain = domain_part.replace('__', '.')
  domain_path = path_part.replace('__', '/')

  return (domain, domain_path)


def RenderPathData(request, config, uri, bundle_name, bundle, path_data, domain, domain_path, request_headers=None, request_data=None):
  """Render the Path Data"""
  # Our starting payload
  payload = {'request': {}, 'header': {}, 'session': {}}

  # Rewrite the URI as the wonkey domain/domain_path for transit and cache key storage
  uri_raw = uri
  uri = EnhanceUriWithDomain(uri, domain, domain_path)

  # Check if this user is authed, if our bundle has auth
  if 'auth' in bundle and 'cookie' in bundle['auth']:
    payload['session'] = GetAuthSession(request, config, bundle_name, bundle, request_headers)

  # If we have request args, assign them into the payload
  if request_data:
    payload['request'] = request_data
  else:
    # We set the URI after this, so empty here
    request_data = {}

  # Set the URI (wonky domain/path combo) and the `uri_raw` for the static entries.  All API endponits will be static
  request_data['uri'] = uri
  request_data['uri_raw'] = uri_raw

  # if request_headers: payload['header'] = request_headers

  # LOG.info(f'''Path Data Cache: {pprint.pformat(path_data.get('cache', {}))}''')

  # Put any cache into our payload
  for (cache_key, payload_data) in path_data.get('cache', {}).items():
    # Format the cache key with the data
    cache_key = utility.FormatTextFromDictKeys(cache_key, request_data)
    # LOG.debug(f'Get from cache_key: {cache_key}')

    # Process each of our items
    for (payload_key, data_key_list) in payload_data.items():
      data_value = config.cache.Get(bundle_name, cache_key)

      # LOG.info(f'Data Value: {data_value}')
      # LOG.info(f'Add key list: {data_key_list}  From Bundle: {bundle_name}  Cache Key: {cache_key}')

      # If we have a key_list, dive down it and extract our data
      if data_key_list:
        payload[payload_key] = utility.GetDataByDictKeyList(data_value, data_key_list)
      # Else, no keys to traverse, so take all the data
      else:
        # LOG.info(f'Setting full key: {payload_key}')
        payload[payload_key] = data_value

    
      # If this doesnt exist, try to get it directly
      if payload[payload_key] == None:
        LOG.error(f'Couldnt find cache key: Bundle: {bundle_name}  Key: {cache_key}')


  # Check if we want to execute a command directly (API)
  if 'execute' in path_data:
    exec_result = ExecuteStoredCommand(config, bundle_name, bundle, path_data['execute'], payload)
    if exec_result:
      payload[path_data['execute']] = exec_result
      # LOG.info(f'''Execute Stored Command: {path_data['execute']}  Result: {exec_result}''')
  
  
  LOG.debug(f'''Payload: {pprint.pformat(payload, indent=2)}''')

  # If we have a template, then run it through Jinja
  if 'template' in path_data:
    template = path_data['template']

    payload = ProcessPayloadData(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data)

    payload = EnhancePagePayload(config, bundle_name, bundle, path_data, payload, request, request_headers, request_data, domain, domain_path)

    payload = EnsureBaseDotToUnderscore(payload)

    # Put all of payload into payload, because Jinja doesnt have a better way to insect all the vars
    payload['_context'] = payload

    return webserver.TEMPLATES.TemplateResponse(name=template, context=payload, request=request)

  # Else, just return the output  
  else:
    return Response(status_code=200, content=json.dumps(payload))
  

