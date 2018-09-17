import io

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import datetime as dt

from ckan.logic import action

class UpdateschemaPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)
    p.implements(p.IResourceController)

    # ==============================
    # IConfigurer
    # ==============================

    # Add plugin template to CKAN templates to be shown
    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    # ==============================
    # IDataset
    # ==============================

    def create_package_schema(self):
        schema = super(UpdateschemaPlugin, self).create_package_schema()

        schema.update(self._modify_package_schema('convert_to_extras'))
        schema['resources'].update(self._modify_resource_schema())

        return schema

    def update_package_schema(self):
        schema = super(UpdateschemaPlugin, self).update_package_schema()

        schema.update(self._modify_package_schema('convert_to_extras'))
        schema['resources'].update(self._modify_resource_schema())

        return schema

    def show_package_schema(self):
        schema = super(UpdateschemaPlugin, self).show_package_schema()

        schema.update(self._modify_package_schema('convert_from_extras'))
        schema['resources'].update(self._modify_resource_schema())

        return schema

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    # ==============================
    # IResourceController
    # ==============================

    def before_create(self, context, resource):
        pass

    def after_create(self, context, resource):
        self._update_package_fields(context, resource)

    def before_update(self, context, current, resource):
        pass

    def after_update(self, context, resource):
        self._update_package_fields(context, resource)

    def before_delete(self, context, resource, resources):
        pass

    def after_delete(self, context, resources):
        pass

    def before_show(self, resource_dict):
        return resource_dict

    # ==============================
    # Functions for modifying default CKAN behaviours
    # ==============================

    def _modify_package_schema(self, convert_method):
        schema = {
            # General dataset info (inputs)
            'collection_method': [tk.get_validator('ignore_missing')],
            'excerpt': [self._validate_string_length],
            'information_url': [],
            'limitations': [tk.get_validator('ignore_missing')],
            'published_date': [self._validate_date],
            # General dataset info (dropdowns)
            'dataset_category': [],
            'pipeline_stage': [],
            'refresh_rate': [],
            'require_legal': [],
            'require_privacy': [],
            # Dataset division info
            'approved_by': [tk.get_validator('ignore_missing')],
            'approved_date': [self._validate_date],
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
        for key, value in schema.items():
            if convert_method == 'convert_to_extras':
                schema[key].append(tk.get_converter(convert_method))
            elif convert_method == 'convert_from_extras':
                schema[key].insert(0, tk.get_converter(convert_method))

        return schema

    def _modify_resource_schema(self):
        resource = {
            'explore_url': [tk.get_validator('ignore_missing')],
            'file_type': [tk.get_validator('ignore_missing')],
            'columns': [tk.get_validator('ignore_missing')],
            'rows': [tk.get_validator('ignore_missing')],
            'extract_job': [tk.get_validator('ignore_missing')]
        }

        return resource

    def _update_package_fields(self, context, resource):
        data = action.get.package_show(context, { 'id': resource['package_id'] })

        if resource['file_type'] == 'Primary data':
            data['primary_resource'] = resource['id']

            for r in data['resources']:
                if r['id'] != resource['id'] and r['file_type'] == 'Primary data':
                    r['file_type'] = 'Secondary data'
                    action.update.resource_update(context, r)

        data['resource_formats'] = data['resource_formats'].lower().split(' ') if len(data['resource_formats']) else []

        if resource['datastore_active'] and resource['dataset_category'] == 'Tabular':
            data['resource_formats'] += ['CSV', 'JSON', 'XML']
        else:
            data['resource_formats'] += [resource['format'].upper()]

        data['resource_formats'] = ' '.join(list(set(sorted(data['resource_formats']))))

        action.update.package_update(context, data)

    def _validate_date(self, value, context):
        if value == '':
            return value
        elif isinstance(value, dt.datetime):
            return value.strftime('%Y-%m-%d')

        try:
            date = h.date_str_to_datetime(value)
            return date.strftime('%Y-%m-%d')
        except (TypeError, ValueError) as e:
            raise tk.Invalid('Please provide the date in YYYY-MM-DD format')

    def _validate_string_length(self, value, context):
        if not len(value):
            raise tk.Invalid('Input required')
        if len(value) > 350:
            raise tk.Invalid('Input exceed 350 character limits')
        return value
