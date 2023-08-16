"""'Logic for multiple Open Data Toronto-specific CKAN actions"""

from ckan.logic import ValidationError
import ckan.plugins.toolkit as tk
from werkzeug.datastructures import FileStorage

from . import utils
from datetime import datetime

import os
import io
import logging


def build_query(query):
    """
    Takes inputs to api calls
    maps those inputs to respective CKAN fields
    and SOLR queries and returns a valid query

    Args:
        query: Content passed from the API call from the frontend

    Returns:
        list: SOLR search params
    """
    q = []

    for k, v in query.items():  # For items in the input API call's params...
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
            q.append(this)  # remove any vocab_ prefix from values

        elif (
            k == "search"
        ):  # When a key is "search" (when searching with opentext search bar)
            for w in v.lower().split(
                " "
            ):  # split the input by spaces, add solr syntax, add to output
                q.append(
                    "(name:(*{0}*))^5.0 OR "
                    "(tags:(*{1}*))^5.0 OR "
                    '(notes:("{1}")) OR '
                    "(title:(*{1}*))^10.0".format(w.replace(" ", "-"), w)
                )

    return q


@tk.side_effect_free
def get_quality_score(context, data_dict):
    """Receives package_id as input
    returns associated data quality score from catalog"""
    pid = data_dict.get("package_id")
    rid = None

    if pid is None:
        raise ValidationError("Missing package ID")

    package = tk.get_action("package_show")(context, {
        "id": "catalogue-quality-scores"
        }
    )

    for r in package["resources"]:
        if r["name"] == "catalogue-scorecard":
            rid = r["id"]
            break

    if rid is not None:
        return tk.get_action("datastore_search")(
            context,
            {
                "resource_id": rid,
                "q": {"package": pid},
                "sort": "recorded_at desc"
            },
        )["records"]


@tk.side_effect_free
def query_facet(context, data_dict):
    """runs package_search API call with input parameters
    This is triggered in the UI when someone clicks on a Dataset Filter
    This returns the appearance of the filter panel on the left side
    of open.toronto.ca intelligently
    """

    q = build_query(data_dict)

    output = tk.get_action("package_search")(
        context,
        {
            "q": " AND ".join(["({x})".format(x=x) for x in q]),  # solr query
            "rows": 0,  # max number of rows shown - presumably 0 is maximum
            "facet": "on",  # whether to enable faceted results
            "facet.limit": -1,  # vals a facet field can return. -1 = infinity
            "facet.field": utils.to_list(
                data_dict["facet_field[]"]
            ),  # fields to facet on - usually a list of all dataset filters
        },
    )

    # for the "multiple_" metadata attrs in the package schema, clean output
    for facet in "topics", "civic_issues", "formats":
        output["search_facets"][facet]["items"] = utils.unstringify(
            output["search_facets"][facet]["items"]
        )
    return output


@tk.side_effect_free
def query_packages(context, data_dict):
    """Used by the catalog page to determine which packages should be listed
    It receives inputs from filters or search terms users have selected
    on the catalog page, then returns the correct CKAN packages"""

    q = build_query(data_dict)
    params = {"rows": 10, "sort": "score desc", "start": 0}
    params.update(data_dict)

    output = tk.get_action("package_search")(
        context,
        {
            "q": " AND ".join(["({x})".format(x=x) for x in q]),  # solr query
            "rows": params["rows"],
            "sort": params["sort"],  # this is solr specific
            "start": params[
                "start"
            ],  # since its 0: start the returned dataset at the first record
        },
    )

    return output


