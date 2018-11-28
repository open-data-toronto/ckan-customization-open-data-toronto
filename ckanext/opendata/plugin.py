import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
import re

@tk.side_effect_free
def catalogue_search(context, data_dict):
    q = []

    for k, v in data_dict.items():
        if k == 'search' and len(v) > 0:
            q.append('(name:(*' + v.replace(' ', '-') + '*)) OR (notes:("' + v + '"))')
        elif (k.endswith('[]') and k[:-2] in ['dataset_category', 'owner_division', 'vocab_formats', 'topic']):
            field = k[:-2]

            if type(v) != list:
                v = [v]

            if field in ['dataset_category', 'vocab_formats']:
                terms = ' AND '.join(['{x}'.format(x=term) for term in v])
            elif field in ['owner_division', 'topic']:
                terms = ' AND '.join(['"{x}"'.format(x=term) for term in v])

            q.append('{key}:({value})'.format(key=field, value=terms))

    if data_dict['type'] == 'full':
        params = {
            'q': ' AND '.join(['({x})'.format(x=x) for x in q]),
            'rows': data_dict['rows'] if 'rows' in data_dict else 10,
            'sort': data_dict['sort'] if 'sort' in data_dict else 'name asc',
            'start': data_dict['start'] if 'start' in data_dict else 0
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

# ==============================
# Functions for modifying default CKAN behaviours
# ==============================

def modify_package_schema(schema, convert_method):
    modifications = {
        # General dataset info (inputs)
        'collection_method': [tk.get_validator('ignore_missing')],
        'excerpt': [validate_string_length],
        'information_url': [],
        'limitations': [tk.get_validator('ignore_missing')],
        'published_date': [validate_date],
        # General dataset info (dropdowns)
        'dataset_category': [],
        'is_archive': [],
        'pipeline_stage': [],
        'refresh_rate': [],
        'require_legal': [],
        'require_privacy': [],
        'topic': [tk.get_validator('ignore_missing')],
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

    # Prepend/append appropriate converter depending if creating/updating/showing schemas
    for key, value in modifications.items():
        if convert_method == 'input':
            if key == 'formats':
                modifications[key].append(tk.get_converter('convert_to_tags')('formats'))
            else:
                modifications[key].append(tk.get_converter('convert_to_extras'))
        elif convert_method == 'output':
            if key == 'formats':
                modifications[key].insert(0, tk.get_converter('convert_from_tags')('formats'))
                # schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))
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

def update_package_fields(context, data):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })
    package['formats'] = []

    for idx, resource in enumerate(package['resources']):
        if resource['datastore_active']:
            package['formats'] += ['JSON', 'XML']

        package['formats'].append(resource['format'].upper())

    package['formats'] = sorted(list(set(package['formats'])))

    tk.get_action('package_update')(context, package)

def validate_date(value, context):
    if value == '':
        return value
    elif isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d')

    try:
        date = h.date_str_to_datetime(value)
        return date.strftime('%Y-%m-%d')
    except (TypeError, ValueError) as e:
        raise tk.Invalid('Please provide the date in YYYY-MM-DD format')

def validate_resource_name(context, data):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })

    for idx, resource in enumerate(package['resources']):
        if resource['name'] == data['name']:
            raise tk.ValidationError({
                'constraints': ['A resource with {name} already exists for this package'.format(name=data['name'])]
            })

def validate_string_length(value, context):
    if isinstance(value, str) and len(value) <= 0:
        raise tk.Invalid('Input required')
    if len(value) > 350:
        raise tk.Invalid('Input exceed 350 character limits')
    return value

class DownloadStoresPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # ==============================
    # IRoutes
    # ==============================

    def before_map(self, m):
        m.connect(
            '/download_resource/{resource_id}',
            controller='ckanext.opendata.downloads:DownloadsController',
            action='download_resource')

        return m

class UpdateSchemaPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IActions)
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)
    p.implements(p.IResourceController, inherit=True)

    # ==============================
    # IActions
    # ==============================

    def get_actions(self):
        return {
            'catalogue_search': catalogue_search
        }

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

    ## To-Do items: package format update on resource update
    # def after_create(self, context, resource):
    #     update_package_fields(context, resource)
    #
    # def after_update(self, context, resource):
    #     update_package_fields(context, resource)
    #
    # def after_delete(self, context, resources):
    #     if len(resources):
    #         update_package_fields(context, resources[0])
