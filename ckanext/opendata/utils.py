from ckan.lib.navl.dictization_functions import missing

import ckan.plugins.toolkit as tk

import codecs


def string_to_hex(s):
    return codecs.encode(s.encode('utf-8'), 'hex')

def hex_to_string(s):
    return codecs.decode(s, 'hex').decode('utf-8')

def is_geospatial(resource_id):
    info = tk.get_action('datastore_info')(None, { 'id': resource_id })

    return 'geometry' in info['schema']

def to_list(l):
    if not isinstance(l, list):
        return [l]

    return l

# def is_hex(s):
#     try:
#         int(s, 16)
#         return True
#     except ValueError:
#         return False

# Built-in vocabulary validation requires context update
def validate_vocabulary(vocab_name, tags, context):
    vocab = tk.get_action('vocabulary_show')(context, { 'id': vocab_name })
    vocab_tags = [ t['name'] for t in vocab['tags'] ]

    if not isinstance(tags, list):
        tags = tags.split(',')

    for t in tags:
        if not t in vocab_tags:
            raise tk.ValidationError({
                'constraints': [
                    'Tag {0} is not in the vocabulary {1}'.format(t, vocab_name)
                ]
            })

    return vocab