@tk.side_effect_free
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
        raise tk.ValidationError(
            {"constraints": ["This endpoint can be used by authorized accounts only"]}
        )

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
    logging.info("[ckanext-opendatatoronto]----------- Looking for resource id in data_dict")
    if "resource_id" in data_dict.keys() and "package_id" not in data_dict.keys():
        resource = tk.get_action("resource_show")(
            context, {"id": data_dict["resource_id"]}
        )
        package = tk.get_action("package_show")(context, {
            "id": resource["package_id"]
            }
        )
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

    # for each resource id in your list...
    for resource_info in package_summary["resources"]:
        # init output
        output = {}

        # find out if resource is spatial
        # if it is, we need to create 2 files per file format for each CRS
        logging.info("[ckanext-opendatatoronto]--------- checking if spatial")
        is_geospatial = utils.is_geospatial(resource_info["id"])

        # create df of gdf for
        # df = downloads._prepare_df(resource_info["id"], is_geospatial)

        # run iotrans wrapper on (g)df for each file + EPSG combination
        # if this is spatial, we'll need to repeat the stuff below for
        # EPSG codes 4326 and 2952 in spatial formats
        if is_geospatial:
            target_formats = ["csv", "shp", "gpkg", "geojson"]
            for format in target_formats:
                output[format.upper()] = {}

            logging.info("[ckanext-opendatatoronto]=========================== CONVERTING Spatial FILE")
            logging.info(resource_info)

            cached_files = tk.get_action("to_file")(
                context,
                {
                    "resource_id": resource_info["id"],
                    "source_epsg": 4326,
                    "target_epsgs": [4326, 2952],
                    "target_formats": target_formats,
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
                    logging.info("[ckanext-opendatatoronto]--------------- " + format + " " + epsg_code)

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
                except Exception as e:                    
                    
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
        elif not is_geospatial:
            target_formats = ["csv", "xml", "json"]
            for format in target_formats:
                output[format.upper()] = {}

            logging.info("[ckanext-opendatatoronto]---------- CONVERTING Non Spatial FILE")
            logging.info("[ckanext-opendatatoronto]-------------- " + format)
            cached_files = tk.get_action("to_file")(
                context,
                {
                    "resource_id": resource_info["id"],
                    "target_formats": target_formats,
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
                    f.close()

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

        # put array of filepaths into package_patch call
        # and current date into resource_patch call
        tk.get_action("resource_patch")(
            context,
            {
                "id": resource_info["id"],
                "datastore_cache": output,
                "datastore_cache_last_update": datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S.%f"
                ),
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
    assert context[
        "auth_user_obj"
    ], "This endpoint can be used by authorized accounts only"
    logging.info("[ckanext-opendatatoronto]------------ Done Checking Auth")
    # 2000 and 20000 are hardcoded "chunk" sizes
    # ETLs from NiFi send data in multiple "chunks"
    # We dont want to hit the /datastore_cache for each chunk,
    # just the last chunk
    # The last "chunk" wont be 2000 or 20000 records in size

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
    logging.info("[ckanext-opendatatoronto]=== LOADED {} RECORDS".format(str(numrecords)))
    if numrecords not in [2000, 1999, 20000, 19999, 0]:

        context.pop("model")
        context.pop("session")
        context.pop("connection")
        
        tk.enqueue_job(
            fn=datastore_cache_job, 
            args=[
                context,
                output["resource_id"],
            ], 
            title="cache_job - " + output["resource_id"],
            rq_kwargs={"timeout":3600}
            #title=output["resource_id"]+"_datastore_cache_job",
            #timeout=3600
        )
        #tk.get_action("datastore_cache")(
        #    context, {"resource_id": output["resource_id"]}
        #)
    logging.info("[ckanext-opendatatoronto]------------ Done Checking If ready for Datastore Cache")

    return output

def datastore_cache_job(context, resource_id):
    """Calls datastore_cache CKAN action"""

    tk.get_action("datastore_cache")(
        context,
        {"resource_id": resource_id}
    )

@tk.chained_action
def datastore_delete_hook(original_datastore_delete, context, data_dict):
    """This logic fires on "/datastore_delete" which is called whenever records
    are deleted from the datastore

    When this endpoint is hit, this logic ensures critical values from the tags
    package are not deleted.

    If these values are deleted, datasets will not be able to get updates
    """

    # make sure an authorized user is making this call
    logging.info("[ckanext-opendatatoronto]------------ Checking Auth")
    tk.check_access("datastore_delete", context, data_dict)
    assert context[
        "auth_user_obj"
    ], "This endpoint can be used by authorized accounts only"
    logging.info("[ckanext-opendatatoronto]------------ Done Checking Auth")

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


@tk.side_effect_free
def reindex_solr(context, data_dict):
    """Endpoint to force a reindex of solr in the target environment
    This wont cause a reindex in an associated delivery environment, though
    The solr-sqs package is responsible for that
    """
    # make sure an authorized user is making this call
    assert context[
        "auth_user_obj"
    ], "This endpoint can be used by authorized accounts only"

    os.system(
        """
        . /usr/lib/ckan/default/bin/activate
        ckan --config=/etc/ckan/default/production.ini search-index rebuild -r
    """
    )
    return "Complete"
