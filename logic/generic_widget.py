"""
Functions that create data (dicts/lists) for Jinja to consume, for each of the types of widgets we have
"""

from logic.log import LOG

from logic.utility import GetUUID


def DataForHTMX(method, url, switch, select, swap, trigger, onload):
  """Come up with the data needed to format any HTMX interaction, then all the widgets can just natively support this"""
  #
  #
  #
  #TODO(geoff): HTMX could be added on with its own data function, but is then incorporated into the template.  Think about it
  pass


def DataForTimeline(title, time_str, info, label=None, button_title=None, button_url=None):
  """Create the data Jinja wants for a timeline"""
  data = {'title': title, 'time': time_str, 'label': label, 'button_title': button_title, 'button_url': button_url}

  return data


def DataForPopover_Info(topic_title, topic_info, subject_title=None, subject_data=None, url=None, UUID=None):
  """Create the data Jinja wants for a Popover which is the Topic Information type.  2 titles and texts with link"""
  #NOTE(geoff): Create a UUID for this item, so we can dynamically create popovers or tooltips
  if UUID == None:
    UUID = GetUUID()

  data = {'title': topic_title, 'info': topic_info, 'subtitle': subject_title, 'subinfo': subject_data, 
          'uuid': UUID, 'url': url}

  return data


def DataForCard(title, info, icon=None, color=None, color_text=None, url=None, UUID=None, popover=None):
  """Create the data Jinja wants for a Card"""
  # Optional Popover data.  If we have it, we take their UUID so the events can be aligned in HTML
  if popover != None:
    UUID = popover['uuid']

  #NOTE(geoff): Create a UUID for this item, so we can dynamically create popovers or tooltips
  if UUID == None:
    UUID = GetUUID()

  data = {'title': title, 'info': info, 'uuid': UUID, 'popover': popover, 'icon': icon, 'url': url,
          'color': color, 'color_text': color_text}

  return data


def DataForBreadcrumbs(current_page, prior_page_crumbs = None):
  """Returns the data required to format Breadcrumbs"""
  crumbs = []

  breadcrumbs = {'name': current_page, 'crumbs': []}

  # Make the fields work easier to templating, but this is uglier for us to create by hand or code
  for field in prior_page_crumbs:
    key = list(field.keys())[0]
    value = field[key]
    breadcrumbs['crumbs'].append({'name': key, 'url': value})

  return breadcrumbs


def DataForTableDictOfDicts(row_data, table_id, key_label, fields, key_url = None):
  """Returns the data required to format a Table from a Dict of Dicts"""
  data = {'id': table_id, 'rows': row_data, 'key_label': key_label, 'fields': [], 'key_url': key_url}

  # Make the fields work easier to templating, but this is uglier for us to create by hand or code
  for field in fields:
    key = list(field.keys())[0]
    name = field[key]
    data['fields'].append({'label': name, 'name': key})
  
  return data


def DataForTableListOfDicts(row_data, table_id, key_label, key_field, fields, key_url = None):
  """Returns the data required to format a Table from a Dict of Dicts"""
  data = {'id': table_id, 'rows': row_data, 'key_label': key_label, 'key_field': key_field, 'fields': [], 'key_url': key_url}

  # Make the fields work easier to templating, but this is uglier for us to create by hand or code
  for field in fields:
    key = list(field.keys())[0]
    name = field[key]
    data['fields'].append({'label': name, 'name': key})
  
  return data


def DataForGraph(label, element, timeseries):
  """Returns data for a Graph"""
  data = {'label': label, 'element': element, 'timeseries_csv': [], 'labels_csv': []}

  for count in range(0, len(timeseries)):
    value = timeseries[count]

    value_str = f'{value:.2f}'

    data['timeseries_csv'].append(value_str)
    data['labels_csv'].append(f'{count}')

  data['timeseries_csv'] = ', '.join(data['timeseries_csv'])
  data['labels_csv'] = ', '.join(data['labels_csv'])

  return data

