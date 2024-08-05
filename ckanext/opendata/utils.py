from datetime import datetime
import ckan.plugins.toolkit as tk
import json
import csv
import re
import codecs


def string_to_hex(s):
    return codecs.encode(s.encode("utf-8"), "hex")


def hex_to_string(s):
    return codecs.decode(s, "hex").decode("utf-8")


def is_geospatial(resource_id):
    info = tk.get_action("datastore_info")(None, {"id": resource_id})

    return "geometry" in info["schema"]


def to_list(input):
    if not isinstance(input, list):
        return [input]
    else:
        # If the item is already a list from wordpress, it
        # may have "vocab_" as an unnecessary prefix to certain
        # values, specifically when running extendedapi's /search_facets
        return [item.replace("vocab_", "") if item.startswith("vocab_") else item for item in input]


def validate_length(key, data, errors, context):
    max_length = 350
    if data[key] and len(data[key]) > max_length:
        raise tk.ValidationError(
            {"constraints": ["Input exceed {0} character limit".format(max_length)]}
        )

    return data[key]


def unstringify(input):
    # inputs "items" dict of a search_facet ...
    # ... (it will hold arrays that solr turned into a string) ...
    # outputs a dict for use in /search_facet

    names = []
    terms = []
    output = []

    assert isinstance(input, list), "Input to unstringify is not a list, its {}".format(
        type(input)
    )

    # for each dict in the input...
    for item in input:
        assert isinstance(
            item, dict
        ), "Input list to unstringify does not contain dicts"
        assert "name" in item.keys(), "Input list's dict doesnt have a name attribute"
        assert "count" in item.keys(), "Input list's dict doesnt have a count attribute"

        # take the item out of its list, and put them in one big array

        if isinstance(item["name"], str):
            these_names = (
                item["name"]
                .replace("{", "")
                .replace("}", "")
                .replace('"', "")
                .split(",")
            )
            names += these_names
            terms.append({"names": these_names, "count": item["count"]})

    # get the distinct terms and make an output dict structure for them
    for name in set(names):
        item = {"count": 0, "display_name": name, "name": name}
        # update the count attribute in the appropriate dict in the output dict
        for value in terms:
            if name in value["names"]:
                item["count"] += value["count"]

        output.append(item)

    return output


# Useful scheming validator functions
# ===
def choices_to_string(value):
    if isinstance(value, list):
        return ", ".join(value)
    elif isinstance(value, dict):
        return json.dumps(value)
    elif isinstance(value, str):
        return (
            value.replace("\\", "")
            .replace("[", "")
            .replace("]", "")
            .replace('"', "")
            .replace("{", "")
            .replace("}", "")
        )


def string_to_choices(value):
    if isinstance(value, str):
        return value.split(",")
    else:
        return value


def default_to_none(value):
    if value:
        return value


def default_to_false(value):
    if isinstance(value, str):
        return value.lower() == "true"

    return bool(value)


def default_to_today(value):
    # if we receive a valid datetime IS format string, parse it into 
    # an ISO format datetime object
    # if we receive a datetime, return it as is
    # if we return something else, return today as a datetime object

    if isinstance(value, str):
        return str_to_datetime(value)

    elif isinstance(value, datetime):
        return value
    else:
        return datetime.today()


def datastore_to_csv(resource_id, data, filepath):
    # In ckan <2.9.3, the lazyjson object only works as a normal dict
    # when you take its 0th index

    with open(
        "/usr/lib/ckan/default/src/ckanext-opendatatoronto/ckanext/opendata/"
        + resource_id
        + ".csv",
        "w",
    ) as file:
        writer = csv.writer(file)
        headers = data[0].keys()
        writer.writerow(headers)
        for row in data:
            assert row.keys() == headers
            writer.writerow(row.values())
    file.close()


def lazyjson_to_dict(lazyjson):
    output = []
    for item in lazyjson:
        output.append(item)
    return output


def str_to_datetime(input):
    # loops through the list of formats and tries to return an input
    # string into a datetime of one of those formats
    assert isinstance(
        input, str
    ), "str_to_datetime() input should be string - it received {}".format(
        type(input)
    )
    for format in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            output = datetime.strptime(input, format)
            return output
        except ValueError:
            pass
    print(
        "No valid datetime format in utils.str_to_datetime() for input string {}".format(
            input
        )
    )


def list_to_words(input):
    if isinstance(input, str):
        return input.split(" ")
    elif isinstance(input, list):
        output = []
        for item in input:
            for word in item.split(" "):
                output.append(word)
        return output


