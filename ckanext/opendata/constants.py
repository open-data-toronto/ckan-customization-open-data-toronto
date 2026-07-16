
from enum import Enum

MULTIPLE_CHOICE_PACKAGE_FIELDS = (
    "topics",
    "civic_issues",
    "formats",
)


class DatastoreCacheFormats(Enum):
    spatial = ["CSV", "SHP", "GPKG", "GEOJSON"]
    non_spatial = ["CSV", "XML", "JSON"]

