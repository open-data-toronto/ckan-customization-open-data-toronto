CUSTOM_MIMETYPES = {
    'gpkg': 'application/geopackage+vnd.sqlite3'
}

ZIPPED_FORMATS = ['SHP']

CATALOGUE_SEARCH = {
    'rows': 10,
    'sort': 'score desc',
    'start': 0
}

GEOSPATIAL_FORMATS = {'CSV', 'GEOJSON', 'GPKG', 'SHP'}
TABULAR_FORMATS = {'CSV', 'JSON', 'XML'}

DOWNLOAD_FORMAT = 'csv'
DOWNLOAD_PROJECTION = '4326'
DOWNLOAD_OFFSET = '0'
DOWNLOAD_LIMIT = '0'

MAX_FIELD_LENGTH = 350

REMOVED_FIELDS = ['author', 'maintainer', 'version']
