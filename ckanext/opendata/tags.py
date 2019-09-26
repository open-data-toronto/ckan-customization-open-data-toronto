from ckan.lib.base import BaseController
from difflib import SequenceMatcher

import ckan.plugins.toolkit as tk
import json


def _get_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

class TagsController(BaseController):
    def get_tag_list(self):
        vocabulary_id = tk.request.GET.get('vocabulary_id', '')
        query = tk.request.GET.get('incomplete', '')

        tags = tk.get_action('tag_list')(None, { 'vocabulary_id': vocabulary_id })
        scores = [_get_similarity(query, t.lower()) for t in tags]

        tags = [{ 'Name': x } for _, x in sorted(zip(scores, tags), reverse=True)]

        tk.response.headers['Content-Type'] = 'application/json;'
        tk.response.body = json.dumps({
            'ResultSet': {
                'Result': tags
            }
        })
