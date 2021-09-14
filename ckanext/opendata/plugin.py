from ckan.common import config

from flask import Blueprint, request, Response
#from urllib.urlparse import urlsplit, urlunsplit

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
    #@ resp = flask.Response()

    if not resource["datastore_active"]:
        tk.redirect_to(resource["url"])
    else:
        #filename, mimetype = downloads._write_datastore(tk.request.GET, resource)
        filename, mimetype, data = downloads._write_datastore(request.args, resource)

        resp = Response(headers = {"Content-Disposition": 'attachment; filename="{0}"'.format(filename)} )
        resp.content_type = mimetype
        resp.set_data( data )
        #resp.headers["Content-Disposition"] = b'attachment; filename="{0}"'.format(filename)

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

    '''
    # pre 2.9 url providing

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
    '''
    

class ManagePackageSchemaPlugin(p.SingletonPlugin):
    p.implements(p.IPackageController)

    # ========================
    # IPackageController
    # Hooks to manage package metadata as desired
    # ========================

    def read(self, entity):
        pass
    def create(self, entity):
        pass
    def edit(self, entity):
        pass
    def delete(self, entity):
        pass
    def after_create(self, context, pkg_dict):
        pass
    def after_update(self, context, pkg_dict):
        pass
    def after_delete(self, context, pkg_dict):
        pass
    def after_show(self, context, pkg_dict):
        pass

    def before_search(self, search_params):
        # runs before package_search
        print("======================== before search! ===========")
        print( search_params )
        print("======================== before search! ===========")

        return search_params

    def after_search(self, search_results, search_params):
        # runs after package_search
        print("======================== after search! ===========")
        print( search_params )
        print( search_results )
        print(search_results.keys())
        print(search_results["search_facets"].keys())
        if "topics" in search_results["search_facets"].keys():
            utils.unstringify( search_results["search_facets"]["topics"]["items"] )
        # TODO - make a function that looks for stringified lists, then:
        #   un-stringifies them into an array
        #   makes them into one array
        #   counts distinct values in that array
        #   returns a dict object like this:
        """
        "vocab_topics": {
                "items": [
                    {
                        "count": 9,
                        "display_name": "Transportation",
                        "name": "Transportation"
                    },
                    {
                        "count": 1,
                        "display_name": "Public safety",
                        "name": "Public safety"
                    },
                    {
                        "count": 1,
                        "display_name": "Parks and recreation",
                        "name": "Parks and recreation"
                    }
                ],
                "title": "vocab_topics"
        """
        print("======================== after search! ===========")

        return search_results

    def before_index(self, pkg_dict):
        print("======================== before index! ===========")
        print(pkg_dict)
        print("======================== before index! ===========")

        return pkg_dict

    def before_view(self, pkg_dict):
        # runs before /package_show
        print("======================== before view! ===========")
        print(pkg_dict)
        print("======================== before view! ===========")

        return pkg_dict

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

    # Handles package metadata schemas when theyre created, updated, or shown to a user
    
    # In brief, it does the following to the schema:
    #   dataset_category and refresh_rate are converted into hexes
    #   excerpt's length is kepy below 350 characters
    #   empty / errored fields default to None
    #   author, maintainer, and version are removed
    #   extract_job and is_preview are added to the resource's schema
    #   civic_issues, formats, and topics get special treatment:
    #       theyre saved as references to vocab, instead of the vocab itself
    #       there is a helper function that translates them back from references to actual vocab strings

    # this is applied to all packages - it is the "fallback" schema


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
