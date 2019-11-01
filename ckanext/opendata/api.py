from datetime import datetime

import constants
import utils

import ckan.plugins.toolkit as tk


def build_query(query):
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
            elif f in ['owner_division', 'vocab_topics', 'vocab_civic_issues']:
                terms = ' AND '.join(['"{x}"'.format(x=term) for term in v])
            else:
                continue

            q.append('{key}:({value})'.format(key=f, value=terms))
        elif k == 'search':
            for w in v.lower().split(' '):
                q.append(
                    '(name:(*{0}*))^5.0 OR '
                    '(tags:(*{1}*))^5.0 OR'
                    '(notes:("{1}")) OR '
                    '(title:(*{1}*))^10.0'.format(
                        w.replace(' ', '-'), w
                    )
                )

    return q

@tk.side_effect_free
def get_quality_score(context, data_dict):
    pid = data_dict['package_id']
    rid = None

    scores = tk.get_action('package_show')(context, {
        'id': 'catalogue-score-scores'
    })

    for r in scores['resources']:
        if r['name'] == 'catalogue-scorecard':
            rid = r['id']
            break

    if not rid is None:
        return tk.get_action('datastore_search')(context, {
            'resource_id': rid,
            'q': {
                'package': pid
            }
        })['records'][0]

    # TODO: Update error handling

@tk.side_effect_free
def extract_info(context, data_dict):
    resource_id = data_dict['resource_id']

    count = tk.get_action('datastore_info')(context, {
        'id': resource_id
    })['meta']['count']

    dt = tk.get_action('resource_show')(context, {
        'id': resource_id
    })['last_modified']

    d = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f').date()

    return {
        'rows': count,
        'updated_at': dt,
        'updated_today': d == datetime.today().date()
    }

@tk.side_effect_free
def query_facet(context, data_dict):
    q = build_query(data_dict)

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': 0,
        'facet': 'on',
        'facet.limit': -1,
        'facet.field': utils.to_list(data_dict['facet_field[]'])
    })

@tk.side_effect_free
def query_packages(context, data_dict):
    q = build_query(data_dict)

    params = constants.CATALOGUE_SEARCH.copy()
    params.update(data_dict)

    return tk.get_action('package_search')(context, {
        'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
        'rows': params['rows'],
        'sort': params['sort'],
        'start': params['start']
    })
