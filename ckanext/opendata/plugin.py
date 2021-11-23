from ckan.common import config

from flask import Blueprint, request, Response, redirect

from . import api, constants, schema, utils, downloads

import ckan.lib.helpers as h

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import codecs
import datetime as dt
import re

# logic used after "Download" button is clicked on Wordpress
def download_data(resource_id):
    # get the resource
    resource = tk.get_action("resource_show")(None, {"id": resource_id})

    # non datastore resources return the resource url
    if not resource["datastore_active"]:
        return redirect(resource["url"])
        
    else:
        # datastore resources convert their records into a file, whose filetype and CRS are based on the request
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
    # These are custom api endpoints
    # ex: hitting <ckan_url>/api/action/extract_info will trigger the api.extract_info function
    # These can also be used with tk.get_action("extract_info"), for example, in this CKAN extension code

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
    # Custom url that triggers a specified function when hit
    
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
    # ===============
    # Validates package / resource metadata attributes
    # These validators are referenced in our schema file

    def get_validators(self):
        return {
            'validate_length': utils.validate_length,
            'choices_to_string': utils.choices_to_string,
            'string_to_choices': utils.string_to_choices,
            'default_to_today': utils.default_to_today,
            'default_to_false': utils.default_to_false,
            'default_to_none': utils.default_to_none
        }

    # ==============================
    # IResourceController
    # ==============================

    # Handles resources around their creation, update, and delete times
    # Specifically:
    #   makes sure resources that already exist arent created again
    #   creates the map preview for geojson data
    #   updates a package's formats and last_refreshed date based on changes to its resources

    def before_create(self, context, resource):
        package = tk.get_action("package_show")(context, {"id": resource["package_id"]})

        # throw an error if we attempt to create 2 packages with the same name
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

        # auto assign a format, if the format isnt assigned yet
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