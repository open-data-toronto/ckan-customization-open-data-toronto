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

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so that CKAN will use this plugin's custom templates.
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
        # Return True to register this plugin as the default handler for package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just registers itself as the default (above).
        return []

    # ==============================
    # IResourceController
    # ==============================

    def before_create(self, context, resource):
        pass

    def after_create(self, context, resource):
        self._validate_primary_resource(context, resource)

    def before_update(self, context, current, resource):
        pass

    def after_update(self, context, resource):
        self._validate_primary_resource(context, resource)

    def before_delete(self, context, resource, resources):
        pass

    def after_delete(self, context, resources):
        pass

    def before_show(self, resource_dict):
        return resource_dict

    # ==============================
    # Functions for modifying default CKAN behaviours
    # ==============================

    # Custom package schema

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
            'primary_resource': [tk.get_validator('ignore_missing')]
        }

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

    # Custom field validators and update field structure

    def _validate_date(self, value, context):
        if isinstance(value, dt.datetime) or value == '':
            return value

        try:
            date = h.date_str_to_datetime(value)
            return date
        except (TypeError, ValueError) as e:
            raise tk.Invalid('Please provide the date in YYYY-MM-DD format')

    def _validate_primary_resource(self, context, resource):
        if resource['file_type'] == 'Primary data':
            data = action.get.package_show(context, { 'id': resource['package_id'] })
            data['primary_resource'] = resource['id']
            action.update.package_update(context, data)

            for r in data['resources']:
                if r['id'] != resource['id'] and r['file_type'] == 'Primary data':
                    r['file_type'] = 'Secondary data'
                    action.update.resource_update(context, r)

    def _validate_string_length(self, value, context):
        if not len(value):
            raise tk.Invalid('Input required')
        if len(value) > 350:
            raise tk.Invalid('Input exceed 350 character limits')
        return value
