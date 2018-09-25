import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
import re

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
        'pipeline_stage': [],
        'refresh_rate': [],
        'require_legal': [],
        'require_privacy': [],
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
        'primary_resource': [tk.get_validator('ignore_missing')],
        'resource_formats': [tk.get_validator('ignore_missing')]
    }

    # Prepend/append appropriate converter depending if creating/updating/showing schemas
    for key, value in modifications.items():
        if convert_method == 'convert_to_extras':
            modifications[key].append(tk.get_converter(convert_method))
        elif convert_method == 'convert_from_extras':
            modifications[key].insert(0, tk.get_converter(convert_method))

    schema.update(modifications)
    schema['resources'].update({
        'explore_url': [tk.get_validator('ignore_missing')],
        'file_type': [tk.get_validator('ignore_missing')],
        'columns': [tk.get_validator('ignore_missing')],
        'rows': [tk.get_validator('ignore_missing')],
        'extract_job': [tk.get_validator('ignore_missing')]
    })

    return schema

def update_package_fields(context, data):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })
    package['resource_formats'] = []

    for idx, resource in enumerate(package['resources']):
        if 'file_type' in resource and resource['file_type'] == 'Primary data':
            if resource['id'] == data['id']:
                package['primary_resource'] = data['id']

            if 'id' in data and resource['id'] != data['id'] and 'file_type' in data and data['file_type'] == 'Primary data':
                package['resources'][idx]['file_type'] = 'Secondary data'

        package['resource_formats'].append(resource['format'].upper())

    package['resource_formats'] = ' '.join(sorted(list(set(package['resource_formats']))))

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

def validate_package_name(package):
    data = package.as_dict()

    name = re.sub(r'[^a-zA-Z0-9]+', '-', data['title'].lower())
    if name != data['name']:
        raise tk.ValidationError({
            'constraints': ['Inconsistency between package name and title']
        })

def validate_resource_name(context, data):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })

    for idx, resource in enumerate(package['resources']):
        if resource['name'] == data['name']:
            raise tk.ValidationError({
                'constraints': ['A resource with {name} already exists for this package'.format(name=data['name'])]
            })

def validate_string_length(value, context):
    if not len(value):
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
        schema = modify_package_schema(schema, 'convert_to_extras')

        return schema

    def update_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).update_package_schema()
        schema = modify_package_schema(schema, 'convert_to_extras')

        return schema

    def show_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).show_package_schema()
        schema = modify_package_schema(schema, 'convert_from_extras')

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
        update_package_fields(context, resource)

    def after_update(self, context, resource):
        update_package_fields(context, resource)

    def after_delete(self, context, resources):
        update_package_fields(context, resources[0])
