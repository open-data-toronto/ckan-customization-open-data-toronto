from ckan.lib.navl.dictization_functions import missing
from datetime import datetime

import ckan.plugins.toolkit as tk
import mimetypes
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


def to_list(l):
    if not isinstance(l, list):
        return [l]
    else:
        # If the item is already a list from wordpress, it 
        # may have "vocab_" as an unnecessary prefix to certain 
        # values, specifically when running extendedapi's /search_facets
        return [item.replace("vocab_", "") if item.startswith("vocab_") else item for item in l]


def validate_length(key, data, errors, context):
    max_length = 350
    if data[key] and len(data[key]) > max_length:
        raise tk.ValidationError(
            {
                "constraints": [
                    "Input exceed {0} character limit".format(
                        max_length
                    )
                ]
            }
        )

    return data[key]


def validate_tag_in_vocab(tag, vocab):
    try:
        tk.get_action("tag_show")(None, {"id": tag, "vocabulary_id": vocab})
    except:
        raise tk.ValidationError(
            {"constraints": ["Tag {0} is not in the vocabulary {1}".format(tag, vocab)]}
        )


def unstringify(input):
    # inputs "items" dict of a search_facet ...
    # ... (it will hold arrays that solr turned into a string) ...
    # outputs a dict for use in /search_facet

    names = []
    terms = []
    output = []

    assert isinstance(input, list), "Input to unstringify is not a list, its {}".format(type(input))
    
    # for each dict in the input...
    for item in input:
        
        assert isinstance(item, dict), "Input list to unstringify does not contain dicts"
        assert "name" in item.keys(), "Input list's dict doesnt have a name attribute"
        assert "count" in item.keys(), "Input list's dict doesnt have a count attribute"

        # take the item out of its list, and put them in one big array
        
        if isinstance(item["name"], str):
            these_names = item["name"].replace("{", "").replace("}", "").replace('"', "").split(",") 
            names += these_names
            terms.append( {"names": these_names, "count": item["count"]} )

    # get the distinct terms and make an output dict structure for them
    for name in set(names):
        item = {
            "count": 0,
            "display_name": name,
            "name": name
        }
        # update the count attribute in the appropriate dict in the output dict
        for value in terms:
            if name in value["names"]:
                item["count"] += value["count"]
        
        output.append( item )
    
    return output


# Useful scheming validator functions
# ===
def choices_to_string(value):

    if isinstance(value, list):
        return ", ".join(value)
    elif isinstance(value, dict):
        return json.dumps(value)
    elif isinstance(value, str):
        return value.replace('\\', '').replace("[", "").replace("]", "").replace('\"', '').replace("{", "").replace("}", "")

def string_to_choices(value):
    if isinstance(value, str):
        return value.split(",")
    else:
        return value

def default_to_none(value):
    if value:
        return value

def default_to_false(value):
    if isinstance(value, string_types):
        return value.lower() == "true"

    return bool(value)

def default_to_today(value):
    # if we receive a valid datetime IS format string, parse it into an ISO format datetime object
    # if we receive a datetime, return it as is
    # if we return something else, return today as a datetime object
    
    if isinstance(value, str):
        return str_to_datetime(value)
        
    elif isinstance(value, datetime):
        return value
    else:
        return datetime.today()

def datastore_to_csv(resource_id, data, filepath):
    # In ckan <2.9.3, the lazyjson object only works as a normal dict when you take its 0th index
    
    with open("/usr/lib/ckan/default/src/ckanext-opendatatoronto/ckanext/opendata/" + resource_id + ".csv", "w") as file:
        writer = csv.writer(file)
        headers = data[0].keys()
        writer.writerow( headers )
        for row in data:
            assert row.keys() == headers
            writer.writerow(row.values())
    file.close()
    
def lazyjson_to_dict(lazyjson):
    output = []
    for item in lazyjson:
        output.append( item )
    return output

def str_to_datetime(input):
    # loops through the list of formats and tries to return an input string into a datetime of one of those formats
    assert isinstance(input, str), "Utils str_to_datetime() function can only receive strings - it instead received {}".format(type(input))
    for format in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]:
        try:
            output = datetime.strptime(input, format)
            return output
        except ValueError:
            pass
    print("No valid datetime format in utils.str_to_datetime() for input string {}".format(input))

def default_to_false(value):
    if value in [True, "true", "True", "TRUE"]:
        return True
    else:
        return False

def list_to_words(input):
    if isinstance(input,str):
        return input.split(" ")
    elif isinstance(input, list):
        output = []
        for item in input:
            for word in item.split(" "):
                output.append(word)
        return output

# gets catalog datastore resource as json object
def get_catalog():

    try:
        package = tk.get_action("package_show")(data_dict={"id": "od-etl-configs"})
        resource_id = package["resources"][0]["id"]
        output = tk.get_action("datastore_search")(data_dict={"resource_id": resource_id, "limit": 32000}) 
        output["url"] = package["resources"][0]["url"]
    except Exception as e:
        print("Couldnt access catalog page:\n" + str(e))
        output = {"records": [{"message": "Log in as an administrator to see the catalog's ETL details on this page"}]}

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
        "invalid_geospatial": "Geography in this dataset is invalid"
    }

    # we add special logic for periods_behind
    # map refresh_rate values to time period values
    rr_dict = {
        "daily": "days",
        "weekly": "weeks",
        "monthly": "months",
        "quarterly": "quarters",
        "semi-annually": "half-years",
        "annually": "years"
    }

    if "periods_behind" in input and "refresh_rate" in input:
        # get the number of periods behind
        periods_behind = int(float(re.search(
            r"periods_behind:([0-9\.]*)", input).group(1)))
        # get the designated refresh rate
        rr = re.search(r"refresh_rate:(.*?)[\~]", input).group(1)
        s = "This dataset is {} {} behind its refresh rate".format(
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

    return output


def get_dqs(input_package):

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
    datastore_resource = tk.get_action("quality_show")(data_dict={"package_id": input_package["name"]})

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
        dimensions += ["usability", "completeness"]


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