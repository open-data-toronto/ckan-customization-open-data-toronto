import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt
# import downloads

# ==============================
# Functions for modifying default CKAN behaviours
# ==============================

def modify_package_schema(schema, convert_method):
    schema.update({
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
    })

    # Prepend/append appropriate converter depending if creating/updating/showing schemas
    for key, value in schema.items():
        if convert_method == 'convert_to_extras':
            schema[key].append(tk.get_converter(convert_method))
        elif convert_method == 'convert_from_extras':
            schema[key].insert(0, tk.get_converter(convert_method))

    schema['resource'].update({
        'explore_url': [tk.get_validator('ignore_missing')],
        'file_type': [tk.get_validator('ignore_missing')],
        'columns': [tk.get_validator('ignore_missing')],
        'rows': [tk.get_validator('ignore_missing')],
        'extract_job': [tk.get_validator('ignore_missing')]
    })
    
    return schema

def update_package_fields(context, data, after_delete=False):
    package = tk.get_action('package_show')(context, { 'id': data['package_id'] })

    # Update resource formats
    package['resource_formats'] = []

    for r in package['resources']:
        if data['file_type'] == 'Primary data' and r['id'] != data['id'] and r['file_type'] == 'Primary data':
            r['file_type'] = 'Secondary data'
            tk.get_action('resource_update')(context, r)

        if r['datastore_active'] and r['format'].upper() == 'CSV':
            package['resource_formats'] += ['CSV', 'JSON', 'XML']
        elif r['datastore_active']:
            package['resource_formats'] += ['JSON', 'XML']
        else:
            package['resource_formats'].append(r['format'].upper())

    package['resource_formats'] = ' '.join(sorted(list(set(package['resource_formats']))))

    # Update primary resource ID
    if data['file_type'] == 'Primary data':
        package['primary_resource'] = data['id']

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
            '/download_resource/{resource_id}/{format}',
            controller='ckanext.opendata.downloads:DownloadsController',
            action='download_resource')
        # m.connect(
        #     'resource_dictionary', '/dataset/{id}/dictionary/{resource_id}',
        #     controller='ckanext.datastore.controller:DatastoreController',
        #     action='dictionary', ckan_icon='book')
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
        # schema.update(modify_package_schema('convert_to_extras'))
        schema = modify_package_schema(schema, 'convert_to_extras')

        return schema

    def update_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).update_package_schema()
        # schema.update(modify_package_schema('convert_to_extras'))
        schema = modify_package_schema(schema, 'convert_to_extras')

        return schema

    def show_package_schema(self):
        schema = super(UpdateSchemaPlugin, self).show_package_schema()
        # schema.update(modify_package_schema('convert_from_extras'))
        schema = modify_package_schema('convert_from_extras')

        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # ==============================
    # IResourceController
    # ==============================

    def after_create(self, context, resource):
        update_package_fields(context, resource)

    def after_update(self, context, resource):
        update_package_fields(context, resource)

    def after_delete(self, context, resources):
        update_package_fields(context, resources[0])
