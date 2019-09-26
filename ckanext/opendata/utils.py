from ckan.lib.navl.dictization_functions import missing

import ckan.plugins.toolkit as tk

import codecs


def string_to_hex(s):
    return codecs.encode(s.encode('utf-8'), 'hex')

def hex_to_string(s):
    return codecs.decode(s, 'hex').decode('utf-8')

def get_hex_tags(vocabulary_id):
    return map(hex_to_string, tk.get_action('tag_list')(
        data_dict={'vocabulary_id': vocabulary_id}
    ))

def validate_hex_tag(key, data, errors, context):
    tag = data[key] if is_hex(data[key]) else string_to_hex(s)

    validate_vocabulary(key[0], tag, context)

    return hex_to_string(tag)

def convert_string_to_tags(key, data, errors, context):
    if data[key]:
        tags = [t.strip() for t in data[key].split(',') if t.strip()]
        vocab = validate_vocabulary(key, tags, context)

        n = 0
        for k in data.keys():
            if k[0] == 'tags':
                n = max(n, k[1] + 1)

        for num, tag in enumerate(tags):
            data[('tags', num + n, 'name')] = tag
            data[('tags', num + n, 'vocabulary_id')] = vocab['id']

    return data[key]

def convert_tags_to_string(key, data, errors, context):
    tags = []
    vocab = tk.get_action('vocabulary_show')(context, {
        'id': key
    })

    for k in data.keys():
        if k[0] == 'tags'and data[k].get('vocabulary_id') == vocab['id']:
            name = data[k].get('display_name', data[k]['name'])
            tags.append(name)

    return ','.join(tags)

def create_preview_map(context, resource):
    if (resource['datastore_active'] or 'datastore' in resource['url']) and \
        'format' in resource and resource['format'].lower() == 'geojson' and \
        'is_preview' in resource and resource['is_preview']:

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

def default_to_none(key, data, errors, context):
    if key not in data or not data[key] or not data[key].strip():
        data[key] = None

    return data[key]

def default_to_false(key, data, errors, context):
    if key not in data or not data[key] or not data[key].strip():
        data[key] = False

    return data[key]

def validate_length(key, data, errors, context):
    if data[key] and len(data[key]) > constants.MAX_FIELD_LENGTH:
        raise tk.ValidationError({
            'constraints': [
                'Input exceed {0} character limit'.format(
                    constants.MAX_FIELD_LENGTH
                )
            ]
        })

    return data[key]

def validate_vocabulary(vocab_name, tags, context):
    vocab = tk.get_action('vocabulary_show')(context, { 'id': vocab_name })
    vocab_tags = [t['name'] for t in vocab['tags']]

    if not isinstance(tags, list):
        tags = tags.split(',')

    for t in tags:
        if not t in vocab_tags:
            raise tk.ValidationError({
                'constraints': ['Tag {0} is not in the vocabulary {1}'.format(t, vocab_name)]
            })

    return vocab

def is_geospatial():
    info = tk.get_action('datastore_info')(None, { 'id': resource_id })

    return 'geometry' in info['schema']

def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False
