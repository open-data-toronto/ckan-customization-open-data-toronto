import ckan.plugins.toolkit as tk


def create_resource_views(context, resource):
    # creates the views for resources to be viewed in the CKAN UI
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
        "dqs": {
            "resource_id": resource["id"],
            "title": "DQS",
            "view_type": "dqs_view",
        },
    }

    # we dont make views for datastore_cache resources
    if resource.get("is_datastore_cache_file", False) in [True, "True", "true"]:
        return

    # gather all old views for this resource
    views = tk.get_action("resource_view_list")(context, {"id": resource["id"]})
    existing_view_types = []
    for view in views:
        existing_view_types.append(view["view_type"])

    # make DQS views for any resource
    if "dqs_view" not in existing_view_types:
        tk.get_action("resource_view_create")(context, format_views["dqs"])

    # only make "preview" views for datastore resources
    # those require datastore resources, so if not datasore, we stop here
    if resource["datastore_active"] in [False, "False", "false"]:
        return

    # make a data explorer view for all resources
    if "recline_view" not in existing_view_types:
        tk.get_action("resource_view_create")(context, format_views["data explorer"])

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
    # Ensures that changes to a resource in a package also affect the
    # package's metadata
    package = context["package"]
    resources = [r for r in package.resources_all if r.state == "active"]

    formats = set()
    last_refreshed = []

    for r in resources:
        resource_format = r.format.upper()

        # add all resource formats to the package's list of formats
        formats.add(resource_format)

        # add possible last refreshed dates to array, to be sorted
        # through below
        last_refreshed.append(r.created if r.last_modified is None else r.last_modified)

    formats = ",".join(list(formats)) if len(formats) else None

    # make sure the package's last refreshed date is the latest last refreshed
    # date of its resources
    last_refreshed = (
        max(last_refreshed).strftime("%Y-%m-%dT%H:%M:%S.%f")
        if len(last_refreshed)
        else None
    )

    # If the last refreshed date isnt what it already is in the CKAN package,
    # update the package
    if (
        "last_refreshed"
        in tk.get_action("package_show")(context, {"id": package.id}).keys()
    ):
        old_last_refreshed = tk.get_action("package_show")(context, {"id": package.id})[
            "last_refreshed"
        ]
    else:
        old_last_refreshed = None

    if last_refreshed != old_last_refreshed:
        tk.get_action("package_patch")(
            context,
            {
                "id": package.id,
                "last_refreshed": last_refreshed,
                "formats": formats},
        )
