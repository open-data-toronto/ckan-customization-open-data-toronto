from ckan.lib.base import BaseController
from shapely.geometry import shape
from urlparse import urlsplit, urlunsplit
​
from .config import DATASTORE_GEOSPATIAL_FORMATS, DATASTORE_TABULAR_FORMATS, DOWNLOAD_FORMAT, DOWNLOAD_PROJECTION
​
import ckan.plugins.toolkit as tk
​
import geopandas as gpd
import iotrans
import pandas as pd
import requests
​
import gc
import io
import json
import mimetypes
import os
import tempfile

​
class DownloadsController(BaseController):
    def download_resource(self, resource_id):
        metadata = tk.get_action('resource_show')(None, { 'id':resource_id })
​
        if not metadata['datastore_active']:
            tk.redirect_to(metadata['url'])
        else:
            filename = self.get_datastore(metadata)
            mimetype, encoding = mimetypes.guess_type(filename)
​
            if mimetype is None and filename.endswith('gpkg'):
                mimetype = 'application/geopackage+vnd.sqlite3'
​
            tk.response.headers['Content-Type'] = mimetype
            tk.response.headers['Content-Disposition'] = (b'attachment; filename="{fn}"'.format(fn=filename))
​
    def get_datastore(self, metadata):
        format = tk.request.GET.get('format', DOWNLOAD_FORMAT).lower()
        projection = tk.request.GET.get('projection', DOWNLOAD_PROJECTION)
​
        info = tk.get_action('datastore_info')(None, { 'id': metadata['id'] })
        is_geospatial = 'geometry' in info['schema']
​
        if not ((is_geospatial and format in DATASTORE_GEOSPATIAL_FORMATS) or \
            (not is_geospatial and format in DATASTORE_TABULAR_FORMATS)):
            raise tk.ValidationError({
                'constraints': ['Inconsistency between data type and requested file format']
            })
​
        raw = requests.get('{host}/datastore/dump/{resource_id}'.format(
            host=tk.config['ckan.site_url'],
            resource_id=metadata['id']
        )).content.decode('utf-8')
​
        df = pd.read_csv(io.StringIO(raw))
​
        del raw
​
        if is_geospatial:
            df['geometry'] = df['geometry'].apply(lambda x: shape(x) if isinstance(x, dict) else shape(json.loads(x)))
            df = gpd.GeoDataFrame(df, crs={ 'init': 'epsg:{0}'.format(DOWNLOAD_PROJECTION) }, geometry='geometry').to_crs({ 'init': 'epsg:{0}'.format(projection) })
​
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, '{0}.{1}'.format(metadata['name'], format))
​
        output = iotrans.to_file(
            df,
            path,
            projection=projection,
            zip_content=(format=='shp')
        )
​
        del df
​
        with open(output, 'rb') as f:
            tk.response.write(f.read())
​
        iotrans.utils.prune(tmp_dir)
        gc.collect()
​
        return '{fn}.{fmt}'.format(fn=metadata['name'], fmt=output.split('.')[-1])
