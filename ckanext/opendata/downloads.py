from shapely.geometry import shape, GeometryCollection
from flask import Response

import ckan.plugins.toolkit as tk

import geopandas as gpd
import iotrans
import pandas as pd
import requests

import tempfile
import gc
import io
import json
import csv
import os

from . import constants, utils

def shape_function_wrapper(x):
    if isinstance(x, dict):
        return shape(x)
    elif x not in ["", None, " "]:
        try:
            return shape(json.loads(x))
        except:
            return GeometryCollection()
    else:
        print("Issue dealing with geometry: " + str(x) + " Returning empty GeometryCollection()")
        return GeometryCollection()


def _write_datastore(params, resource, target_dir):
    # converts and returns input file to given format
    print("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx STARTING FILE CREATION")

    # get format and projection from the request headers - likely the input GET url params
    format = params.get("format", constants.DOWNLOAD_FORMAT).upper()
    projection = params.get("projection", constants.DOWNLOAD_PROJECTION)

    # determine if the resource is geospatial
    is_geospatial = utils.is_geospatial(resource["id"])

    # make sure these formats make sense together
    assert (is_geospatial and format in constants.GEOSPATIAL_FORMATS) or (
        not is_geospatial and format in constants.TABULAR_FORMATS
    ), "Inconsistency between data type and requested file format"

    # Get data from the datastore by using a datastore/dump call

    # convert the data to a dataframe
    # WISHLIST: remove dependency on pandas/geopandas
    env = tk.config.get("ckan.site_url")
    dump = env + "/datastore/dump/" + resource["id"]

    print("-------------------------------- FILE CREATION - to dataframe")
    df = pd.read_csv( dump )
    print(" ---------------------------- ################################# are there duplicates?")
    print( df[df.duplicated()] )
    print(" ---------------------------- #################################")
    #del records

    # if we have geospatial data, use the shape() fcn on each object
    if is_geospatial:
        df["geometry"] = df["geometry"].apply(shape_function_wrapper)
        
        # we'll add the EPSG code to the output filename
        filename_suffix = " - {}".format( projection )

    # make this a geodataframe
        df = gpd.GeoDataFrame(
            df,
            crs={"init": "epsg:{0}".format(constants.DOWNLOAD_PROJECTION)},
            geometry="geometry",
        )#.to_crs({"init": "epsg:{0}".format(projection)})
        print("-------------------------------- FILE CREATION - to GEOGRAPHIC dataframe")

    # TODO: validate that the resource name doesn't already contain format

    # if the file isnt geospatial, we wont need to add an EPSG code to its filename
    if not is_geospatial:
        filename_suffix = ""
    
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, "{0}.{1}".format(resource["name"], format.lower()))

    print("-------------------------------- FILE CREATION - output file making start")
    # turn the geodataframe into a file
    output = iotrans.to_file(
        df,
        path,
        projection=projection,
        zip_content=(format in constants.ZIPPED_FORMATS),
    )
    print("-------------------------------- FILE CREATION - output file making end")

    del df
    print("-------------------------------- FILE CREATION - output file writing start")
    # store the bytes of the file
    with open(output, 'rb') as f:
        response = io.BytesIO(f.read())
    print("-------------------------------- FILE CREATION - output file writing end")

    print(response)

    # delete the tmp dir used above to make the file
    iotrans.utils.prune(tmp_dir)
    gc.collect()

    ## assign filename and mimetype
    fn = "{0}{2}.{1}".format(resource["name"], output.split(".")[-1], filename_suffix)
    mt = "application/octet-stream" #utils.get_mimetype(fn)

    print("--------------------- FINISHED FILE CREATION")

    return fn, mt, response
