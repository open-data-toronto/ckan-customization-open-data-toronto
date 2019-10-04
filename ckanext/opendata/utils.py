from ckan.lib.navl.dictization_functions import missing

import ckan.plugins.toolkit as tk

import codecs


def string_to_hex(s):
    return codecs.encode(s.encode('utf-8'), 'hex')

def hex_to_string(s):
    return codecs.decode(s, 'hex').decode('utf-8')

def is_geospatial(resource_id):
    info = tk.get_action('datastore_info')(None, { 'id': resource_id })

    return 'geometry' in info['schema']

def to_list(l):
    if not isinstance(l, list):
        return [l]

    return l

# Built-in vocabulary validation requires context update
def validate_tag_in_vocab(tag, vocab):
    try:
        tk.get_action('tag_show')(None, { 'id': tag, 'vocabulary_id': vocab })
    except:
        raise tk.ValidationError({
            'constraints': [
                'Tag {0} is not in the vocabulary {1}'.format(tag, vocab)
            ]
        })

def create_preview_map(context, resource):
    if (resource['datastore_active'] or 'datastore' in resource['url']) and \
        resource.get('format', '').lower() == 'geojson' and \
        resource.get('is_preview', False):

        views = tk.get_action('resource_view_list')(context, {
            'id': resource['id']
        })

        for v in views:
            if v['view_type'] == 'recline_map_view':
                return

        tk.get_action('resource_view_create')(context, {
            'resource_id': resource['id'],
            'title': 'Map',
            'view_type': 'recline_map_view',
            'auto_zoom': True,
            'cluster_markers': False,
            'map_field_type': 'geojson',
            'limit': 500
            # 'geojson_field': 'geometry'
        })
