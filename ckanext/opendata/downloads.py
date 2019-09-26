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


def _write_datastore(params, resource):
    format = params.get('format', constants.DOWNLOAD_FORMAT).lower()
    projection = params.get('projection', constants.DOWNLOAD_PROJECTION)

    is_geospatial = utils.is_geospatial(resource['id'])

    assert (
        (is_geospatial and format in constants.GEOSPATIAL_FORMATS) or \
        (not is_geospatial and format in constants.TABULAR_FORMATS)
    ), 'Inconsistency between data type and requested file format'

    # Is this the best way to fetch data from datastore tables?
    raw = requests.get('{host}/datastore/dump/{resource_id}'.format(
        host=tk.config['ckan.site_url'],
        resource_id=metadata['id']
    )).content.decode('utf-8')

    # WISHLIST: remove dependency on pandas/geopandas
    df = pd.read_csv(io.StringIO(raw))

    del raw

    if is_geospatial:
        df['geometry'] = df['geometry'].apply(
            lambda x: shape(x)
                if isinstance(x, dict)
                else shape(json.loads(x))
        )

        df = gpd.GeoDataFrame(
            df,
            crs={
                'init': 'epsg:{0}'.format(constants.DOWNLOAD_PROJECTION)
            },
            geometry='geometry'
        ).to_crs({
            'init': 'epsg:{0}'.format(projection)
        })

    # WISHLIST: store conversion in memory instead of write to disk
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, '{0}.{1}'.format(metadata['name'], format))

    output = iotrans.to_file(
        df,
        path,
        projection=projection,
        zip_content=(format=='shp')
    )

    del df

    with open(output, 'rb') as f:
        tk.response.write(f.read())

    iotrans.utils.prune(tmp_dir)
    gc.collect()

    return '{fn}.{fmt}'.format(
        fn=metadata['name'],
        fmt=output.split('.')[-1]
    )

class DownloadsController(BaseController):
    def download_resource(self, resource_id):
        resource = tk.get_action('resource_show')(None, { 'id':resource_id })

        if not resource['datastore_active']:
            tk.redirect_to(resource['url'])
        else:
            filename = _write_datastore(tk.request.GET, resource)
            mimetype, encoding = mimetypes.guess_type(filename)

            if mimetype is None and filename.endswith('gpkg'):
                mimetype = 'application/geopackage+vnd.sqlite3'

            tk.response.headers['Content-Type'] = mimetype
            tk.response.headers['Content-Disposition'] = \
                (b'attachment; filename="{fn}"'.format(fn=filename))
