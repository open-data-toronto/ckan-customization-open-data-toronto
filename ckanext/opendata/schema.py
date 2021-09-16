from six import string_types

from . import constants, utils

import ckan.plugins.toolkit as tk
import logging


# Default behaviours for custom fields
def default_to_none(value):
    if value:
        return value


def default_to_false(value):
    if isinstance(value, string_types):
        return value.lower() == "true"

    return bool(value)


def get_package_schema(schema, show=False):
    mods = {
        # General dataset info (inputs)
        "collection_method": [default_to_none],
        "excerpt": [default_to_none, utils.validate_length],
        "limitations": [default_to_none],
        "information_url": [default_to_none],
        # General dataset info (dropdowns)
        "dataset_category": [default_to_none, manage_tag_hexed_fields],
        "is_retired": [default_to_false],
        "refresh_rate": [default_to_none, manage_tag_hexed_fields],
        # Filters
        "civic_issues": [default_to_none],
        "formats": [default_to_none],
        "topics": [default_to_none],
        # Dataset division info
        "owner_division": [default_to_none],
        "owner_section": [default_to_none],
        "owner_unit": [default_to_none],
        "owner_email": [default_to_none],
        # Internal CKAN/WP fields
        "image_url": [default_to_none],
        "last_refreshed": [default_to_none],
    }

    if not show:
        for f in constants.TAG_LIST_FIELDS:
            mods[f].append(manage_tag_list_fields)

    for key, value in mods.items():
        if show:
            mods[key].insert(0, tk.get_converter("convert_from_extras"))
        else:
            mods[key].append(tk.get_converter("convert_to_extras"))

    for key in schema.keys():
        if any([x in key for x in constants.REMOVED_FIELDS]):
            schema.pop(key, None)

    schema.update(mods)
    schema["resources"].update(
        {"extract_job": [default_to_none], "is_preview": [default_to_false]}
    )

    return schema


def manage_tag_hexed_fields(key, data, errors, context):
    if data[key] is None:
        return

    tag = utils.string_to_hex(data[key])
    vocab = key[0]

    utils.validate_tag_in_vocab(tag, vocab)


def manage_tag_list_fields(key, data, errors, context):
    if data[key] is None:
        return

    vocab = tk.get_action("vocabulary_show")(context, {"id": key[0]})

    n = 0
    for k in data.keys():
        if k[0] == "tags":
            n = max(n, k[1] + 1)

    tags = []
    for t in data[key].split(","):
        tag = t.strip()

        if len(t):
            utils.validate_tag_in_vocab(tag, vocab["name"])
            tags.append(tag)

    for i, t in enumerate(tags):
        data[("tags", n + i, "name")] = t
        data[("tags", n + i, "vocabulary_id")] = vocab["id"]


def show_tags(vocabulary_id, hexed=False):
    tags = tk.get_action("tag_list")(data_dict={"vocabulary_id": vocabulary_id})

    if hexed:
        return map(utils.hex_to_string, tags)

    return tags


def create_resource_views(context, resource):
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
        return

    view = format_views.pop(resource_format)

    views = tk.get_action("resource_view_list")(context, {"id": resource["id"]})

    for v in views:
        if v["view_type"] == view["view_type"]:
            return

    view["resource_id"] = resource["id"]

    tk.get_action("resource_view_create")(context, view)


def update_package(context):
    print("=================== update package start ==============")
    package = context["package"]
    resources = [r for r in package.resources_all if r.state == "active"]

    formats = set()
    last_refreshed = []

    for r in resources:
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

        print(r.created)
        print(type(r.created))
        print(r.last_modified)
        print(type(r.last_modified))

        last_refreshed.append(r.created if r.last_modified is None else r.last_modified)

    # make sure the package's last refreshed date is the latest last refreshed date of its resources
    # formats = ",".join(list(formats)) if len(formats) else None
    last_refreshed = (
        max(last_refreshed).strftime("%Y-%m-%dT%H:%M:%S.%f")
        if len(last_refreshed)
        else None
    )

    #if formats != package.formats or 
    print(package)
    print(last_refreshed)
    if last_refreshed != tk.get_action("package_show")(context, {"id": package.id})["last_refreshed"]:
        tk.get_action("package_patch")(
            context,
            {"id": package.id, "last_refreshed": last_refreshed}#, "formats": formats},
        )
