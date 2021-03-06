from ckan.common import config

from urlparse import urlsplit, urlunsplit

import api
import constants
import schema
import utils

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import codecs
import datetime as dt
import re


class ExtendedAPIPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    # ==============================
    # IActions
    # ==============================

    def get_actions(self):
        return {
            "extract_info": api.extract_info,
            "quality_show": api.get_quality_score,
            "search_packages": api.query_packages,
            "search_facet": api.query_facet,
        }


class ExtendedURLPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # ==============================
    # IRoutes
    # ==============================

    def before_map(self, m):
        m.connect(
            "/download_resource/{resource_id}",
            controller="ckanext.opendata.downloads:DownloadsController",
            action="download_data",
        )

        m.connect(
            "/tags_autocomplete",
            controller="ckanext.opendata.tags:TagsController",
            action="match_tags",
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
        tk.add_template_directory(config, "templates")

    # ==============================
    # IDataset
    # ==============================

    def create_package_schema(self):
        struc = super(UpdateSchemaPlugin, self).create_package_schema()
        struc = schema.get_package_schema(struc)

        return struc

    def update_package_schema(self):
        struc = super(UpdateSchemaPlugin, self).update_package_schema()
        struc = schema.get_package_schema(struc)

        return struc

    def show_package_schema(self):
        struc = super(UpdateSchemaPlugin, self).show_package_schema()
        struc["tags"]["__extras"].append(tk.get_converter("free_tags_only"))

        struc = schema.get_package_schema(struc, show=True)

        return struc

    def is_fallback(self):
        return True

    def package_types(self):
        return []

    def get_helpers(self):
        return {"show_tags": schema.show_tags}

    # ==============================
    # IResourceController
    # ==============================

    def before_create(self, context, resource):
        package = tk.get_action("package_show")(context, {"id": resource["package_id"]})

        for idx, r in enumerate(package["resources"]):
            if r["name"] == resource["name"]:
                raise tk.ValidationError(
                    {
                        "constraints": [
                            "A resource with {name} already exists \
                            for this package".format(
                                name=r["name"]
                            )
                        ]
                    }
                )

        if not ("format" in resource and resource["format"]):
            resource["format"] = resource["url"].split(".")[-1]

        resource["format"] = resource["format"].upper()

        utils.validate_tag_in_vocab(resource["format"], "formats")

    def after_create(self, context, resource):
        schema.create_resource_views(context, resource)
        schema.update_package(context)

    def after_update(self, context, resource):
        schema.update_package(context)

    def after_delete(self, context, resources):
        schema.update_package(context)