def get_catalog():
    """gets catalog datastore resource as json object"""

    try:
        package = tk.get_action("package_show")(data_dict={"id": "od-etl-configs"})
        resource_id = package["resources"][0]["id"]
        output = tk.get_action("datastore_search")(
            data_dict={"resource_id": resource_id, "limit": 32000}
        )
        output["url"] = package["resources"][0]["url"]
    except Exception as e:
        print("Couldnt access catalog page:\n" + str(e))
        output = {
            "records": [
                {
                    "message": "Log in as an admin to see catalog ETL details"
                }
            ]
        }

    return output


def parse_dqs_codes(input):
    '''takes a tilde (~) separated string containing dqs codes
    and parses it into meaningful descriptions in an array'''

    output = {}
    # init translation dict
    code_dict = {
        "colnames_unclear": "Column names are not composed of clear english words", 
        "constant_cols": "The following column(s) contain constant values:",
        "metadata_missing": "The following metadata field(s) are empty:", 
        "owner_is_opendata": "This dataset's owner is marked as opendata@toronto.ca, when there may be a better contact email", 
        "bad_info_url": "The url where users can get more information about this data is broken", 
        "all_data_def_missing": "There are no column definitions in this dataset", 
        "missing_def_cols": "The following column definitions are empty:", 
        #"periods_behind": "The dataset is not being refreshed at its designated refresh rate.", 
        "stale": "This dataset has not been updated in over 2 years", 
        "significant_missing_data": "A significant amount of data is null in this dataset", 
        "no_pipeline_found": "This dataset is updated by hand", 
        "no_tags": "This dataset hasn't been associated with any additional, searchable keywords", 
        "invalid_geospatial": "Geography in this dataset is invalid",
        "filestore_resource": "This data is saved in a file instead of in the Open Data database"
    }

    # we add special logic for periods_behind
    # map refresh_rate values to time period values
    rr_dict = {
        "daily": "day(s)",
        "weekly": "week(s)",
        "bi-weekly": "week(s)",
        "monthly": "month(s)",
        "quarterly": "quarter(s)",
        "semi-annually": "half-year(s)",
        "annually": "year(s)"
    }

    if "periods_behind" in input and "refresh_rate" in input:
        # get the number of periods behind
        periods_behind = int(float(re.search(
            r"periods_behind:([0-9\.]*)", input).group(1)))

        rr = re.search(r"refresh_rate:(.*?)[\~]", input).group(1)

        # create the descriptive text for the periods behind
        if periods_behind < 1:
            s = "This dataset is almost 1 {} behind its refresh rate".format(
                rr_dict[rr]
            )

        else:
            s = "This dataset is over {} {} behind its refresh rate".format(
                periods_behind, rr_dict[rr]
            )
        
        output[s] = []


    codes = input.split("~")

    for code in codes:
        main_code = code.split(":")[0]
        for lookup in code_dict.keys():
            # if an input code matches the dict, add it to output
            if code.startswith(lookup):
                if code_dict[main_code] not in output.keys():
                    output[code_dict[main_code]] = []
                # if code containts ':', it has more details
                # we want to add those details to the output too
                if ":" in code:
                    subcodes = code.split(":")[-1].split(",")
                    for subcode in subcodes:
                        output[code_dict[main_code]].append(subcode)

    # remove duplicate explanation code details    
    for k,v in output.items():
            output[k] = set(v)

    return output


