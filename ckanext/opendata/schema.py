from six import string_types

import constants
import utils

import ckan.plugins.toolkit as tk


# Default behaviours for custom fields
def default_to_none(value):
    if value:
        return value

def default_to_false(value):
    return bool(value)

def get_package_schema():
    return {
        # General dataset info (inputs)
        'collection_method': [ default_to_none ],
        'excerpt': [ default_to_none, utils.validate_length ],
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
        'is_preview': [ default_to_false ],
        'is_zipped': [ default_to_false ]
    }

def manage_tag_hexed_fields(key, data, errors, context):
    if data[key] is None:
        return

    tag = utils.string_to_hex(data[key])
    vocab = key[0]

    utils.validate_tag_in_vocab(tag, vocab)

def manage_tag_list_fields(key, data, errors, context):
    if data[key] is None:
        return

    tag_list = data[key]

    if isinstance(data[key], string_types):
        tag_list = tag_list.split(',')

        for t in tag_list:
            tag = t.strip()
            vocab = key[0]

            if not tag:
                continue

            utils.validate_tag_in_vocab(tag, vocab)

        data[key] = tag_list
    else:
        data[key] = ','.join(tag_list)

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

    modifications = get_package_schema()

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

    schema['resources'].update(get_resource_schema())

    return schema

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

def update_package(context):
    package = context['package']
    resources = [
        r for r in package.resources_all if r.state == 'active'
    ]

    formats = set()
    last_refreshed = []

    for r in resources:
        resource_format = r.format.upper()

        if ('datastore_active' in r.extras and r.extras['datastore_active']) \
            or r.url_type == 'datastore':

            if resource_format == 'CSV':
                formats = formats.union(constants.TABULAR_FORMATS)
            elif resource_format == 'GEOJSON':
                formats = formats.union(constants.GEOSPATIAL_FORMATS)
        else:
            formats.add(resource_format)

        last_refreshed.append(
            r.created if r.last_modified is None else r.last_modified
        )

    formats = ','.join(list(formats)) if len(formats) else None
    last_refreshed = max(last_refreshed) if len(last_refreshed) else None

    if formats != package.formats or last_refreshed != package.last_refreshed:
        tk.get_action('package_patch')(context, {
            'id': package.id,
            'formats': formats,
            'last_refreshed': last_refreshed
        })
