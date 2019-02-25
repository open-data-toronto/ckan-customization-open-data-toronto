import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
import re

from six import string_types

DEFAULT_FORMATS = {
    'geospatial': ['csv', 'geojson', 'shp'],
    'tabular': ['csv', 'json', 'xml']
}
DEFAULT_SEARCH = {
    'rows': 10,
    'sort': 'score desc',
    'start': 0
}
MAX_STRING_LENGTH = 350

@tk.side_effect_free
def catalogue_search(context, data_dict):
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
        v = v.lower()

        if k == 'search' and len(v) > 0:
            q.append('(name:(*' + v.replace(' ', '-') + '*)) OR (notes:("' + v + '")) OR (title:(*' + v + '*))')
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
            'rows': data_dict['rows'] if 'rows' in data_dict else DEFAULT_SEARCH['row'],
            'sort': data_dict['sort'] if 'sort' in data_dict else DEFAULT_SEARCH['sort'],
            'start': data_dict['start'] if 'start' in data_dict else DEFAULT_SEARCH['start']
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

def convert_string_to_tags(key, data, errors, context):
    topics = [topic.strip() for topic in data[key].split(',') if topic.strip()]

    vocab = tk.get_action('vocabulary_show')(context, { 'id': 'topics' })
    vocab_topics = tk.get_action('tag_list')(context, { 'vocabulary_id': vocab['id'] })

    for t in topics:
        if not t in vocab_topics:
            raise tk.ValidationError({
                'constraints': ['Tag {name} is not in the vocabulary Topics'.format(name=t)]
            })

    n = 0
    for k in data.keys():
        if k[0] == 'tags':
            n = max(n, k[1] + 1)

    for num, tag in enumerate(topics):
        data[('tags', num + n, 'name')] = tag
        data[('tags', num + n, 'vocabulary_id')] = vocab['id']

    return data[key]

def convert_tags_to_string(key, data, errors, context):
    tags = []
    vocab = tk.get_action('vocabulary_show')(context, {
        'id': 'topics'
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
        'information_url': [],
        'limitations': [tk.get_validator('ignore_missing')],
        'published_date': [validate_date],
        # General dataset info (dropdowns)
        'dataset_category': [],
        'is_retired': [],
        'pipeline_stage': [],
        'refresh_rate': [],
        'require_legal': [],
        'require_privacy': [],
        'topics': [tk.get_validator('ignore_missing')],
        # Dataset division info
        'approved_by': [tk.get_validator('ignore_missing')],
        'approved_date': [validate_date],
        'owner_type': [tk.get_validator('ignore_missing')],
        'owner_division': [tk.get_validator('ignore_missing')],
        'owner_section': [tk.get_validator('ignore_missing')],
        'owner_unit': [tk.get_validator('ignore_missing')],
        'owner_email': [tk.get_validator('ignore_missing')],
        # Internal CKAN/WP fields
        'image_url': [tk.get_validator('ignore_missing')],
        'formats': [tk.get_validator('ignore_missing')]
    }

    for key, value in modifications.items():
        if convert_method == 'input':
            if key in ('formats'):
                modifications[key].append(tk.get_converter('convert_to_tags')(key))
            elif key in ('topics'):
                modifications[key].append(convert_string_to_tags)
                modifications[key].append(tk.get_converter('convert_to_extras'))
            else:
                modifications[key].append(tk.get_converter('convert_to_extras'))
        elif convert_method == 'output':
            if key in ('formats'):
                modifications[key].insert(0, tk.get_converter('convert_from_tags')(key))
            elif key in ('topics'):
                modifications[key].append(convert_tags_to_string)
                modifications[key].insert(0, tk.get_converter('convert_from_extras'))
            else:
                modifications[key].insert(0, tk.get_converter('convert_from_extras'))

    schema.update(modifications)
    schema['resources'].update({
        'columns': [tk.get_validator('ignore_missing')],
        'rows': [tk.get_validator('ignore_missing')],
        'extract_job': [tk.get_validator('ignore_missing')],
        'is_preview': [tk.get_validator('ignore_missing')]
    })

    return schema

def update_formats(context, resources):
    formats = []
    for r in resources:
        if r['datastore_active'] or r['url_type'] == 'datastore':
            if r['format'].lower() == 'csv':
                formats += DEFAULT_FORMATS['tabular']
            elif r['format'].lower() == 'geojson':
                formats += DEFAULT_FORMATS['geospatial']
        else:
            formats.append(r['format'])

    tk.get_action('package_patch')(context, {
        'id': resources[0]['package_id'],
        'formats': [x.upper() for x in sorted(list(set(formats)))]
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
    if len(value) > MAX_STRING_LENGTH:
        raise tk.ValidationError({
            'constraints': ['Input exceed 350 character limit']
        })
    return value

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

class ExtendedAPIPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    # ==============================
    # IActions
    # ==============================

    def get_actions(self):
        return {
            'catalogue_search': catalogue_search
        }


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
