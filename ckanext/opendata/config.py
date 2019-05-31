GEOSPATIAL_FORMATS = ['csv', 'geojson', 'gpkg', 'shp']
TABULAR_FORMATS = ['csv', 'json', 'xml']

DEFAULTS = {
    'format': 'csv',
    'projection': '4326',
    'offset': '0',
    'limit': '0'
}

DEFAULT_FORMATS = {
    'geospatial': ['csv', 'geojson', 'shp'],
    'tabular': ['csv', 'json', 'xml']
}

DEFAULT_SEARCH = {
    'rows': 10,
    'sort': 'score desc',
    'start': 0
}

MAX_STRING_LENGTH = 350
