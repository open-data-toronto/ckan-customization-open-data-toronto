from datetime import datetime

from ckan.logic import ValidationError

from . import constants, utils, downloads

import ckan.plugins.toolkit as tk

import json, os, io, traceback, subprocess

from werkzeug.datastructures import FileStorage


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

    for k, v in query.items():                          # For everything in the input API call's parameters...
        if not len(v):                                      # ignore empty strings and non-strings
            continue

        if k.endswith("[]") and k != "facet_field[]":                                # If a key ends in [] ...
            f = k[:-2]                                          # remove [] at end of key names and turn the values into a list
            if f.startswith("vocab_"):                          # if there is a vocab_ prefix in the key name, remove that too
                f = f[6:]    
            v = utils.to_list(v)
            
            terms = " AND ".join(['*"{x}"*'.format(x=term.replace("vocab_", "")) if " " in term else '*{x}*'.format(x=term.replace("vocab_", "")) for term in v]) # remove any vocab_ prefix from values
            q.append( "{f}: {terms}".format(f=f, terms=terms) ) # the cleaned up key, and the AND-delineated "terms" string, are appended to this functions output
        
        elif k == "search":                                 # When a key is "search" (this is when users enter terms into the opentext search bar) ...
            for w in v.lower().split(" "):                      # split the input by spaces and add it to the output with some solr query syntax on it
                q.append(
                    "(name:(*{0}*))^5.0 OR "
                    "(tags:(*{1}*))^5.0 OR"
                    '(notes:("{1}")) OR '
                    "(title:(*{1}*))^10.0".format(w.replace(" ", "-"), w)
                )

    return q


@tk.side_effect_free
def get_quality_score(context, data_dict):
    pid = data_dict.get("package_id")
    rid = None

    if pid is None:
        raise ValidationError("Missing package ID")

    package = tk.get_action("package_show")(
        context, {"id": constants.DQ.get("package")}
    )

    for r in package["resources"]:
        if r["name"] == constants.DQ.get("resource"):
            rid = r["id"]
            break

    if not rid is None:
        return tk.get_action("datastore_search")(
            context,
            {"resource_id": rid, "q": {"package": pid}, "sort": "recorded_at desc"},
        )["records"]


@tk.side_effect_free
def extract_info(context, data_dict):
    # returns summary statistics regarding a particular CKAN resource
    # the time this is called from the open.toronto.ca UI is unclear
    resource_id = data_dict.get("resource_id")

    if resource_id is None:
        raise ValidationError("Missing resource ID")

    count = tk.get_action("datastore_info")(context, {"id": resource_id})["meta"]["count"]

    dt = tk.get_action("resource_show")(context, {"id": resource_id})["last_modified"]
    d = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f").date()

    return {
        "rows": count,
        "updated_at": dt,
        "updated_today": d == datetime.today().date(),
    }


@tk.side_effect_free
def query_facet(context, data_dict):
    # runs package_search API call with input parameters
    # this is triggered in the UI when someone clicks on a Dataset Filter
    # this returns the appearance of the filter panel on the left side of open.toronto.ca intelligently

    q = build_query(data_dict)

    output = tk.get_action("package_search")(
        context,
        {
            "q": " AND ".join(["({x})".format(x=x) for x in q]),        # solr query
            "rows": 0,                                                  # max number of rows shown - presumably 0 is maximum
            "facet": "on",                                              # whether to enable faceted results
            "facet.limit": -1,                                          # number of values a facet field can return - negative is infinite
            "facet.field": utils.to_list(data_dict["facet_field[]"]),   # fields to facet on - this list typically includes a list of all the dataset filter names
        },
    )

    

    # for the "multiple_" metadata attributes in the package schema, clean their output
    for facet in "topics", "civic_issues", "formats":
        output["search_facets"][facet]["items"] = utils.unstringify( output["search_facets"][facet]["items"] )
    return output


@tk.side_effect_free
def query_packages(context, data_dict):

    q = build_query(data_dict) 
    params = constants.CATALOGUE_SEARCH.copy()                          # {"rows": 10, "sort": "score desc", "start": 0}
    params.update(data_dict)
    print("Query Packages Query: {}".format( q ))
    print(" AND ".join(["{x}".format(x=x) for x in q]))
    output = tk.get_action("package_search")(
        context,
        {
            "q": " AND ".join(["{x}".format(x=x) for x in q]),        # solr query
            "rows": params["rows"],                                     
            "sort": params["sort"],                                     # this is solr specific
            "start": params["start"],                                   # since its 0: start the returned dataset at the first record
        },
    )

    return output

