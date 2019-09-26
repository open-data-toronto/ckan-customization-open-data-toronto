import constants

import ckan.plugins.toolkit as tk


@tk.side_effect_free
def search_packages(context, data_dict):
    q = _build_query(data_dict)

    for k, v in constants.CATALOGUE_SEARCH:
        if not k in data_dict:
            data_dict[k] = v

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': data_dict['rows'],
        'sort': data_dict['sort'],
        'start': data_dict['start']
    })

@tk.side_effect_free
def search_facet(context, data_dict):
    q = _build_query(data_dict)

    if not isinstance(data_dict['facet_field[]'], list):
        data_dict['facet_field[]'] = [data_dict['facet_field[]']]

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': 0,
        'facet': 'on',
        'facet.limit': -1,
        'facet.field': data_dict['facet_field[]']
    })

def _build_query(query):
    '''
        Parses parameters from frontend search inputs to respective CKAN fields
        and SOLR queries with logic.

        Args:
            query: Content passed from the API call from the frontend

        Returns:
            list: SOLR search params
    '''

    q = []

    for k, v in query.items():
        if k == 'search' and len(v) > 0:
            v = v.lower()

            q.append(
                '(name:(*{0}*))^5.0 OR '
                '(notes:("{1}")) OR '
                '(title:(*{1}*))^10.0'.format(
                    v.replace(' ', '-'), v
                )
            )
        elif k.endswith('[]'):
            field = k[:-2]

            if not isinstance(v, list):
                v = [v]

            if field in ['dataset_category', 'vocab_formats']:
                terms = ' AND '.join(['{x}'.format(x=term) for term in v])
            elif field in ['owner_division', 'vocab_topics']:
                terms = ' AND '.join(['"{x}"'.format(x=term) for term in v])
            else:
                continue

            q.append('{key}:({value})'.format(key=field, value=terms))

    return q
