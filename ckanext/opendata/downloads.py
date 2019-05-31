from ckan.lib.base import BaseController
from shapely.geometry import shape

import ckan.plugins.toolkit as tk

import geopandas as gpd
import iotrans
import pandas as pd
import requests

import io
import json
import logging
import mimetypes
import os
import shutil
import tempfile


def df_to_xml(df, path):
    def row_to_xml(row):
        xml = ['<row>']
        for i, col_name in enumerate(row.index):
            xml.append('  <field name="{0}">{1}</field>'.format(col_name, row.iloc[i]))
        xml.append('</row>')
        return '\n'.join(xml)

    content = '\n'.join(df.apply(row_to_xml, axis=1))

    with open(path, 'w') as f:
        f.write(content)

class DownloadsController(BaseController):
    def download_resource(self, resource_id):
        metadata = tk.get_action('resource_show')(None, { 'id':resource_id })

        if not metadata['datastore_active']:
            tk.redirect_to(metadata['url'])
        else:
            filename = self.get_datastore(metadata)

            tk.response.headers['Content-Type'] = mimetypes.guess_type('.'.join(filename))[0]
            tk.response.headers['Content-Disposition'] = (b'attachment; filename="{fn}"'.format(fn='.'.join(filename)))

    def get_datastore(self, metadata):
        format = tk.request.GET.get('format', config.DOWNLOAD_FORMAT).lower()
        projection = tk.request.GET.get('projection', config.DOWNLOAD_PROJECTION)
        # offset = tk.request.GET.get('offset')
        # limit = tk.request.GET.get('limit')

        data = tk.get_action('datastore_search')(None, {
            'resource_id': metadata['id'],
            'limit': 0,
            'include_total': True
        })

        # try:
        #     offset = int(offset)
        # except:
        #     raise tk.ValidationError({
        #         'offset': ['Requested offset is an invalid number']
        #     })

        # if offset > data['total']:
        #     raise tk.ValidationError({
        #         'offset': ['Requested offset is greater than the {num} of rows available in the dataset'.format(num=data['total'])]
        #     })

        is_geospatial = False
        for x in data['fields']:
            if x['id'] == 'geometry':
                is_geospatial = True
                break

        if not ((is_geospatial and format in config.DATASTORE_GEOSPATIAL_FORMATS) or \
            (not is_geospatial and format in config.DATASTORE_TABULAR_FORMATS)):
            raise tk.ValidationError({
                'constraints': ['Inconsistency between data type and requested file format']
            })

        r = requests.get('{host}/datastore/dump/{resource_id}'.format(host=tk.config['ckan.site_url'], resource_id=metadata['id']))
        df = pd.read_csv(io.StringIO(r.content.decode('utf-8')))

        if is_geospatial:
            df['geometry'] = df['geometry'].apply(lambda x: shape(x) if isinstance(x, dict) else shape(json.loads(x)))
            df = gpd.GeoDataFrame(df, crs={ 'init': 'epsg:{0}'.format(DEFAULTS['projection']) }, geometry='geometry').to_crs({ 'init': 'epsg:{0}'.format(projection) })

        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, '{0}.{1}'.format(metadata['name'], format))

        output = iotrans.to_file(
            df,
            path,
            projection=projection,
            zip_content=(format=='shp')
        )

        with open(output, 'r') as f:
            shutil.copyfileobj(f, tk.response)

        iotrans.utils.prune(tmp_dir)

        return [metadata['name'], output.split('.')[-1]]
