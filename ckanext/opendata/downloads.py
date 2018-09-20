from ckan.lib.base import BaseController
from ckan.plugins.toolkit import get_action
from contextlib import contextmanager

import csv
import io
import json

from flask import make_response

PAGINATE_BY = 32000

class DownloadsController(base.BaseController):
    def download_resource(self, resource_id, format):
        records_format_map = {
            'json': 'objects',
            'xml': 'objects',
            'csv': 'csv',
        }

        resource = get_action('datastore_search')(None, {
            'resource_id': resource_id,
            'limit': PAGINATE_BY if limit is None else min(PAGINATE_BY, lim),
            'offset': offs,
            'sort': '_id',
            'records_format': records_format_map['format'],
            'include_total': 'false',  # XXX: default() is broken
        })

        with start_writer(result['fields']) as wr:
            records = resource['records']
            wr.write_records(records)

@contextmanager
def csv_writer(response, fields, name=None):
    if hasattr(response, 'headers'):
        response.headers['Content-Type'] = b'text/csv; charset=utf-8'
        if name:
            response.headers['Content-disposition'] = (b'attachment; filename="{name}.csv"'.format(name=name))

    csv.writer(response, encoding='utf-8').writerow(f['id'] for f in fields)
    yield TextWriter(response)

class TextWriter(object):
    def __init__(self, response):
        self.response = response

    def write_records(self, records):
        self.response.write(records)