def get_dqs(input_package, input_resource):

    # initialize descriptions for output
    descriptions = {
        "usability": {"definition": "How easy is it to work with the data?", 
                      "metrics": [
                        "Do columns have meaningful, English names?",
                        "Do any columns have a single, constant value?"
                      ]},
        "metadata": {"definition": "Is the data well described?", 
                      "metrics": [
                        "Are there metadata missing from the dataset?",
                        "Is the dataset associated with a placeholder email, like opendata@toronto.ca?",
                        "Is the 'Learn More' URL a broken link?",
                        "Are data definitions missing?",
                      ]},
        "freshness": {"definition": "Is the dataset up-to-date?", 
                      "metrics": [
                        "Is the dataset not being refreshed on schedule (if it has a refresh rate)?",
                        "Has the data not been updated in over 2 years?"
                      ]},
        "completeness": {"definition": "Is there lots of missing data?", 
                      "metrics": [
                        "Are more than half of the values in this dataset null?"
                      ]},
        "accessibility": {"definition": "Is the data easy to access for different kinds of users?", 
                      "metrics": [
                        "Are there any tags/keywords on the dataset?",
                        "Is this dataset updated manually by the Open Data team?",
                        "Is the data stored as a file instead of a database table?",
                      ]},
    }

    # get DQS values from CKAN for this package    
    datastore_resources = tk.get_action("quality_show")(data_dict={"package_id": input_package["name"]})

    # if there's no DQS for this package, return empty list
    if len(datastore_resources) == 0:
         return [] 
	    
    datastore_resource = [r for r in datastore_resources if r["resource"] == input_resource["name"]]

    # if there's no DQS for this resource, return empty list
    if len(datastore_resource) == 0:
         return [] 
    
    # parse DQS values
    max_date = max(datetime.strptime(x["recorded_at"], "%Y-%m-%dT%H:%M:%S") for x in datastore_resource)
    records = [r for r in datastore_resource if r["recorded_at"] == max_date.strftime("%Y-%m-%dT%H:%M:%S")]
    
    # init output with overall scores
    output = {
        "dimensions": {},
        "overall": {
            "last refreshed": max_date.strftime("%Y-%m-%dT%H:%M:%S")[:10],
            "overall score": str(int(float(records[0]["score"])*100))+"%",
            "grade": records[0]["grade"],
        }
    }

    # populate output with dimension-specific scores
    # filestore resources only get 3 dimensions, datastore get all 5

    store_type = "datastore" if any([r for r in datastore_resource if r["store_type"]=="datastore"]) else "filestore"
    dimensions = ["freshness", "metadata", "accessibility"]
    if store_type == "datastore":
        dimensions += ["completeness","usability"]


    for dimension in dimensions:
        mean_score = sum(r[dimension] for r in records) / len(records)
        codes = "~".join([r[dimension+"_code"] for r in records])
        output["dimensions"][dimension] = {
            "score": str(int(100*mean_score))+"%",
            "codes": parse_dqs_codes(codes),
            "description": descriptions[dimension]["definition"],
            "metrics": descriptions[dimension]["metrics"],
        }
    
    return output


def get_non_empty_var(input_dict, var1, var2):
     assert isinstance(input_dict, dict)
     assert isinstance(var1, str)
     assert isinstance(var2, str)
 
     if not input_dict[var1]:
         return input_dict[var2]
     else:
	         return input_dict[var1]


