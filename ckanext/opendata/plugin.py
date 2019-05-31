from .catalogue import search
from .config import MAX_FIELD_LENGTH

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
import re


def convert_string_to_tags(key, data, errors, context):
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
    if (resource['datastore_active'] or resource['url_type'] == 'datastore') and \
        'format' in resource and resource['format'].lower() == 'geojson' and \
        'is_preview' in resource and resource['is_preview'] == 'true':
        found = False
        views = tk.get_action('resource_view_list')(context, {
            'id': resource['id']
        })

        for v in views:
            if v['view_type'] == 'recline_map_view':
                found = True
                break

        if not found:
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

def modify_package_schema(schema, convert_method):
    '''
        Update the package schema on package read or write.

        Args:
            schema: Original CKAN schema
            convert_method: Determines if the schema is for reading or writing
                            and affects the validators for certain fields

        Returns:
            Updated schema with customization
    '''

    modifications = {
        # General dataset info (inputs)
        'collection_method': [tk.get_validator('ignore_missing')],
        'excerpt': [validate_string_length],
        'limitations': [tk.get_validator('ignore_missing')],
        'information_url': [tk.get_validator('ignore_missing')],
        # General dataset info (dropdowns)
        'dataset_category': [],
        'is_retired': [],
        'refresh_rate': [],
        # Filters
        'formats': [tk.get_validator('ignore_missing')],
        'topics': [tk.get_validator('ignore_missing')],
        # Dataset division info
        'owner_division': [tk.get_validator('ignore_missing')],
        'owner_section': [tk.get_validator('ignore_missing')],
        'owner_unit': [tk.get_validator('ignore_missing')],
        'owner_email': [tk.get_validator('ignore_missing')],
        # Internal CKAN/WP fields
        'image_url': [tk.get_validator('ignore_missing')]
    }

    for key, value in modifications.items():
        if convert_method == 'input':
            if key in ('formats', 'topics'):
                modifications[key].append(convert_string_to_tags)
                modifications[key].append(tk.get_converter('convert_to_extras'))
            else:
                modifications[key].append(tk.get_converter('convert_to_extras'))
        elif convert_method == 'output':
            if key in ('formats', 'topics'):
                modifications[key].append(convert_tags_to_string)
                modifications[key].insert(0, tk.get_converter('convert_from_extras'))
            else:
                modifications[key].insert(0, tk.get_converter('convert_from_extras'))

    schema.update(modifications)
    schema['resources'].update({
        'extract_job': [tk.get_validator('ignore_missing')],
        'is_preview': [tk.get_validator('ignore_missing')]
    })

    return schema

def update_formats(context, resources):
    formats = []
    for r in resources:
        if r['datastore_active'] or r['url_type'] == 'datastore':
            if r['format'].lower() == 'csv':
                formats += DATASTORE_TABULAR_FORMATS
            elif r['format'].lower() == 'geojson':
                formats += DATASTORE_GEOSPATIAL_FORMATS
        else:
            formats.append(r['format'])

    tk.get_action('package_patch')(context, {
        'id': resources[0]['package_id'],
        'formats': ','.join([x.upper() for x in sorted(list(set(formats)))])
    })

def validate_date(value, context):
    if value == '':
        return value
    elif isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d')

    try:
        date = h.date_str_to_datetime(value)
        return date.strftime('%Y-%m-%d')
    except (TypeError, ValueError) as e:
        raise tk.ValidationError({
            'constraints': ['Please provide the date in YYYY-MM-DD format']
        })

def validate_resource_name(context, data):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })

    for idx, resource in enumerate(package['resources']):
        if resource['name'] == data['name']:
            raise tk.ValidationError({
                'constraints': ['A resource with {name} already exists for this package'.format(name=data['name'])]
            })

def validate_string_length(value, context):
    if isinstance(value, str) and len(value) <= 0:
        raise tk.ValidationError({
            'constraints': ['Input required']
        })
    if len(value) > MAX_FIELD_LENGTH:
        raise tk.ValidationError({
            'constraints': ['Input exceed 350 character limit']
        })
    return value

def validate_vocabulary(vocab_name, tags, context):
    try:
        vocab = tk.get_action('vocabulary_show')(context, { 'id': vocab_name })
        vocab_tags = tk.get_action('tag_list')(context, {
            'vocabulary_id': vocab['id']
        })

        if not isinstance(tags, list):
            tags = tags.split(',')

        for t in tags:
            if not t in vocab_tags:
                raise tk.ValidationError({
                    'constraints': ['Tag {0} is not in the vocabulary {1}'.format(t, vocab_name)]
                })
    except:
        raise tk.ValidationError({
            'constraints': ['{0}'.format(vocab_name)]
        })

    return vocab

class ExtendedAPIPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    # ==============================
    # IActions
    # ==============================

    def get_actions(self):
        return {
            'catalogue_search': search
        }

class ExtendedURLPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # ==============================
    # IRoutes
    # ==============================

    def before_map(self, m):
        m.connect(
            '/download_resource/{resource_id}',
            controller='ckanext.opendata.downloads:DownloadsController',
            action='download_resource')

        m.connect(
            '/tags_autocomplete',
            controller='ckanext.opendata.tags:TagsController',
            action='get_tag_list'
        )

        return m

class UpdateSchemaPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)
    p.implements(p.IResourceController, inherit=True)

    # ==============================
    # IConfigurer
    # ==============================

    # Add the plugin template's directory to CKAN UI
    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    # ==============================
    # IDataset
    # ==============================

    def create_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).create_package_schema()
        schema = modify_package_schema(schema, 'input')

        return schema

    def update_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).update_package_schema()
        schema = modify_package_schema(schema, 'input')

        return schema

    def show_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).show_package_schema()
        schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))

        schema = modify_package_schema(schema, 'output')

        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # ==============================
    # IResourceController
    # ==============================

    def before_create(self, context, resource):
        validate_resource_name(context, resource)
        print(resource['format'])
        validate_vocabulary('formats', [resource['format']], context)

    def after_create(self, context, resource):
        tk.get_action('resource_patch')(context, {
            'id': resource['id'],
            'format': resource['format'].upper()
        })

    def after_update(self, context, resource):
        create_preview_map(context, resource)
        update_formats(context, tk.get_action('package_show')(context, { 'id': resource['package_id'] })['resources'])

    def after_delete(self, context, resources):
        update_formats(context, resources)
