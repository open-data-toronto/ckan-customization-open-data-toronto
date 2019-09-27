import constants

import ckan.plugins.toolkit as tk


@tk.side_effect_free
def search_packages(context, data_dict):
    q = _build_query(data_dict)

    params = constants.CATALOGUE_SEARCH.copy()
    params.update(data_dict)

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': params['rows'],
        'sort': params['sort'],
        'start': params['start']
    })

@tk.side_effect_free
def search_facet(context, data_dict):
    q = _build_query(data_dict)

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': 0,
        'facet': 'on',
        'facet.limit': -1,
        'facet.field': utils.to_list(data_dict['facet_field[]'])
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
        if not len(v):
            continue

        if k.endswith('[]'):
            f = k[:-2]
            v = utils.to_list(v)

            if f in ['dataset_category', 'vocab_formats']:
                terms = ' AND '.join(['{x}'.format(x=term) for term in v])
            elif f in ['owner_division', 'vocab_topics']:
                terms = ' AND '.join(['"{x}"'.format(x=term) for term in v])
            else:
                continue

            q.append('{key}:({value})'.format(key=f, value=terms))
        elif k == 'search':
            # TODO: TOKENIZE SEARCH TERM
            v = v.lower()

            q.append(
                '(name:(*{0}*))^5.0 OR '
                '(notes:("{1}")) OR '
                '(title:(*{1}*))^10.0'.format(
                    v.replace(' ', '-'), v
                )
            )

    return q
