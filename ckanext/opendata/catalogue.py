import ckan.plugins.toolkit as tk

from datetime import datetime

from .config import CATALOGUE_ROWS, CATALOGUE_SORT, CATALOGUE_START

@tk.side_effect_free
def extract_info(context, data_dict):
    resource_id = data_dict['resource_id']

    try:
        dt = tk.get_action('resource_show')(context, {
            'id': resource_id
        })['last_modified']
    except:
        raise Exception('Resource ID not found')

    d = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f').date()

    try:
        count = tk.get_action('datastore_info')(context, {
            'id': resource_id
        })['meta']['count']
    except:
        count = 0

    return {
        'rows': count,
        'updated_at': dt,
        'updated_today': d == datetime.today().date()
    }


@tk.side_effect_free
def search(context, data_dict):
    '''
        Parses parameters from frontend search inputs to respective CKAN fields
        and SOLR queries with logic.

        Args:
            content: Internal CKAN field for tracking environmental variables
                     (eg. CKAN user and permission)
            data_dict: Content passed from the API call from the frontend

        Returns:
            Result of the SOLR search containing a list of packages
    '''

    q = []

    for k, v in data_dict.items():
        if k == 'search' and len(v) > 0:
            v = v.lower()

            q.append('(name:(*' + v.replace(' ', '-') + '*))^5.0 OR (notes:("' + v + '")) OR (title:(*' + v + '*))^10.0')
        elif k.endswith('[]') and k[:-2] in ['dataset_category', 'owner_division', 'vocab_formats', 'vocab_topics']:
            field = k[:-2]

            if not isinstance(v, list):
                v = [v]

            if field in ['dataset_category', 'vocab_formats']:
                terms = ' AND '.join(['{x}'.format(x=term) for term in v])
            elif field in ['owner_division', 'vocab_topics']:
                terms = ' AND '.join(['"{x}"'.format(x=term) for term in v])

            q.append('{key}:({value})'.format(key=field, value=terms))

    if data_dict['type'] == 'full':
        params = {
            'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
            'rows': data_dict['rows'] if 'rows' in data_dict else CATALOGUE_ROWS,
            'sort': data_dict['sort'] if 'sort' in data_dict else CATALOGUE_SORT,
            'start': data_dict['start'] if 'start' in data_dict else CATALOGUE_START
        }
    elif data_dict['type'] == 'facet':
        params = {
            'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
            'rows': 0,
            'facet': 'on',
            'facet.limit': -1,
            'facet.field': data_dict['facet_field[]'] if type(data_dict['facet_field[]']) == list else [data_dict['facet_field[]']]
        }

    return tk.get_action('package_search')(context, params)
