from ckan.lib.base import BaseController
from ckan.plugins.toolkit import get_action, request, response, redirect_to, ValidationError

from shapely.geometry import shape

import geopandas as gpd
import pandas as pd

import io
import json
import mimetypes
import os
import requests
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
        metadata = get_action('resource_show')(None, { 'id':resource_id })

        if not metadata['datastore_active']:
            redirect_to(metadata['url'])
        else:
            filename = self.get_datastore(metadata)

            response.headers['Content-Type'] = mimetypes.guess_type('.'.join(filename))[0]
            response.headers['Content-Disposition'] = (b'attachment; filename="{fn}"'.format(fn='.'.join(filename)))

    def get_datastore(self, metadata):
        format = request.GET.get('format', 'csv').lower()
        projection = request.GET.get('projection', '4326')
        offset = request.GET.get('offset', '0')
        # limit = request.GET.get('limit')

        data = get_action('datastore_search')(None, {
            'resource_id': metadata['id'],
            'limit': 0,
            'include_total': True
        })

        try:
            offset = int(offset)
        except:
            raise ValidationError({
                'offset': ['Requested offset is an invalid number']
            })

        if offset > data['total']:
            raise ValidationError({
                'offset': ['Requested offset greater than number of rows in data']
            })

        is_geospatial = False
        for x in data['fields']:
            if x['id'] == 'geometry':
                is_geospatial = True
                break

        if (is_geospatial and format in ['csv', 'dxf', 'geojson', 'shp']) or (not is_geospatial and format in ['csv', 'json', 'xml']):
            is_valid_request = True
        else:
            raise ValidationError({
                'constraints': ['Inconsistency between data type and requested file format']
            })

        r = requests.get(metadata['url']).content
        df = pd.read_csv(io.StringIO(r.decode('utf-8')))

        if is_geospatial:
            df['geometry'] = df['geometry'].apply(lambda x: shape(x) if isinstance(x, dict) else shape(json.loads(x)))
            df = gpd.GeoDataFrame(df, crs={ 'init': 'epsg:4326' }, geometry='geometry').to_crs({ 'init': 'epsg:{0}'.format(projection) })

        tmp_dirs = [tempfile.mkdtemp()]
        path = os.path.join(tmp_dirs[0], '{name}.{format}'.format(name=metadata['name'], format=format))

        if format == 'csv':
            df.to_csv(path, index=False, encoding='utf-8')
        elif format == 'json':
            df.to_json(path, orient='records')
        elif format == 'xml':
            df_to_xml(df, path)
        elif format == 'geojson':
            df.to_file(path, driver='GeoJSON', encoding='utf-8')
        elif format == 'dxf':
            df.to_file(path, driver='DXF')
        elif format == 'shp':
            df.to_file(path, driver='ESRI Shapefile')

            tmp_dirs.append(tempfile.mkdtemp())
            format = 'zip'
            path = shutil.make_archive(os.path.join(tmp_dirs[1], metadata['name']), 'zip', root_dir=tmp_dirs[0], base_dir='.')

        with open(path, 'r') as f:
            shutil.copyfileobj(f, response)

        for td in tmp_dirs:
            shutil.rmtree(td)

        return [metadata['name'], format]
