import codecs
import csv
import requests
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from warnings import warn
import sqlalchemy as sa

import ckan.plugins.toolkit as tk
from ckan.common import config

from .types import SchemingSchema


def string_to_hex(s):
    return codecs.encode(s.encode("utf-8"), "hex")


def hex_to_string(s):
    return codecs.decode(s, "hex").decode("utf-8")


def is_geospatial(resource_id):
    info = tk.get_action("datastore_info")(None, {"id": resource_id})

    return "geometry" in [field["id"] for field in info["fields"]]


def to_list(input):
    if not isinstance(input, list):
        return [input]
    else:
        # If the item is already a list from wordpress, it
        # may have "vocab_" as an unnecessary prefix to certain
        # values, specifically when running extendedapi's /search_facets
        return [
            item.replace("vocab_", "") if item.startswith("vocab_") else item
            for item in input
        ]


def validate_length(key, data, errors, context):
    max_length = 350
    if data[key] and len(data[key]) > max_length:
        raise tk.ValidationError(
            {"constraints": ["Input exceed {0} character limit".format(max_length)]}
        )

    return data[key]


class Facet(TypedDict):
    name: str
    display_name: str
    count: int


class ListFacet(TypedDict):
    """ListFacet
    A type of facet counts where the values (`name`s) and labels (`display_name`s) are
    actually lists themselves.

    Typically downstream processing needs to occur before these are useful for the FE

    e.g. we're not that interested in how many records have exactly the topics:
    ```
    ["Health", "Public safety", "Something else"]
    ```
    in that order, but more typically want to flatten/aggregate/sum for 'Health',
    'Public safety' and 'Something else'.

    """

    name: List[str]
    display_name: List[str]
    count: int


def calculate_list_facets(values: List[ListFacet]) -> List[Facet]:
    """calculate_list_facets

    Process a list of facets where the values (`name`s) and labels (`display_name`s) are
    lists of values into a list of facets that are more consumable for the FE.

    E.g. Relevant for `topics`, `civic_issues`, and `formats` which are many <-> many
      with respect to datasets

    In this situation, facet counts need to be aggregated before being served to the FE.

    e.g, for `topics` as a facet:
    # One record has
    {name: ["Health", "Public safety"], count: 1, ...}
    # another maybe has
    {name: ["Health", "Somethin Else"], count: 2, ...}

    We need to aggregate (sum) the `Health` counts and produce something more useful for
    the FE:
    [
      # note the count = sum of the 2 above
      {name: "Health", count 3, ...}
      {name: "Somethin Else", count 2, ...}
    ]

    :param values: list of facets where each facet 'value' (`name`) is actually a list
      of values
    :type values: List[ListFacet]
    :return: _description_
    :rtype: List[ListFacet]
    """
    aggregated_facet_counts: Dict[str, ListFacet] = {}
    for facet in values:
        if isinstance(facet["name"], list):
            names = facet["name"]
        elif isinstance(facet["name"], str):
            try:
                # NOTE: this is not really the best place for this to be done. We are
                # incurring O(n) `json.loads` each call to search_facets.
                # This could (should) be done in `before_index` before solr indexes datasets
                # so that solr will return lists to begin with, as is advised here:
                #
                # https://github.com/ckan/ckanext-scheming/issues/195#issuecomment-421154311
                #
                # However, as noted in the link above, this requires changing `solr`'s
                # config which we don't have access to.
                names = json.loads(facet["name"])
            except json.JSONDecodeError as exc:
                warn(f"Could not parse as json: {exc}, this facet will not be counted")
                continue
        else:
            warn(
                f"Could not parse facet name: {facet['name']}, this facet will not be "
                "counted"
            )
            continue
        for name in names:
            if name not in aggregated_facet_counts:
                aggregated_facet_counts[name] = {
                    "name": name,
                    # NOTE: of consequence. the shape of the FacetCount type here makes
                    # it hard for us to find a `display_name` that corresponds with a
                    # given `name` (we'd have to do some fuzzy string-matching which is
                    # precarious).
                    # Chose to set to `name` because:
                    # - we're only using this for `topics`,`civic_issues`,`formats`
                    # - we've chosen to restrict these values such that their `value`s
                    #   are equivalent to their `label`s (see
                    #   `ckan opendatatoronto scheming-migration` CLI command which
                    #   performs this. It is otherwise enforced by scheming)
                    # - in this context, this means that `name` and `display_name`
                    #   should be equivalent anyway.
                    "display_name": name,
                    "count": 0,
                }
            aggregated_facet_counts[name]["count"] += facet["count"]

    return list(aggregated_facet_counts.values())


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
    ), "str_to_datetime() input should be string - it received {}".format(type(input))
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
        return output
    except tk.NotAuthorized:
        pass

    return None


def parse_dqs_codes(input):
    """takes a tilde (~) separated string containing dqs codes
    and parses it into meaningful descriptions in an array"""

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
        # "periods_behind": "The dataset is not being refreshed at its designated refresh rate.",
        "stale": "This dataset has not been updated in over 2 years",
        "significant_missing_data": "A significant amount of data is null in this dataset",
        "no_pipeline_found": "This dataset is updated by hand",
        "no_tags": "This dataset hasn't been associated with any additional, searchable keywords",
        "invalid_geospatial": "Geography in this dataset is invalid",
        "filestore_resource": "This data is saved in a file instead of in the Open Data database",
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
        "annually": "year(s)",
    }

    if "periods_behind" in input and "refresh_rate" in input:
        # get the number of periods behind
        periods_behind = int(
            float(re.search(r"periods_behind:([0-9\.]*)", input).group(1))
        )

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
    for k, v in output.items():
        output[k] = set(v)

    return output


