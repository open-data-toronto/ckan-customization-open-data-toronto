"""'Logic for multiple Open Data Toronto-specific CKAN actions"""

import functools
import io
import logging
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

import ckan.plugins.toolkit as tk
from ckan.authz import is_sysadmin
from werkzeug.datastructures import FileStorage

from .constants import MULTIPLE_CHOICE_PACKAGE_FIELDS, DatastoreCacheFormats
from .util import utils
from .util.intake import utils as intake_utils
from .util.intake.types import (
    PreparedIntake,
)


def build_query(query_args: Dict[str, str]) -> str:
    """_summary_
    Takes inputs to api calls
    maps those inputs to respective CKAN fields
    and SOLR queries and returns a valid query

    :param query_args:  Content passed from the API call from the frontend
    :type query_args: Dict[str, str]
    :return: a Solr 'query' string
    :rtype: str
    """

    query = []

    for k, v in query_args.items():  # For items in the input API call's params...
        if not len(v):  # ignore empty strings and non-strings
            continue

        if (
            k.endswith("[]") and k != "facet_field[]"
        ):  # If a key ends in [], it must be an input filter! So...
            f = k[:-2]  # remove [] at end of key names and turn values to list
            if f.startswith(
                "vocab_"
            ):  # if there is a vocab_ prefix in the key name, remove that too
                f = f[6:]
            v = utils.list_to_words(
                v
            )  # split the input values by spaces and return list of each word

            this = (
                "("
                + " AND ".join(
                    [
                        "+{f}:*{x}*".format(x=term.replace("vocab_", ""), f=f)
                        for term in v
                    ]
                )
                + ")"
            )
            query.append(this)  # remove any vocab_ prefix from values

        elif (
            k == "search"
        ):  # When a key is "search" (when searching with opentext search bar)
            for w in v.lower().split(
                " "
            ):  # split the input by spaces, add solr syntax, add to output
                query.append(
                    "(name:(*{0}*))^5.0 OR "
                    "(tags:(*{1}*))^5.0 OR "
                    '(notes:("{1}")) OR '
                    "(title:(*{1}*))^10.0".format(w.replace(" ", "-"), w)
                )

    return " AND ".join(["({x})".format(x=x) for x in query])


@tk.side_effect_free
def quality_show(context, data_dict):
    """Receives package_id as input
    returns associated data quality score from catalog"""
    pid = data_dict.get("package_id")
    rid = None

    if pid is None:
        raise tk.ValidationError("Missing package ID")

    package = tk.get_action("package_show")(context, {"id": "catalogue-quality-scores"})

    for r in package["resources"]:
        if r["name"] == "quality-scores-explanation-codes-and-scores":
            rid = r["id"]
            break

    if rid is not None:
        return [
            r
            for r in tk.get_action("datastore_search")(
                context,
                {"resource_id": rid, "q": {"package": pid}, "sort": "recorded_at desc"},
            )["records"]
            if r["package"] == pid
        ]


@tk.side_effect_free
def search_facet(context, data_dict):
    """runs package_search API call with input parameters
    This is triggered in the UI when someone clicks on a Dataset Filter
    This returns the appearance of the filter panel on the left side
    of open.toronto.ca intelligently
    """

    facet_field = data_dict.get("facet_field[]")
    if not (isinstance(facet_field, list) or isinstance(facet_field, str)):
        raise tk.ValidationError("facet_field[] parameter must be provided as a list")

    query = build_query(data_dict)

    output = tk.get_action("package_search")(
        context,
        {
            "q": query,  # solr query
            "rows": 0,  # max number of rows shown - presumably 0 is maximum
            "facet": "on",  # whether to enable faceted results
            "facet.limit": -1,  # vals a facet field can return. -1 = infinity
            # fields to facet on - usually a list of all dataset filters
            "facet.field": utils.to_list(facet_field),
        },
    )

    # for the "multiple_" metadata attrs in the package schema, clean output
    # e.g: topics, civic_issues, formats
    mc_package_fields = [
        facet
        for facet in MULTIPLE_CHOICE_PACKAGE_FIELDS
        if facet in output["search_facets"]
    ]
    for facet in mc_package_fields:
        output["search_facets"][facet]["items"] = utils.calculate_list_facets(
            output["search_facets"][facet]["items"]
        )
    return output


