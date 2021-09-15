from datetime import datetime

from ckan.logic import ValidationError

from . import constants, utils

import ckan.plugins.toolkit as tk


def build_query(query):
    """
        Parses parameters from frontend search inputs to respective CKAN fields
        and SOLR queries with logic.

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

            """
            if f in ["dataset_category", "formats"]:      # join dataset_category and vocab_formats as vars, not strings, to "terms"
                terms = " AND ".join(["{x}".format(x=term) for term in v])
            elif f in [                                         # other terms in list below are added as strings to "terms"
                "owner_division",
                "refresh_rate",
                "topics",
                "civic_issues",
                "custom_attribute_test_id"  # this is a test attribute put in to see if scheming works with this extension - it does
                                            # to get scheming and extendedapi to work together, add a custom attribute to a datasets schema
                                            # add that custom attribute to a query_packages call's params, but make sure its name ends in [] in the call
                                            # add that custom attributes name to the array above, like "custom_attribute_test_id"
                                            # restart ckan, make the api call, and see only packages w/ a value that matches the one in your api call returned
                
            ]:
                terms = " AND ".join(['"{x}"'.format(x=term) for term in v])
            else:                                               # words not in this list are not added to the "terms"
                continue
            """
            
            terms = " AND ".join(["{x}".format(x=term.replace("vocab_", "")) for term in v]) # remove any vocab_ prefix from values
            q.append("{key}:*({value})*".format(key=f, value=terms)) # the cleaned up key, and the AND-delineated "terms" string, are appended to this functions output
        
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

    count = tk.get_action("datastore_info")(context, {"id": resource_id})["meta"][
        "count"
    ]

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
    print("======================search_facets start=================================================")

    q = build_query(data_dict)

    print(data_dict)
    print(q)
    print( " AND ".join(["({x})".format(x=x) for x in q]) )
    print(utils.to_list(data_dict["facet_field[]"]))
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
    print(output)

    
    print("======================search_facets end=================================================")

    return output


@tk.side_effect_free
def query_packages(context, data_dict):
    print("=======================query_packages_start================================================")
    print(data_dict)
    print("=======================query_packages================================================")
    q = build_query(data_dict)
    print("=======================query_packages================================================")
    print(q)
    print("=======================query_packages================================================")

    params = constants.CATALOGUE_SEARCH.copy()                          # {"rows": 10, "sort": "score desc", "start": 0}
    params.update(data_dict)

    print("========================query_packages===============================================")
    print(" AND ".join(["({x})".format(x=x) for x in q]))
    print("========================query_packages_end===============================================")

    return tk.get_action("package_search")(
        context,
        {
            "q": " AND ".join(["({x})".format(x=x) for x in q]),        # solr query
            "rows": params["rows"],                                     
            "sort": params["sort"],                                     # this is solr specific
            "start": params["start"],                                   # since its 0: start the returned dataset at the first record
        },
    )