def detail_intake(intake):
    """Presents details of ticket group to be rendered on the frontend.
    Attribute of output include:
    - Most recent update date
    - Jira Ticket IDs
    - Inquiry Source
    - Request Type(s)
    - Ticket Group Name
    - Ordered list of milestones (dicts)
    
    Each milestone will have the following attributes:
    - title
    - timestamp
    - subtext
    - activity_state (done, active, future)
    """

    assert isinstance(intake, list), f"Input must be a list of dicts!"
    assert len(intake), f"Input must be populated!"

    # Let's make high level info for this ticket group
    last_update = datetime.strptime("1000-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    start_date = datetime.strptime("1000-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    jira_ticket_ids = []
    inquiry_source = []
    request_types = []
    to_statuses = []
    from_statuses = []
    
    for rec in intake:
        ticket_group_name = rec["Ticket Name"]

        # last update
        if datetime.strptime(get_non_empty_var(rec, "Status Timestamp", "Created"), "%Y-%m-%dT%H:%M:%S") > last_update:
            last_update = datetime.strptime(get_non_empty_var(rec, "Status Timestamp", "Created"), "%Y-%m-%dT%H:%M:%S")    
            latest_record = rec

        # start date
        if datetime.strptime(rec["Created"], "%Y-%m-%dT%H:%M:%S") < start_date:
            start_date = datetime.strptime(rec["Created"], "%Y-%m-%dT%H:%M:%S")

        # ticket ids
        if rec["Ticket Id"] not in jira_ticket_ids:
            jira_ticket_ids.append(rec["Ticket Id"])

        # inquiry source
        if rec["Inquiry Source"] not in inquiry_source:
            inquiry_source.append(rec["Inquiry Source"])

        # request_types
        if rec["Request Type"] not in request_types:
            request_types.append(rec["Request Type"])

        # to statuses
        if rec["To Status"] not in to_statuses:
            to_statuses.append(rec["To Status"])

        # from statuses
        if rec["From Status"] not in from_statuses:
            from_statuses.append(rec["From Status"])

    details = []
    
    # ticket history is presented in an order that is meant to be easy to understand
    # this history, then, has a set order. We show the history that fits this order
    # we do this to simplify the process for people consuming this info

    # first, here is the ideal order and content
    orders = [
        {
            "request_types": ["Make Open Data Inquiry"],
            "order": {
                "Identified": {"order":1, "title": "Inquiry Received", "text": "This inquiry is on the Open Data Team's list"},
                "Initiating": {"order":2, "title": "Initiating Inquiry", "text": "Open Data is searching for data owner(s) within the city to help address this inquiry"},
                "Exploring": {"order":3, "title": "Exploring Details", "text": "Data owners have been identified, and technical details and feasibility concerns are being explored"},
                #"Waiting on Division": {"order":4, "title": "", "text": "Data "},
                "Closed": {"order":5, "title": "Inquiry Concluded", "text": "Investigations here have finished. If there are no additional details here, no further actions are being taken by City staff"}
            }
        },
        {
            "request_types": ["Update Existing Open Dataset Page", "Publish New Open Dataset Page"],
            "order": {
                "Waiting on Open Data": {"order":6, "title": "Waiting on Open Data", "text": "The Open Data Team has the configurations it needs to create/update this dataset but has not begun work"},
                "Waiting on Owner Division": {"order":7, "title": "Waiting on Owner Division", "text": "The Open Data Team needs more details from the data owners before work can continue"},
                "In Progress": {"order":8, "title": "Configuration In Progress", "text": "Open Data is configuring the process of loading this data into the open data portal"},
                "Staged for Review": {"order":9, "title": "Under Review", "text": "The dataset has been staged and is under review by city staff"},
                "Published": {"order":10, "title": "Published", "text": "This data has been published"},
                "Closed": {"order":10, "title": "Will not Action", "text": "There is no action that can be taken here, and so this work has concluded"},
                "Retired": {"order":10, "title": "Retired", "text": "This dataset has been retired"},
            }
        }
    ]


    # sort out the last ticket type
    latest_type = latest_record.get("Request Type")
    latest_status = latest_record.get("To Status", None)
    
    for order in orders:
        # for each status, we'll get all relevant ticket records and choose the earliest
        for order_status, order_detail in order["order"].items():
            detail = {
                "timestamp": datetime.strptime("9999-12-31T00:00:00", "%Y-%m-%dT%H:%M:%S"),
                "match": False
            }
            for i in range(len(intake)):
                rec = intake[i]
                # skip irrelevant tickets in this loop
                if rec["Request Type"] not in order["request_types"]:
                    continue
                
                # if we make a match and its the earliest timestamp, it will be included in the output
                if rec["To Status"] == order_status and detail["timestamp"] > datetime.strptime(get_non_empty_var(rec, "Status Timestamp", "Created"), "%Y-%m-%dT%H:%M:%S"):
                    detail = {
                        "title": order_detail["title"],
                        "timestamp": datetime.strptime(get_non_empty_var(rec, "Status Timestamp", "Created"), "%Y-%m-%dT%H:%M:%S"),
                        "text": order_detail["text"],
                        "activity_state": "done",
                        "order": order_detail["order"]
                    }
                
            # append the detail if there's been a match
            if detail.get("match", True) == True:
                details.append(detail)                

    # loop through details again to 
    #   make sure the final detail's state is "active"
    #   see if there are "future" states, that they are added
    #   special logic for final statuses to make sure only one is shown
    #   make sure no dates and orders of things are incorrect
    to_remove = []
    for i in range(len(details)):
        detail = details[i]

        # make sure orders and dates are correct
        if i+1 < len(details) and i != 0:
            # loop through all preceding details. If it has a later date than this one, delete the preceding one
            if details[i]["timestamp"] < details[i-1]["timestamp"]:
                to_remove.append(i-1)

        # if there's only a closed inquiry ticket, don't add future details
        if detail["order"] == 5 and len(request_types) == 1:
            break

        # add active state to last detail
        elif i+1 == len(details):            
            details[i]["activity_state"] = "active"

            # add future details
            for order in orders:
                for order_status, order_detail in order["order"].items():
                    if order_detail["order"] > detail["order"]:
                        if order_detail["order"] not in [10, 5]:
                            details.append({
                                "title": order_detail["title"],
                                "timestamp": None,
                                "text": order_detail["text"],
                                "activity_state": "future",
                                "order": order_detail["order"]
                            })
                        
                        # special logic for "final" future detail
                        elif order_detail["order"] == 10:
                            details.append({
                                "title": "Resolution",
                                "timestamp": None,
                                "text": "The resolution of this work can result in the publication, retirement, or update of an open dataset. It may, depending on circumstances, end in nothing actionable.",
                                "activity_state": "future",
                                "order": 10
                            })
                            break
    
    # remove problematic details
    for i in to_remove:
        details.pop(i)

    return  {
        "ticket_group_name": ticket_group_name,
        "last_update": last_update,
        "jira_ticket_ids": jira_ticket_ids,
        "inquiry_source": inquiry_source,
        "request_types": request_types,
        "to_statuses": to_statuses,
        "from_statuses": from_statuses,
        "details": details
    }