@tk.side_effect_free
def search_requests(context, data_dict) -> PreparedIntake:

    intake_tickets = intake_utils.get_intake_tickets(context)

    status_definitions = intake_utils.get_status_definitions(context)

    ticket_ids = {row["Ticket Id"] for row in intake_tickets}

    # group records by ticket id
    grouped_tickets = intake_utils.group_tickets(intake_tickets, ticket_ids)

    # group records by linked ticket id
    linked_tickets = intake_utils.join_linked_tickets(grouped_tickets)

    return intake_utils.summarize_intake(status_definitions, linked_tickets, data_dict)


@tk.side_effect_free
def search_packages(context, data_dict):
    """Used by the catalog page to determine which packages should be listed
    It receives inputs from filters or search terms users have selected
    on the catalog page, then returns the correct CKAN packages"""
    query = build_query(data_dict)
    sort = data_dict.get("sort", "score desc")
    retired_last = utils.to_bool(data_dict.get("retired_last", False), False)
    if retired_last:
        # First sort expression here ensures is_retired datasets are sorted lasted.
        # This isn't the best/most efficient sort term - `is_retired` comes from
        # package_extra which exists in solr just as stringified JSON (it gets
        # deserialized in CKAN as a boolean via scheming output_validators for the FE)..
        # So to check for is_retired==False from solr's perspective we need to do messy
        # string-check (termferq) for 'false'.
        # TODO: We can fix this by changing Solr's schemal.xml but this is presently a black
        # box to us (OD team) - we will need changes to CFN to modify this xml file..
        sort = f"or(not(exists(is_retired)),termfreq(is_retired,'false')) desc, {sort}"
    rows = data_dict.get("rows", 10)
    start = data_dict.get("start", 0)

    output = tk.get_action("package_search")(
        context,
        {
            "q": query,
            "rows": rows,
            "sort": sort,
            "start": start,
        },
    )

    intake = tk.get_action("search_requests")(context, {"page": "dataset", "resolved": "false"})

    intake_names = {intake_utils.parse_package_name(intake["ticket_group_name"]) for intake in intake["intake"]}

    for i in range(len(output["results"])):
        output["results"][i]["updating"] = output["results"][i]["name"] in intake_names

    return output


# ---------------------------------------------------------------------------
# Activity-stream suppression for datastore_cache
#
# Rewriting a resource's cached filestore copies (CSV/XML/JSON/geo) touches
# several resources via resource_create/resource_patch, and each of those calls
# package_update under the hood - which CKAN's activity plugin turns into an
# activity-stream entry. A single cache run therefore produced six-to-eight
# activity records, bloating the activity table for high-frequency datasets.
#
# We suppress every activity generated during a datastore_cache run except one
# deliberate entry per resource, so a data refresh records a single
# "changed package" activity instead of a burst. Suppression is thread-local,
# so it only affects the worker handling the cache request.
# ---------------------------------------------------------------------------
_activity_suppression = threading.local()


def _suppress_activity_start():
    _activity_suppression.active = True
    _activity_suppression.allow_next = False


def _suppress_activity_stop():
    _activity_suppression.active = False
    _activity_suppression.allow_next = False


def _allow_one_activity():
    """Let the next activity_create call through, then resume suppressing."""
    _activity_suppression.allow_next = True


def _should_suppress_activity() -> bool:
    if not getattr(_activity_suppression, "active", False):
        return False
    if getattr(_activity_suppression, "allow_next", False):
        _activity_suppression.allow_next = False
        return False
    return True


