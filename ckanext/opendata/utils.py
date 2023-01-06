from datetime import datetime
from . import constants

import ckan.plugins.toolkit as tk
import json


def is_geospatial(resource_id):
    """Determines whether input datastore resource is geospatial
    It does this by seeing whether it has a 'geometry' column"""
    info = tk.get_action("datastore_info")(None, {"id": resource_id})

    return "geometry" in info["schema"]


def to_list(input_list):
    """Returns input as list, removing 'vocab_' prefix if present
    vocab_ prefix is present in certain package metadata"""
    if not isinstance(input_list, list):
        return [input_list]
    else:
        # If the item is already a list from wordpress, it
        # may have "vocab_" as an unnecessary prefix to certain
        # values, specifically when running extendedapi's /search_facets
        return [
            item.replace("vocab_", "") if item.startswith("vocab_") else item
            for item in input_list
        ]


def validate_length(key, data, errors, context):
    """Throws an error if input is over a certain char count"""
    if data[key] and len(data[key]) > constants.MAX_FIELD_LENGTH:
        raise tk.ValidationError(
            {
                "constraints": [
                    "Input exceed {0} character limit".format(
                        constants.MAX_FIELD_LENGTH
                    )
                ]
            }
        )

    return data[key]


def unstringify(input):
    """inputs "items" dict of a search_facet
    (it will hold arrays that solr turned into a string)
    outputs a dict for use in /search_facet"""

    names = []
    terms = []
    output = []

    assert isinstance(input, list), "Input to unstringify is not a list, \
                                    its a {}".format(type(input))

    # for each dict in the input...
    for item in input:

        assert isinstance(
            item, dict
        ), "Input list to unstringify does not contain dicts"
        assert "name" in item.keys(), "Input list's dict missing 'name'"
        assert "count" in item.keys(), "Input list's dict missing 'count'"

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


def choices_to_string(value):
    """Returns input as a comma-delimited string"""

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
    """Returns input comma-delimited string as a list"""
    if isinstance(value, str):
        return value.split(",")
    else:
        return value


def default_to_none(value):
    """Returns None if no input is given"""
    if value:
        return value


def default_to_today(value):
    """if we receive a valid datetime IS format string, parse it into an ISO
    format datetime object
    if we receive a datetime, return it as is
    if we return something else, return today as a datetime object
    """

    if isinstance(value, str):
        return str_to_datetime(value)

    elif isinstance(value, datetime):
        return value
    else:
        return datetime.today()


def str_to_datetime(input):
    """loops through the list of formats and tries to return an input string
    into a datetime of one of those formats"""
    assert isinstance(
        input, str
    ), "str_to_datetime() can only receive strings - it received {}".format(
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
        "No valid datetime format in utils.str_to_datetime() \
            for input string {}".format(
            input
        )
    )


def default_to_false(value):
    """Returns boolean false unless some permutation of true is given"""
    if value in [True, "true", "True", "TRUE"]:
        return True
    else:
        return False


def list_to_words(input):
    """splits input by spaces, returns list"""
    if isinstance(input, str):
        return input.split(" ")
    elif isinstance(input, list):
        output = []
        for item in input:
            for word in item.split(" "):
                output.append(word)
        return output


def get_catalog():
    """ gets catalog datastore resource as json object"""

    try:
        package = tk.get_action("package_show")(data_dict={
            "id": "od-etl-configs"
        })
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
                    "message": "Only Admins can see catalog ETL details here"
                }
            ]
        }

    return output
