from ckan.lib.base import BaseController
from ckan.plugins.toolkit import get_action, request, response, redirect_to

from simplejson import dumps
from six import text_type
from xml.etree.cElementTree import Element, SubElement, ElementTree

import urllib

PAGE_SIZE = 5000

CONTENT_TYPE_MAP = {
    'csv': b'text/csv; charset=utf-8',
    'json': b'application/json; charset=utf-8',
    'xml': b'text/xml; charset=utf-8'
}

RECORDS_FORMAT_MAP = {
    'csv': 'csv',
    'json': 'objects',
    'xml': 'objects'
}


def insert_xml_node(root, k, v, key_attr=None):
    element = SubElement(root, k)

    if v is None:
        element.attrib[u'xsi:nil'] = u'true'
    elif not isinstance(v, (list, dict)):
        element.text = text_type(v)
    else:
        if isinstance(v, list):
            it = enumerate(v)
        else:
            it = v.items()

        for key, value in it:
            insert_xml_node(element, 'value', value, key)

    if key_attr is not None:
        element.attrib['key'] = text_type(key_attr)

class DownloadsController(BaseController):
    def download_resource(self, resource_id):
        metadata = get_action('resource_show')(None, { 'id':resource_id })

        if metadata['datastore_active']:
            self.get_datastore(metadata)
        else:
            self.get_filestore(metadata)

    def get_datastore(self, metadata):
        format = request.GET.get('format', 'csv').lower()
        # limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset', '0'))

        response.headers['Content-Type'] = CONTENT_TYPE_MAP[format]
        response.headers['Content-Disposition'] = (b'attachment; filename="{name}.{format}"'.format(name=metadata['name'], format=format))

        first = True
        while True:
            resource = get_action('datastore_search')(None, {
                'resource_id': metadata['id'],
                'records_format': RECORDS_FORMAT_MAP[format],
                'limit': PAGE_SIZE,
                'offset': offset,
                'sort': '_id'
            })

            if first:
                wrappers = {
                    'csv': ['{data}\n'.format(data=','.join([f['id'] for f in resource['fields']])), ''],
                    'json': ['[', ']'],
                    'xml': [b'<data>\n', b'</data>']
                }

                response.write(wrappers[format][0])

                first = False

            if format == 'csv':
                response.write(resource['records'])
            elif format == 'json':
                response.write(dumps(resource['records'], separators=(u',', u':'))[1:-1])
            elif format == 'xml':
                for r in resource['records']:
                    root = Element(u'row')
                    root.attrib[u'_id'] = text_type(r[u'_id'])

                    for c in [f['id'] for f in resource['fields'][1:]]:
                        insert_xml_node(root, c, r[c])

                    ElementTree(root).write(response, encoding='utf-8')
                    response.write(b'\n')

            if len(resource['records']) < PAGE_SIZE:
                break

            offset += PAGE_SIZE

        response.write(wrappers[format][1])

    def get_filestore(self, metadata):
        if metadata['format'].lower() in ['html']:
            redirect_to(metadata['url'])
        else:
            response.headers['Content-Type'] = CONTENT_TYPE_MAP[metadata['format'].lower()] if format in CONTENT_TYPE_MAP.keys() else 'application/octet-stream'
            response.headers['Content-Disposition'] = (b'attachment; filename="{name}.{format}"'.format(name=metadata['name'], format=metadata['format'].lower()))

            content = urllib.urlopen(metadata['url'])
            for line in content:
                response.write(line)

