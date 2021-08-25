from shapely.geometry import shape
from flask import Response

import ckan.plugins.toolkit as tk

import geopandas as gpd
import iotrans
import pandas as pd
import requests

import gc
import io
import json
import os
import tempfile

from . import constants, utils

def _datastore_dump(resource):
    # get format of resource
    format = resource["format"]

def _write_datastore(params, resource):
    # get format and projection from the request headers - likely the input GET url params
    print("========================================")
    print(params)
    print("========================================")

    format = params.get("format", constants.DOWNLOAD_FORMAT).upper()
    projection = params.get("projection", constants.DOWNLOAD_PROJECTION)

    # make sure these formats make sense together and determine if the resource is geospatial
    is_geospatial = utils.is_geospatial(resource["id"])

    print("========================================")
    print(is_geospatial)
    print("========================================")

    assert (is_geospatial and format in constants.GEOSPATIAL_FORMATS) or (
        not is_geospatial and format in constants.TABULAR_FORMATS
    ), "Inconsistency between data type and requested file format"

    # Get data from the datastore by using a datastore/dump call
    # Is this the best way to fetch data from datastore tables?
    length = tk.get_action("datastore_info")(None, {"id": resource["id"]})["meta"]["count"]
    raw = tk.get_action("datastore_search")(None, {"resource_id": resource["id"], "limit": length})
    #raw = requests.get(
    #    "{host}/datastore/dump/{resource_id}".format(
    #        host=tk.config["ckan.site_url"], resource_id=resource["id"]
    #    )
    #).content.decode("utf-8")

    print("========================================")
    print(raw)
    print(type(raw["records"]))
    print(raw["records"][:])
    print(raw["records"][0])
    print("========================================")

    # convert the data to a dataframe
    # WISHLIST: remove dependency on pandas/geopandas
    df = pd.DataFrame( raw["records"][:] )

    del raw

    # if we have geospatial data, use the shape() fcn on each object
    if is_geospatial:
        df["geometry"] = df["geometry"].apply(
            lambda x: shape(x) if isinstance(x, dict) else shape(json.loads(x))
        )

    # make this a geodataframe
        df = gpd.GeoDataFrame(
            df,
            crs={"init": "epsg:{0}".format(constants.DOWNLOAD_PROJECTION)},
            geometry="geometry",
        ).to_crs({"init": "epsg:{0}".format(projection)})

    # TODO: validate that the resource name doesn't already contain format

    
    # WISHLIST: store conversion in memory instead of write to disk
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "{0}.{1}".format(resource["name"], format.lower()))

    # turn the geodataframe into a file
    output = iotrans.to_file(
        df,
        path,
        projection=projection,
        zip_content=(format in constants.ZIPPED_FORMATS),
    )

    del df

    # ... read the file in tk.response.write()
    # this likely creates the actual response returned by the function
    
    # this is unclear and causes an error so im commenting it out for now
    with open(output, "rb") as f:
        #response_object.set_data( f.read() )
        response = f.read() 

    # delete the tmp dir used above to make the file
    iotrans.utils.prune(tmp_dir)
    gc.collect()

    # TODO: What's wrong with the default file name? (ie. first half of output)
    fn = "{0}.{1}".format(resource["name"], output.split(".")[-1])
    mt = utils.get_mimetype(fn)

    return fn, mt, response


