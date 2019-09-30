CUSTOM_MIMETYPES = {
    'gpkg': 'application/geopackage+vnd.sqlite3'
}

ZIPPED_FORMATS = ['shp']

CATALOGUE_SEARCH = {
    'rows': 10,
    'sort': 'score desc',
    'start': 0
}

GEOSPATIAL_FORMATS = ['csv', 'geojson', 'gpkg', 'shp']
TABULAR_FORMATS = ['csv', 'json', 'xml']

DOWNLOAD_FORMAT = 'csv'
DOWNLOAD_PROJECTION = '4326'
DOWNLOAD_OFFSET = '0'
DOWNLOAD_LIMIT = '0'

MAX_FIELD_LENGTH = 350

REMOVED_FIELDS = ['author', 'maintainer', 'version']
