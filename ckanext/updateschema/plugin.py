# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk

class UpdateschemaPlugin(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)
    p.implements(p.IConfigurer)

    def _modify_package_schema(self, schema):
        schema.update({
            u"collection_method": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"excerpt": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"limitations": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"refresh_rate": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"information_url": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"owner_type": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"owner_division": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"owner_section": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"owner_unit": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"owner_email": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"image_url": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"approved_by": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"source_type": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"extraction_details": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"pipeline_stage": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"published_date": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"dataset_category": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"preview_data": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")],
            u"primary_resource": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing"), tk.get_converter(u"convert_to_extras")]
        })

        schema["resources"].update({
            u"extract_job_id": [tk.get_validator(u"ignore_missing")],
            u"file_type": [tk.get_validator(u"ignore_missing")],
            u"shape": [tk.get_validator(u"ignore_missing")],
            u"explore_url": [tk.get_validator(u"ignore_missing")]
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
            u"collection_method": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"excerpt": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"limitations": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"refresh_rate": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"information_url": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"owner_type": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"owner_division": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"owner_section": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"owner_unit": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"owner_email": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"image_url": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"approved_by": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"source_type": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"extraction_details": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"pipeline_stage": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"published_date": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"dataset_category": [tk.get_converter(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"preview_data": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing")],
            u"primary_resource": [tk.get_validator(u"convert_from_extras"), tk.get_validator(u"ignore_missing")]
        })

        schema["resources"].update({
            u"extract_job_id": [tk.get_validator(u"ignore_missing")],
            u"file_type": [tk.get_validator(u"ignore_missing")],
            u"shape": [tk.get_validator(u"ignore_missing")],
            u"explore_url": [tk.get_validator(u"ignore_missing")]
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn"t handle any special package types, it just
        # registers itself as the default (above).
        return []

    def update_config(self, config):
        # Add this plugin"s templates dir to CKAN"s extra_template_paths, so
        # that CKAN will use this plugin"s custom templates.
        tk.add_template_directory(config, "templates")
