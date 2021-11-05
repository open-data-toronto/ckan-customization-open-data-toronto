from ckan.common import config

from flask import Blueprint, request, Response, redirect

from . import api, constants, schema, utils, downloads

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import codecs
import datetime as dt
import re

def download_data(resource_id):
    resource = tk.get_action("resource_show")(None, {"id": resource_id})
    # init flask response
    if not resource["datastore_active"]:
        return redirect(resource["url"])
        
    else:
        print("datastore!")
        filename, mimetype, data = downloads._write_datastore(request.args, resource)

        resp = Response(headers = {"Content-Disposition": 'attachment; filename="{0}"'.format(filename)} )
        resp.content_type = mimetype
        resp.set_data( data )

        return resp


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
            "datastore_cache": api.datastore_cache,
            "datastore_create": api.datastore_create_hook,
            "reindex_solr": api.reindex_solr
        }


class ExtendedURLPlugin(p.SingletonPlugin):
    
    p.implements(p.IBlueprint)

    def get_blueprint(self):
        blueprint = Blueprint('extendedurl', self.__module__)
        
        blueprint.add_url_rule("/download_resource/<resource_id>", 
            methods=["GET"], 
            view_func=download_data
        )

        return blueprint  

class UpdateSchemaPlugin(p.SingletonPlugin):
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.IValidators)

    # ===============
    # IValidators
    # Validates package / resource metadata attributes
    # ===============

    def get_validators(self):
        return {
            'validate_length': utils.validate_length,
            'choices_to_string': utils.choices_to_string,
            'string_to_choices': utils.string_to_choices,
            'default_to_today': utils.default_to_today,
            'default_to_false': utils.default_to_false
        }

    # ==============================
    # IResourceController
    # ==============================

    # Handles resources around their creation, update, and delete times
    # Specifically:
    #   makes sure resources that already exist arent created again
    #   assigns a format tag, based on the filetype of the resource
    #   makes an error if the format of the file isnt in the vocabulary already
    #   creates the map preview for geojson data
    #   updates a package's formats and last_refreshed date based on changes to its resources

    def before_create(self, context, resource):
        package = tk.get_action("package_show")(context, {"id": resource["package_id"]})

        for idx, r in enumerate(package["resources"]):
            if r["name"] == resource["name"]:
                raise tk.ValidationError(
                    {
                        "constraints": [
                            "A resource with the name {name} already exists \
                            for this package".format(
                                name=r["name"]
                            )
                        ]
                    }
                )

        if not ("format" in resource and resource["format"]):
            resource["format"] = resource["url"].split(".")[-1]
        
        resource["format"] = resource["format"].upper()
        
    def after_create(self, context, resource):
        schema.create_resource_views(context, resource)
        schema.update_package(context)

    def after_update(self, context, resource):
        schema.update_package(context)

    def after_delete(self, context, resources):
        schema.update_package(context)