def get_dqs(input_package, input_resource):

    # initialize descriptions for output
    descriptions = {
        "usability": {
            "definition": "How easy is it to work with the data?",
            "metrics": [
                "Do columns have meaningful, English names?",
                "Do any columns have a single, constant value?",
            ],
        },
        "metadata": {
            "definition": "Is the data well described?",
            "metrics": [
                "Are there metadata missing from the dataset?",
                "Is the dataset associated with a placeholder email, like opendata@toronto.ca?",
                "Is the 'Learn More' URL a broken link?",
                "Are data definitions missing?",
            ],
        },
        "freshness": {
            "definition": "Is the dataset up-to-date?",
            "metrics": [
                "Is the dataset not being refreshed on schedule (if it has a refresh rate)?",
                "Has the data not been updated in over 2 years?",
            ],
        },
        "completeness": {
            "definition": "Is there lots of missing data?",
            "metrics": ["Are more than half of the values in this dataset null?"],
        },
        "accessibility": {
            "definition": "Is the data easy to access for different kinds of users?",
            "metrics": [
                "Are there any tags/keywords on the dataset?",
                "Is this dataset updated manually by the Open Data team?",
                "Is the data stored as a file instead of a database table?",
            ],
        },
    }

    # get DQS values from CKAN for this package
    datastore_resources = tk.get_action("quality_show")(
        data_dict={"package_id": input_package["name"]}
    )

    # if there's no DQS for this package, return empty list
    if len(datastore_resources) == 0:
        return []

    datastore_resource = [
        r for r in datastore_resources if r["resource"] == input_resource["name"]
    ]

    # if there's no DQS for this resource, return empty list
    if len(datastore_resource) == 0:
        return []

    # parse DQS values
    max_date = max(
        datetime.strptime(x["recorded_at"], "%Y-%m-%dT%H:%M:%S")
        for x in datastore_resource
    )
    records = [
        r
        for r in datastore_resource
        if r["recorded_at"] == max_date.strftime("%Y-%m-%dT%H:%M:%S")
    ]

    # init output with overall scores
    output = {
        "dimensions": {},
        "overall": {
            "last refreshed": max_date.strftime("%Y-%m-%dT%H:%M:%S")[:10],
            "overall score": str(int(float(records[0]["score"]) * 100)) + "%",
            "grade": records[0]["grade"],
        },
    }

    # populate output with dimension-specific scores
    # filestore resources only get 3 dimensions, datastore get all 5

    store_type = (
        "datastore"
        if any([r for r in datastore_resource if r["store_type"] == "datastore"])
        else "filestore"
    )
    dimensions = ["freshness", "metadata", "accessibility"]
    if store_type == "datastore":
        dimensions += ["completeness", "usability"]

    for dimension in dimensions:
        mean_score = sum(r[dimension] for r in records) / len(records)
        codes = "~".join([r[dimension + "_code"] for r in records])
        output["dimensions"][dimension] = {
            "score": str(int(100 * mean_score)) + "%",
            "codes": parse_dqs_codes(codes),
            "description": descriptions[dimension]["definition"],
            "metrics": descriptions[dimension]["metrics"],
        }

    return output


def validate_schema(schema: Dict):
    SchemingSchema(**schema)


def to_bool(item: Any, default: Optional[bool] = None) -> bool:
    if isinstance(item, bool):
        return item
    elif isinstance(item, str):
        return item.lower() == "true"
    elif item is None:
        return False
    elif default is not None:
        return default

    raise ValueError(f"Could not parse {item} as a bool")


def count_cached_geojson_vertices(datastore_cache):
    geojson_ids = datastore_cache.get("GEOJSON", None)
    if geojson_ids:
        geojson_id = geojson_ids["4326"]

    if not geojson_id or not geojson_ids:
        return None

    resource = tk.get_action("resource_show")(data_dict={"id": geojson_id})
    raw = json.loads(requests.get((resource["url"])).text)
    return count_vertices(raw)


def count_vertices(raw_geojson):
  final_count = 0
  def counter(coords):
    count = 0
    # check if this element is a coord
    if isinstance(coords, (list, tuple)) and len(coords) == 2:
      if all(isinstance(coord, (int, float)) for coord in coords):
        return 1

    if isinstance(coords, (list, tuple)):
      for item in coords:
        count += counter(item)

    return count

  for feature in raw_geojson["features"]:
    if feature.get("geometry"):
        coords = feature["geometry"]["coordinates"]
        final_count += counter(coords)

  return final_count

def count_datastore_rows(resource_id):
    db_url = config['ckan.datastore.read_url']
    engine = sa.create_engine(db_url)
    
    with engine.connect() as conn:
        result = conn.execute(
            sa.text(f'SELECT count(*) FROM "{resource_id}"')
        )

    for row in result:
        output = row[0]


    return output