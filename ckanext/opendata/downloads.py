from ckan.lib.base import BaseController
from shapely.geometry import shape

import ckan.plugins.toolkit as tk

import geopandas as gpd
import iotrans
import pandas as pd
import requests

import gc
import io
import json
import mimetypes
import os
import tempfile

import constants
import utils


def _write_datastore(params, resource):
    format = params.get('format', constants.DOWNLOAD_FORMAT).upper()
    projection = params.get('projection', constants.DOWNLOAD_PROJECTION)

    is_geospatial = utils.is_geospatial(resource['id'])

    assert (
        (is_geospatial and format in constants.GEOSPATIAL_FORMATS) or \
        (not is_geospatial and format in constants.TABULAR_FORMATS)
    ), 'Inconsistency between data type and requested file format'

    # Is this the best way to fetch data from datastore tables?
    raw = requests.get('{host}/datastore/dump/{resource_id}'.format(
        host=tk.config['ckan.site_url'],
        resource_id=resource['id']
    )).content.decode('utf-8')

    # WISHLIST: remove dependency on pandas/geopandas
    df = pd.read_csv(io.StringIO(raw))

    del raw

    if is_geospatial:
        df['geometry'] = df['geometry'].apply(
            lambda x: \
                shape(x) if isinstance(x, dict) else shape(json.loads(x))
        )

        df = gpd.GeoDataFrame(
            df,
            crs={ 'init': 'epsg:{0}'.format(constants.DOWNLOAD_PROJECTION) },
            geometry='geometry'
        ).to_crs(
            { 'init': 'epsg:{0}'.format(projection) }
        )

    # TODO: validate that the resource name doesn't already contain format

    # WISHLIST: store conversion in memory instead of write to disk
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(
        tmp_dir,
        '{0}.{1}'.format(resource['name'], format.lower())
    )

    output = iotrans.to_file(
        df,
        path,
        projection=projection,
        zip_content=(format in constants.ZIPPED_FORMATS)
    )

    del df

    with open(output, 'rb') as f:
        tk.response.write(f.read())

    iotrans.utils.prune(tmp_dir)
    gc.collect()

    # TODO: What's wrong with the default file name? (ie. first half of output)
    fn = '{0}.{1}'.format(resource['name'], output.split('.')[-1])
    mt = utils.get_mimetype(fn)

    return fn, mt

class DownloadsController(BaseController):
    def download_data(self, resource_id):
        resource = tk.get_action('resource_show')(None, { 'id': resource_id })

        if not resource['datastore_active']:
            tk.redirect_to(resource['url'])
        else:
            filename, mimetype = _write_datastore(tk.request.GET, resource)

            tk.response.headers['Content-Type'] = mimetype
            tk.response.headers['Content-Disposition'] = (
                b'attachment; filename="{0}"'.format(filename)
            )