#@tk.chained_action
@tk.side_effect_free
def datastore_cache(context, data_dict):
    # init some params we'll need later
    url_base = "/usr/lib/ckan/default/src/ckanext-opendatatoronto/ckanext/opendata"
    output = {}

    # make sure an authorized user is making this call
    assert context["auth_user_obj"], "This endpoint can be used by authorized accounts only"

    # make sure the call has the necessary inputs
    assert "resource_id" in data_dict.keys() or "package_id" in data_dict.keys(), "This endpoint requires package_id or resource_id as an input"
    
    # if input param has package id, get all its resource ids that are datastore resources
    if "package_id" in data_dict.keys():
        package = tk.get_action("package_show")(context, {"id": data_dict["package_id"]})
        package_summary = {
            "package_id": package["name"], 
            "resources": [ {"id": resource["id"], "name": resource["name"]} for resource in package["resources"] if resource["datastore_active"] ]
        }

    # otherwise, use input param has resource id only
    if "resource_id" in data_dict.keys() and "package_id" not in data_dict.keys():
        resource = tk.get_action("resource_show")(context, {"id": data_dict["resource_id"]})
        package = tk.get_action("package_show")(context, {"id": resource["package_id"]})
        resource_id = resource["id"] if resource["datastore_active"] else None
        resource_name = resource["name"] if resource["datastore_active"] else None
        resource_dict = {"id": resource_id, "name": resource_name} if resource["datastore_active"] else None
        package_summary = {
            "package_id": package["name"],
            "resources": [ resource_dict ]
        }
        
    # for each resource id in your list...
    assert len(package_summary["resources"]) > 0, "Your inputs are not associated with any datastore resources"
    for resource_info in package_summary["resources"]:

        resource = tk.get_action("datastore_search")(context, {"id": resource_info["id"]})

        # is the datastore resource spatial? if it is, we need to create 2 files per type (for each CRS we use)
        spatial = utils.is_geospatial( resource_info["id"] )

        # if this is spatial, we'll need to repeat the stuff below for EPSG codes 4326 and 2945 in spatial formats
        if spatial:
            for format in constants.GEOSPATIAL_FORMATS:
                output[format] = {}
                for epsg_code in ["4326", "2945"]:
                    params = {"format": format, "projection": epsg_code}
                    filename, mimetype, response = downloads._write_datastore(params , resource_info, url_base + "/" + package_summary["package_id"])

                    try:
                        
                        filestore_resource = tk.get_action("resource_create")(context, {
                            "package_id": package_summary["package_id"], 
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True, 
                            "datastore_resource_id": resource_info["id"]
                        })
                    
                    except:
                        existing_resource = tk.get_action("resource_search")(context, {"query": "name:{}".format(filename)})
                        resource_id = existing_resource["results"][0]["id"]
                        filestore_resource = tk.get_action("resource_patch")(context, {
                            "id": resource_id, 
                            "mimetype": mimetype,
                            "upload": FileStorage(stream=response, filename=filename),
                            "name": filename,
                            "format": format,
                            "is_datastore_cache_file": True,
                            "datastore_resource_id": resource_info["id"] 
                        })
                                       
                    output[format][epsg_code] = filestore_resource["id"]

        # if its not spatial, we'll have different file formats, but no epsg codes to worry about
        elif not spatial:
            for format in constants.TABULAR_FORMATS:

                params = {"format": format}
                filename, mimetype, response = downloads._write_datastore(params , resource_info, url_base + "/" + package_summary["package_id"])

                try:
                    filestore_resource = tk.get_action("resource_create")(context, {
                        "package_id": package_summary["package_id"], 
                        "mimetype": mimetype,
                        "upload": FileStorage(stream=response, filename=filename),
                        "name": filename,
                        "format": format,
                        "is_datastore_cache_file": True,
                        "datastore_resource_id": resource_info["id"]
                    })
                except:
                    existing_resource = tk.get_action("resource_search")(context, {"query": "name:{}".format(filename)})
                    resource_id = existing_resource["results"][0]["id"]
                    filestore_resource = tk.get_action("resource_patch")(context, {
                        "id": resource_id, 
                        "mimetype": mimetype,
                        "upload": FileStorage(stream=response, filename=filename),
                        "name": filename,
                        "format": format,
                        "is_datastore_cache_file": True,
                        "datastore_resource_id": resource_info["id"] 
                    })
                
                output[format] = filestore_resource["id"] # put resource id for filestore resource#url_base + "/" + package_summary["package_id"] + "/" + filename 
                
        # put array of filepaths into package_patch call and current date into resource_patch call
        #tk.get_action("package_patch")(context, {"id": package_summary["package_id"], "datastore_cache": output })
        tk.get_action("resource_patch")(context, {"id": resource_info["id"], "datastore_cache": output, "datastore_cache_last_update": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f") })
    return output

@tk.chained_action
def datastore_create_hook(original_datastore_create, context, data_dict):
    # make sure an authorized user is making this call
    assert context["auth_user_obj"], "This endpoint can be used by authorized accounts only"

    numrecords = len(data_dict["records"])

    output = original_datastore_create(context, data_dict)
    
    if numrecords not in [2000, 20000]:
        tk.get_action("datastore_cache")(context, {"resource_id": output["resource_id"]})


@tk.side_effect_free
def reindex_solr(context, data_dict):
    # make sure an authorized user is making this call
    assert context["auth_user_obj"], "This endpoint can be used by authorized accounts only"

    os.system("""
        . /usr/lib/ckan/default/bin/activate
        ckan --config=/etc/ckan/default/production.ini search-index rebuild
    """)
    return "Complete"
    