def _reset_activity_suppression(func):
    """Guarantee suppression state never leaks past a datastore_cache call."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            _suppress_activity_stop()

    return wrapper


@tk.chained_action
def activity_create(original_activity_create, context, data_dict):
    """Suppress activity-stream entries generated during a datastore_cache run.

    All package/resource activity created while caching is dropped except a
    single deliberate entry per resource (see datastore_cache), reducing a data
    refresh from six-to-eight activity records down to one. Outside of caching
    this is a transparent pass-through to CKAN's activity_create.
    """
    if _should_suppress_activity():
        return None
    return original_activity_create(context, data_dict)


@_reset_activity_suppression
def datastore_cache(context, data_dict):
    """Logic for creating datastore_cache filestore resources
    Datastore_cache filestore resources are filestore copies
    of datastore resources. They're saved in the filestore so
    they can be accessed quickly by users.

    This logic creates different kinds of filestore files for geographic
    vs non geographic datasets.

    For non geographic datastore resources, it creates:
    - XML
    - CSV
    - JSON

    For geographic datastore resources, it creates:
    - geojson
    - csv
    - gpkg
    - shp
    It creates each of these in 2 EPSGs:
    - 4326
    - 2952
    """
    # init some params we'll need later
    output = {}

    # make sure an authorized user is making this call
    if not context.get("auth_user_obj", None):
        raise tk.NotAuthorized("This endpoint can be used by authorized accounts only")

    # make sure the call has the necessary inputs
    if "resource_id" not in data_dict.keys() and "package_id" not in data_dict.keys():
        raise tk.ValidationError(
            {"constraints": ["Endpoint needs input package_id or resource_id"]}
        )

    logging.info("[ckanext-opendatatoronto] ----- Datastore Caching has started!")

    # if input param has package id, get all its datastore resource
    logging.info("[ckanext-opendatatoronto] --- Looking for package id in data_dict")
    if "package_id" in data_dict.keys():
        package = tk.get_action("package_show")(
            context, {"id": data_dict["package_id"]}
        )
        package_summary = {
            "package_id": package["name"],
            "resources": [
                {"id": resource["id"], "name": resource["name"]}
                for resource in package["resources"]
                if resource["datastore_active"] in [True, "true", "True"]
            ],
        }

    # otherwise, use input param has resource id only
    logging.info(
        "[ckanext-opendatatoronto]----------- Looking for resource id in data_dict"
    )
    if "resource_id" in data_dict.keys() and "package_id" not in data_dict.keys():
        resource = tk.get_action("resource_show")(
            context, {"id": data_dict["resource_id"]}
        )
        package = tk.get_action("package_show")(context, {"id": resource["package_id"]})
        resource_id = (
            resource["id"]
            if resource["datastore_active"] in [True, "true", "True"]
            else None
        )
        resource_name = (
            resource["name"]
            if resource["datastore_active"] in [True, "true", "True"]
            else None
        )
        resource_dict = (
            {"id": resource_id, "name": resource_name}
            if resource["datastore_active"] in [True, "true", "True"]
            else None
        )
        package_summary = {"package_id": package["name"], "resources": [resource_dict]}

    logging.info(
        "----------- found {} resources in datastore_cache input".format(
            str(len(package_summary["resources"]))
        )
    )

    if len(package_summary["resources"]) == 0:
        raise tk.ValidationError(
            {"constraints": ["Your inputs are not associated with datastore resources"]}
        )

    # Suppress the burst of activity-stream entries that the caching writes
    # below would otherwise create; a single entry is emitted per resource
    # instead (see _allow_one_activity before the final resource_patch).
    _suppress_activity_start()

    # for each resource id in your list...
    for resource_info in package_summary["resources"]:
        # init output
        output = {}

        # find out if resource is spatial
        # if it is, we need to create 2 files per file format for each CRS
        logging.info("[ckanext-opendatatoronto]--------- checking if spatial")
        is_geospatial = utils.is_geospatial(resource_info["id"])

        # run iotrans wrapper on each file + EPSG combination
        # if this is spatial, we'll need to repeat the stuff below for
        # EPSG codes 4326 and 2952 in spatial formats
        if is_geospatial:

            for format in DatastoreCacheFormats.spatial.value:
                output[format.upper()] = {}

            logging.info(
                "[ckanext-opendatatoronto]=========================== CONVERTING Spatial FILE"
            )
            logging.info(resource_info)

            cached_files = tk.get_action("to_file")(
                context,
                {
                    "resource_id": resource_info["id"],
                    "source_epsg": 4326,
                    "target_epsgs": [4326, 2952],
                    "target_formats": [
                        fmt.lower() for fmt in DatastoreCacheFormats.spatial.value
                    ],
                },
            )

            # get directory where all these cached files will be stored
            # we'll want to use it to delete the dir later
            cached_files_dir = "/".join(list(cached_files.values())[0].split("/")[:-1])

            for key, val in cached_files.items():
                format = key.split("-")[0]
                epsg_code = key.split("-")[1]
                mimetype = "application/octet-stream"
                filename = val.split("/")[-1]

                with open(val, "rb") as f:
                    response = io.BytesIO(f.read())
                    f.close()
                    logging.info(
                        "[ckanext-opendatatoronto]--------------- "
                        + format
                        + " "
                        + epsg_code
                    )

                try:
                    # try making a resource from scratch
                    filestore_resource = tk.get_action("resource_create")(
                        context,
                        {
                            "package_id": package_summary["package_id"],
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True,
                            "datastore_resource_id": resource_info["id"],
                        },
                    )

                # TODO fix bare exception without `raise`
                except Exception:
                    # otherwise, update the existing one
                    existing_resource = tk.get_action("resource_search")(
                        context, {"query": "name:{}".format(filename)}
                    )
                    resource_id = existing_resource["results"][0]["id"]
                    filestore_resource = tk.get_action("resource_patch")(
                        context,
                        {
                            "id": resource_id,
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True,
                            "datastore_resource_id": resource_info["id"],
                        },
                    )

                # add details to output
                output[format.upper()][epsg_code] = filestore_resource["id"]

                # delete temp file now that we've used it
                tk.get_action("prune")(context, {"path": val})
        # if its not spatial, we'll have different file formats,
        # but no epsg codes to worry about
        else:
            for format in DatastoreCacheFormats.non_spatial.value:
                output[format.upper()] = {}

            logging.info(
                "[ckanext-opendatatoronto]---------- CONVERTING Non Spatial FILE"
            )
            logging.info("[ckanext-opendatatoronto]-------------- " + format)
            cached_files = tk.get_action("to_file")(
                context,
                {
                    "resource_id": resource_info["id"],
                    "target_formats": [
                        fmt.lower() for fmt in DatastoreCacheFormats.non_spatial.value
                    ],
                },
            )

            # get directory where all these cached files will be stored
            # we'll want to use it to delete the dir later
            cached_files_dir = "/".join(list(cached_files.values())[0].split("/")[:-1])

            for key, val in cached_files.items():
                format = key.split("-")[0]
                mimetype = "application/octet-stream"
                filename = val.split("/")[-1]
                with open(val, "rb") as f:
                    response = io.BytesIO(f.read())

                try:
                    # try creating a resource
                    filestore_resource = tk.get_action("resource_create")(
                        context,
                        {
                            "package_id": package_summary["package_id"],
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True,
                            "datastore_resource_id": resource_info["id"],
                        },
                    )
                # TODO fix bare exception without `raise`
                except Exception:
                    # otherwise edit an existing resource
                    existing_resource = tk.get_action("resource_search")(
                        context, {"query": "name:{}".format(filename)}
                    )
                    resource_id = existing_resource["results"][0]["id"]
                    filestore_resource = tk.get_action("resource_patch")(
                        context,
                        {
                            "id": resource_id,
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True,
                            "datastore_resource_id": resource_info["id"],
                        },
                    )

                # add details to output
                output[format.upper()] = filestore_resource[
                    "id"
                ]  # put resource id for filestore resource

                # delete temp file now that we've used it
                tk.get_action("prune")(context, {"path": val})

        # delete the temp directory where we stored the cached files
        tk.get_action("prune")(context, {"path": cached_files_dir})

        # Allow exactly one activity-stream entry for this resource: the final
        # metadata patch below records a single "changed package" activity,
        # while all the per-format caching activity above stays suppressed.
        _allow_one_activity()

        # current date and cache paths into resource_patch call
        tk.get_action("resource_patch")(
            context,
            {
                "id": resource_info["id"],
                "datastore_cache": output,
                "datastore_cache_last_update": datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                ),
                "record_count": utils.count_datastore_rows(resource_info["id"]),
                "vertex_count": utils.count_cached_geojson_vertices(output)
            },
        )

    logging.info("[ckanext-opendatatoronto] --- Finished Datastore Cache")
    return output


@tk.chained_action
def datastore_create_hook(original_datastore_create, context, data_dict):
    """This logic fires on "/datastore_create" which is called whenever records
    are inserted into the datastore

    When this endpoint is hit, this logic ensures the datastore resource
    will be cached

    In other words, it is put into the datastore *and* copied into multiple
    formats into the filestore
    """

    # make sure an authorized user is making this call
    logging.info("[ckanext-opendatatoronto]------------ Checking Auth")
    tk.check_access("datastore_create", context, data_dict)
    if not context["auth_user_obj"]:
        raise tk.NotAuthorized("Not authorized to create datastore records")
    logging.info("[ckanext-opendatatoronto]------------ Done Checking Auth")
    # 2000 and 20000 are hardcoded "chunk" sizes
    # ETLs from NiFi send data in multiple "chunks"
    # We dont want to hit the /datastore_cache for each chunk,
    # just the last chunk
    # The last "chunk" wont be 2000 or 20000 records in size

    # We also have an optional "do not cache" input for datastore_create
    # if this is marked, caching wont occur after a final chunk

    if "records" not in data_dict.keys():
        numrecords = 0
    else:
        numrecords = len(data_dict["records"])
    logging.info(
        "=============================== STARTING LOAD OF {} RECORDS".format(
            str(numrecords)
        )
    )
    output = original_datastore_create(context, data_dict)
    logging.info(
        "[ckanext-opendatatoronto]=== LOADED {} RECORDS".format(str(numrecords))
    )
    if numrecords not in [2000, 1999, 20000, 19999, 0] and not data_dict.get(
        "do_not_cache", False
    ):

        context.pop("model")
        context.pop("session")
        context.pop("connection")

        # tk.enqueue_job(
        #    fn=datastore_cache_job,
        #    args=[
        #        context,
        #        output["resource_id"],
        #    ],
        #    title="cache_job - " + output["resource_id"],
        #    rq_kwargs={"timeout":3600}
        #    #title=output["resource_id"]+"_datastore_cache_job",
        #    #timeout=3600
        # )
        tk.get_action("datastore_cache")(
            context, {"resource_id": output["resource_id"]}
        )
    logging.info(
        "[ckanext-opendatatoronto]------------ Done Checking If ready for Datastore Cache"
    )

    return output


def datastore_cache_job(context, resource_id):
    """Calls datastore_cache CKAN action"""

    tk.get_action("datastore_cache")(context, {"resource_id": resource_id})


@tk.chained_action
def datastore_delete_hook(original_datastore_delete, context, data_dict):
    """This logic fires on "/datastore_delete" which is called whenever records
    are deleted from the datastore

    When this endpoint is hit, this logic ensures critical values from the tags
    package are not deleted.

    If these values are deleted, datasets will not be able to get updates
    """

    # make sure an authorized user is making this call
    logging.info("------------ Checking Auth")
    tk.check_access("datastore_delete", context, data_dict)
    assert context[
        "auth_user_obj"
    ], "This endpoint can be used by authorized accounts only"
    logging.info("------------ Done Checking Auth")

    # checking if this targets the metadata-catalog package
    metadata_catalog_package = tk.get_action("package_show")(
        context, {"id": "metadata-catalog"}
    )
    metadata_catalog_resources = {
        r["id"]: r["name"]
        for r in metadata_catalog_package["resources"]
        if r["datastore_active"] in [True, "True", "true"]
    }
    # if it does, make sure it doesnt target important metadata-catalog
    if data_dict["id"] in metadata_catalog_resources.keys():
        if metadata_catalog_resources[data_dict["id"]] in [
            "Owner Division",
            "Refresh Rate",
            "Dataset Category",
        ]:
            # if we delete important metadata-catalog, ensure we dont delete all values
            if "filters" not in data_dict.keys():
                raise tk.ValidationError(
                    {
                        "constraints": [
                            "Not allowed to bulk delete from {}".format(
                                metadata_catalog_resources[data_dict["id"]]
                            )
                        ]
                    }
                )

            # make sure we dont delete values belonging to the metadata-catalog package
            elif "filters" in data_dict.keys():
                metadata_catalog_metadata = [
                    metadata_catalog_package["owner_division"],
                    metadata_catalog_package["refresh_rate"],
                    metadata_catalog_package["dataset_category"],
                ]

                incoming_deletes = data_dict["filters"].values()

                matches = set(metadata_catalog_metadata) & set(incoming_deletes)

                if matches:
                    raise tk.ValidationError(
                        {
                            "constraints": [
                                "Not allowed to delete tag {}".format(str(matches))
                            ]
                        }
                    )

    original_datastore_delete(context, data_dict)
