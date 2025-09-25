import ckan.plugins.toolkit as tk


def create_resource_views(context, resource):
    # creates the views for resources to be viewed in the CKAN UI
    format_views = {
        "map": {
            "resource_id": resource["id"],
            "title": "Map",
            "view_type": "geojson_view",
        },
        "data_table": {
            "resource_id": resource["id"],
            "title": "Data Table",
            "view_type": "datatables_view",
            "ellipsis_length": 0,
            "date_format": "llll",
        },
    }

    # make a data tables view for all datastore resources
    if resource["datastore_active"] in [True, "true", "True"]:
        tk.get_action("resource_view_create")(context, format_views["data_table"])

    # make a map view for a resource with a 'geometry' field
    if resource["format"].lower() == "geojson":
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
            {"id": package.id, "last_refreshed": last_refreshed, "formats": formats},
        )
