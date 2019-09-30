import utils

# Default behaviours for custom fields
def default_to_none(value):
    # TODO: CHECK IF STRING
    if not value or not value.strip():
        return None

def default_to_false(value):
    # TODO: WHAT IF VALUE IS BOOLEAN ALREADY?
    if not value or not value.strip():
        return False

# Convert structure for custom fields
# TODO: REDO THE HEXT TO STRING CONVERTERS FOR SCHEMA..

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

def show_tags(vocabulary_id, hexed=False):
    tags = tk.get_action('tag_list')(
        data_dict={'vocabulary_id': vocabulary_id}
    )

    if hexed:
        return map(utils.hex_to_string, tags)

    return tags


def show_schema(schema, show=False):
    for key in schema.keys():
        if any([ x in key for x in constants.REMOVED_FIELDS ]):
            schema.pop(key, None)

    modifications = utils.get_package_schema()

    for key, value in modifications.items():
        if show:
            modifications[key].insert(
                0, tk.get_converter('convert_from_extras')
            )
        else:
            modifications[key].insert(
                1, tk.get_converter('convert_to_extras')
            )

    schema.update(modifications)

    schema['resources'].update(utils.get_resource_schema())

    return schema

def update_package(context):
    package = context['package']
    resources = [
        r for r in package.resources_all if r.state == 'active'
    ]

    formats = []
    for r in resources:
        if ('datastore_active' in r.extras and r.extras['datastore_active']) \
            or r.url_type == 'datastore':

            if r.format.lower() == 'csv':
                formats += constants.TABULAR_FORMATS
            elif r.format.lower() == 'geojson':
                formats += constants.GEOSPATIAL_FORMATS
        else:
            formats.append(r.format)

    formats = sorted(list(set([ f.upper() for f in formats ])))

    last_refreshed = [
        r.created if r.last_modified is None else r.last_modified for r in resources
    ]

    tk.get_action('package_patch')(context, {
        'id': package.id,
        'formats': ','.join(formats) if len(formats) > 0 else None,
        'last_refreshed': max(last_refreshed) if len(last_refreshed) > 0 else None
    })

def get_package_schema():
    return {
        # General dataset info (inputs)
        'collection_method': [ default_to_none ],
        'excerpt': [ default_to_none, validate_length ],
        'limitations': [ default_to_none ],
        'information_url': [ default_to_none ],
        # General dataset info (dropdowns)
        'dataset_category': [
            default_to_none, manage_tag_hexed_fields
        ],
        'is_retired': [ default_to_false ],
        'refresh_rate': [
            default_to_none, manage_tag_hexed_fields
        ],
        # Filters
        'civic_issues': [
            default_to_none, manage_tag_list_fields
        ],
        'formats': [ default_to_none, manage_tag_list_fields ],
        'topics': [ default_to_none, manage_tag_list_fields ],
        # Dataset division info
        'owner_division': [
            default_to_none, manage_tag_hexed_fields
        ],
        'owner_section': [ default_to_none ],
        'owner_unit': [ default_to_none ],
        'owner_email': [ default_to_none ],
        # Internal CKAN/WP fields
        'image_url': [ default_to_none ],
        'last_refreshed': [ default_to_none ]
    }

def get_resource_schema():
    return {
        'extract_job': [ default_to_none ],
        'is_preview': [ default_to_false ]
    }

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
