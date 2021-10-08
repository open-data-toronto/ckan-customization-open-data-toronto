from six import string_types

from . import constants, utils

import ckan.plugins.toolkit as tk
import logging

def create_resource_views(context, resource):
    #print("=================== create resource views ====================================")
    format_views = {
        "geojson": {
            "title": "Map",
            "view_type": "recline_map_view",
            "auto_zoom": True,
            "cluster_markers": False,
            "map_field_type": "geojson",
            "limit": 500,
        },
    }

    resource_format = resource.get("format", "").lower()

    if not all(
        [
            (resource["datastore_active"] or "datastore" in resource["url"]),
            resource_format in format_views.keys(),
        ]
    ):
        #print("We're not makign a view for this resource")
        return

    view = format_views.pop(resource_format)

    views = tk.get_action("resource_view_list")(context, {"id": resource["id"]})
    #print(" ####################### views ###############")
    #print(views)
    #print(" ####################### views ###############")
    
    for v in views:
        if v["view_type"] == view["view_type"]:
            #print("We found a view type in our list")
            return

    view["resource_id"] = resource["id"]

    #print("===================== resource view create view:")
    #print(view)
    #print("===================== resource view create view.")

    tk.get_action("resource_view_create")(context, view)


def update_package(context):
    #print("=================== update package start ==============")
    package = context["package"]
    resources = [r for r in package.resources_all if r.state == "active"]

    formats = set()
    last_refreshed = []

    for r in resources:
        #print(r)
        resource_format = r.format.upper()

        # Datastore resources will, by default, be marked as CSV (nonspatial) or GEOJSON (spatial)
        # the logic below ensures that other formats are tagged to those resources based on whether theyre spatial
        if (
            "datastore_active" in r.extras and r.extras["datastore_active"]
        ) or r.url_type == "datastore":

            if resource_format == "CSV":
                formats = formats.union(constants.TABULAR_FORMATS)
            elif resource_format == "GEOJSON":
                formats = formats.union(constants.GEOSPATIAL_FORMATS)
        else:
            formats.add(resource_format)

        #print(r.created)
        #print(type(r.created))
        #print(r.last_modified)
        #print(type(r.last_modified))

        last_refreshed.append(r.created if r.last_modified is None else r.last_modified)

    
    # make sure the package's last refreshed date is the latest last refreshed date of its resources
    formats = ",".join(list(formats)) if len(formats) else None
    last_refreshed = (
        max(last_refreshed).strftime("%Y-%m-%dT%H:%M:%S.%f")
        if len(last_refreshed)
        else None
    )

    #if formats != package.formats or 
    #print(package)
    #print(last_refreshed)
    #print("================================== here! ===========")
    #print(tk.get_action("package_show")(context, {"id": package.id}))
    if last_refreshed != tk.get_action("package_show")(context, {"id": package.id})["last_refreshed"]:
        tk.get_action("package_patch")(
            context,
            {"id": package.id, "last_refreshed": last_refreshed, "formats": formats},
        )
    
