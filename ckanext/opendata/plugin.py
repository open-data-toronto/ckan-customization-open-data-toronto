from .catalogue import search
from .config import DATASTORE_GEOSPATIAL_FORMATS, DATASTORE_TABULAR_FORMATS, MAX_FIELD_LENGTH, REMOVED_FIELDS

from ckan.common import config

from urlparse import urlsplit, urlunsplit

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
import re


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
        'collection_method': [tk.get_validator('ignore_missing'), validate_string],
        'excerpt': [tk.get_validator('ignore_missing'), validate_string, validate_length],
        'limitations': [tk.get_validator('ignore_missing'), validate_string],
        'information_url': [tk.get_validator('ignore_missing'), validate_string],
        # General dataset info (dropdowns)
        'dataset_category': [tk.get_validator('ignore_missing')],
        'is_retired': [tk.get_validator('ignore_missing'), tk.get_validator('boolean_validator')],
        'refresh_rate': [tk.get_validator('ignore_missing')],
        # Filters
        'civic_issues': [tk.get_validator('ignore_missing'), validate_string],
        'formats': [tk.get_validator('ignore_missing'), validate_string],
        'topics': [tk.get_validator('ignore_missing'), validate_string],
        # Dataset division info
        'owner_division': [tk.get_validator('ignore_missing'), validate_string],
        'owner_section': [tk.get_validator('ignore_missing'), validate_string],
        'owner_unit': [tk.get_validator('ignore_missing'), validate_string],
        'owner_email': [tk.get_validator('ignore_missing'), validate_string],
        # Internal CKAN/WP fields
        'image_url': [tk.get_validator('ignore_missing'), validate_string],
        'last_refreshed': [tk.get_validator('ignore_missing')]
    }

    for key, value in modifications.items():
        if convert_method == 'input':
            if key in ('civic_issues', 'formats', 'topics'):
                modifications[key].append(convert_string_to_tags)
            elif key in ('dataset_category', 'refresh_rate', 'owner_division'):
                modifications[key].append(
                    tk.get_converter('convert_to_tags')(_to_plural(key))
                )

            modifications[key].insert(1, tk.get_converter('convert_to_extras'))
        elif convert_method == 'output':
            if key in ('civic_issues', 'formats', 'topics'):
                modifications[key].append(convert_tags_to_string)
            elif key in ('dataset_category', 'refresh_rate', 'owner_division'):
                modifications[key].append(
                    tk.get_converter('convert_from_tags')(_to_plural(key))
                )

            modifications[key].insert(0, tk.get_converter('convert_from_extras'))

    schema.update(modifications)
    schema['resources'].update({
        'extract_job': [tk.get_validator('ignore_missing'), validate_string],
        'is_preview': [tk.get_validator('ignore_missing'), tk.get_validator('boolean_validator')]
    })

    for key in schema.keys():
        if any([x in key for x in REMOVED_FIELDS]):
            schema.pop(key, None)

    return schema

def update_package(context):
    package = context['package']
    resources = [
        r for r in package.resources_all if r.state == 'active'
    ]

    formats = []
    for r in resources:
        if r.extra['datastore_active'] or r.url_type == 'datastore':
            if r.format.lower() == 'csv':
                formats += DATASTORE_TABULAR_FORMATS
            elif r.format.lower() == 'geojson':
                formats += DATASTORE_GEOSPATIAL_FORMATS
        else:
            formats.append(r.format)

    formats = sorted(list(set([ f.upper() for f in formats ])))

    last_refreshed = [
        r.create if r.last_modified is None else r.last_modified for r in resources
    ]

    tk.get_action('package_patch')(context, {
        'id': package.id,
        'formats': ','.join(formats) if len(formats) > 0 else None,
        'last_refreshed': max(last_refreshed) if len(last_refreshed) > 0 else None
    })

def validate_length(key, data, errors, context):
    if data[key] and len(data[key]) > MAX_FIELD_LENGTH:
        raise tk.ValidationError({
            'constraints': ['Input exceed {0} character limit'.format(MAX_FIELD_LENGTH)]
        })

    return data[key]

def validate_string(key, data, errors, context):
    if not data[key] or not data[key].strip():
        data[key] = None

    return data[key]

def validate_vocabulary(vocab_name, tags, context):
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

    return vocab

def _to_plural(word):
    if word.endswith('y'):
        return word[:-1] + 'ies'
    else:
        return word + 's'

def dataset_categories():
    try:
        tag_list = tk.get_action('tag_list')
        dataset_categories = tag_list(data_dict={'vocabulary_id': 'dataset_categories'})
        return dataset_categories
    except tk.ObjectNotFound:
        return None

def refresh_rates():
    try:
        tag_list = tk.get_action('tag_list')
        refresh_rates = tag_list(data_dict={'vocabulary_id': 'refresh_rates'})
        return refresh_rates
    except tk.ObjectNotFound:
        return None

def owner_divisions():
    try:
        tag_list = tk.get_action('tag_list')
        owner_divisions = tag_list(data_dict={'vocabulary_id': 'owner_divisions'})
        return owner_divisions
    except tk.ObjectNotFound:
        return None

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
    p.implements(p.ITemplateHelpers)

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

    def get_helpers(self):
        return {
            'dataset_categories': dataset_categories, 
            'refresh_rates': refresh_rates, 
            'owner_divisions': owner_divisions
        } 

    

    # ==============================
    # IResourceController
    # ==============================

    def before_create(self, context, resource):
        package = tk.get_action('package_show')(context, { 'id': resource['package_id'] })
        for idx, r in enumerate(package['resources']):
            if r['name'] == resource['name']:
                raise tk.ValidationError({
                    'constraints': ['A resource with {name} already exists for this package'.format(name=r['name'])]
                })

        if 'format' not in resource or not resource['format']:
            resource['format'] = resource['url'].split('.')[-1]

        resource['format'] = resource['format'].upper()

        validate_vocabulary('formats', [resource['format']], context)

    def after_create(self, context, resource):
        create_preview_map(context, resource)
        update_package(context)

    def after_update(self, context, resource):
        update_package(context)

    def after_delete(self, context, resources):
        update_package(context)

    def before_show(self, resource_dict):
        if (not 'datastore_active' in resource_dict or not resource_dict.get('datastore_active')) and \
            resource_dict.get('url_type', '') == 'upload':
            link = list(urlsplit(resource_dict.get('url')))
            site = list(urlsplit(config.get('ckan.site_url')))

            link[1] = site[1]
            resource_dict['url'] = urlunsplit(link)

        return resource_dict
