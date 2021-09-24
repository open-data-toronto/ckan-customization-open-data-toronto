from ckan.lib.navl.dictization_functions import missing
from datetime import datetime
from . import constants

import ckan.plugins.toolkit as tk
import mimetypes
import json

import codecs


def string_to_hex(s):
    return codecs.encode(s.encode("utf-8"), "hex")


def hex_to_string(s):
    return codecs.decode(s, "hex").decode("utf-8")


def get_mimetype(path):
    mimetype, encoding = mimetypes.guess_type(path)

    if mimetype is None:
        ext = path.split(".")[-1]

        if ext in constants.CUSTOM_MIMETYPES:
            return constants.CUSTOM_MIMETYPES[ext]

    return mimetype


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

    terms = []
    output = []

    assert isinstance(input, list), "Input to unstringify is not a list, its {}".format(type(input))
    
    # for each dict in the input...
    for item in input:
        
        assert isinstance(item, dict), "Input list to unstringify does not contain dicts"
        assert "name" in item.keys(), "Input list's dict doesnt have a name attribute"
        assert "count" in item.keys(), "Input list's dict doesnt have a count attribute"

        # take the item out of its list, and put them in one big array
        print(item)
        print(type(item))
        if isinstance(item["name"], str):
            these_items = item["name"].replace("{", "").replace("}", "").replace('"', "").split(",")
            print(these_items)
            terms += these_items 

    # get the distinct terms and make an output dict structure for them
    for term in set(terms):
        item = {
            "count": 0,
            "display_name": term,
            "name": term
        }
        # update the count attribute in the appropriate dict in the output dict
        for value in terms:
            if term == value:
                item["count"] += 1
        
        output.append( item )
    
    return output


# Useful scheming validator functions
# ===
def choices_to_string(value):
    print("===============================choices_to_string")
    print(value)
    print(type(value))
    if isinstance(value, list):
        print("converted!")
        return ", ".join(value)
    else:
        print("not converted!")
        return value.replace('\\', '').replace("[", "").replace("]", "").replace('\"', '').replace("{", "").replace("}", "")

def string_to_choices(value):
    print("==================================string_to_choices")
    if isinstance(value, str):
        print("converted!")
        return value.split(",")
    else:
        print("not converted!")
        return value

def default_to_none(value):
    if value:
        return value

def default_to_false(value):
    if isinstance(value, string_types):
        return value.lower() == "true"

    return bool(value)

def default_to_today(value):
    if type(value) != datetime:
        return datetime.today()