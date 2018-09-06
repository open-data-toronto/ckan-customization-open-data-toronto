import ckan.plugins as p
import ckan.plugins.toolkit as tk

class UpdateschemaPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)
    p.implements(p.IConfigurer)

    def _modify_package_schema(self, schema):
        schema.update({
            # General dataset info (dropdown)
            'dataset_category': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'refresh_rate': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'pipeline_stage': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            # General dataset info (inputs)
            'collection_method': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'excerpt': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'information_url': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'limitations': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'published_date': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            # Dataset division info
            'approved_by': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'approved_date': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'owner_type': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'owner_division': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'owner_section': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'owner_unit': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'owner_email': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            # Internal CKAN/WP fields
            'image_url': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')],
            'primary_resource': [tk.get_validator('ignore_missing'), tk.get_converter('convert_to_extras')]
        })

        schema['resources'].update({
            'explore_url': [tk.get_validator('ignore_missing')]
            'file_type': [tk.get_validator('ignore_missing')],
            'preview_data': [tk.get_validator('ignore_missing')],
            'columns': [tk.get_validator('ignore_missing')],
            'rows': [tk.get_validator('ignore_missing')],
            'extract_job_id': [tk.get_validator('ignore_missing')],
        })
        return schema

    def create_package_schema(self):
        schema = super(UpdateschemaPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(UpdateschemaPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(UpdateschemaPlugin, self).show_package_schema()
        schema.update({
            # General dataset info (dropdown)
            'dataset_category': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'refresh_rate': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'pipeline_stage': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            # General dataset info (inputs)
            'collection_method': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'excerpt': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'information_url': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'limitations': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'published_date': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            # Dataset division info
            'approved_by': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'approved_date': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'owner_type': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'owner_division': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'owner_section': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'owner_unit': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'owner_email': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            # Internal CKAN/WP fields
            'image_url': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')],
            'primary_resource': [tk.get_converter('convert_from_extras'), tk.get_validator('ignore_missing')]
        })

        schema['resources'].update({
            'explore_url': [tk.get_validator('ignore_missing')]
            'file_type': [tk.get_validator('ignore_missing')],
            'preview_data': [tk.get_validator('ignore_missing')],
            'columns': [tk.get_validator('ignore_missing')],
            'rows': [tk.get_validator('ignore_missing')],
            'extract_job': [tk.get_validator('ignore_missing')],
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, 'templates')
