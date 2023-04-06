'''Functions for managing CKAN package schemas and resource views'''

import ckan.plugins.toolkit as tk


def create_resource_views(context, resource):
    '''creates the views for resources to be viewed in the CKAN UI'''
    format_views = {
        "map": {
            "resource_id": resource["id"],
            "title": "Map",
            "view_type": "recline_map_view",
            "auto_zoom": True,
            "cluster_markers": False,
            "map_field_type": "geojson",
            "limit": 500,
        },
        "data explorer": {
            "resource_id": resource["id"],
            "title": "Data Explorer",
            "view_type": "recline_view",
        },
    }

    # only make views for datastore resources
    if resource["datastore_active"] in [False, "False", "false"]:
        return

    # delete all old views for this resource
    views = tk.get_action("resource_view_list")(context, {"id": resource["id"]})
    existing_view_types = []
    for view in views:
        existing_view_types.append(view["view_type"])
        # tk.get_action("resource_view_delete")(context, {"id": view["id"] })

    # make a data explorer view for all resources
    if "recline_view" not in existing_view_types:
        tk.get_action("resource_view_create")(
            context, format_views["data explorer"]
        )

    # make a map view for a resource with a 'geometry' field
    if (
        "geometry"
        in [
            field["id"]
            for field in tk.get_action("datastore_search")(
                context, {"id": resource["id"], "limit": 0}
            )["fields"]
        ]
        and "recline_map_view" not in existing_view_types
    ):
        tk.get_action("resource_view_create")(context, format_views["map"])


def update_package(context):
    """propagates changes in a resource to package's metadata

    This includes:
    - adding or changing resource formats
    - adding or changing resource last updated dates

    """

    package = context["package"]
    resources = [r for r in package.resources_all if r.state == "active"]

    # start by checking if the dataset is retired. If it is, set
    # refresh_rate = "Will not be Refreshed"

    formats = set()
    last_refreshed = []

    for resource in resources:
        resource_format = resource.format.upper()

        # add all resource formats to the package's list of formats
        formats.add(resource_format)

        # add possible last refreshed dates to array
        if resource.last_modified is None:
            last_refreshed.append(resource.created)
        else:
            last_refreshed.append(resource.last_modified)

    formats = ",".join(list(formats)) if len(formats) > 0 else None

    # make sure the package's last refreshed date is the latest last refreshed
    # date of its resources
    last_refreshed = (
        max(last_refreshed).strftime("%Y-%m-%dT%H:%M:%S.%f")
        if len(last_refreshed) > 0
        else None
    )

    # If the last refreshed date isnt what it already is in the CKAN package,
    # update the package formats and last_refreshed
    if (
        "last_refreshed"
        in tk.get_action("package_show")(context, {"id": package.id}).keys()
    ):
        old_last_refreshed = tk.get_action("package_show")(
            context, {"id": package.id})["last_refreshed"]
    else:
        old_last_refreshed = None

    if last_refreshed != old_last_refreshed:
        tk.get_action("package_patch")(
            context,
            {
                "id": package.id,
                "last_refreshed": last_refreshed,
                "formats": formats,
            },
        )
