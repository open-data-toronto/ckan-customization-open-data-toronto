from ckan.lib.navl.dictization_functions import missing
from datetime import datetime

import ckan.plugins.toolkit as tk
import mimetypes
import json
import csv

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


def get_dqs(input_resource, input_package):

    # initialize descriptions for output
    descriptions = {
        "usability": "How easy is it to work with the data?",
        "metadata": "Is the data well described/contextualized?",
        "freshness": "Is the dataset up-to-date?",
        "completeness": "Is the significant amounts of missing data?",
        "accessibility": "Is the data easy to access for different kinds of users?",
    }
    package = tk.get_action("package_show")(data_dict={"id": "catalogue-quality-scores"})
    dqs_resource_id = [r["id"] for r in package["resources"] if r["name"] == "quality-scores-explanation-codes"][0]

    datastore_resource = tk.get_action("datastore_search")(
        data_dict=
        {
            "resource_id": dqs_resource_id, 
            "limit": 32000,
            "q": {"resource": input_resource["name"], "package": input_package["name"]}
        }
    )

    records = sorted(datastore_resource["records"], key=lambda x:datetime.strptime(x["recorded_at"], "%Y-%m-%dT%H:%M:%S"), reverse=True)[0]

    output = {}
    for dimension in ["usability", "metadata", "freshness", "completeness", "accessibility"]:
        output[dimension] = {
            "score": str(100*records[dimension])[:4]+"%",
            "code": records[dimension+"_code"],
            "icon": icons[dimension],
            "description": descriptions[dimension],
        }
    
    return output