from ckan.lib.base import BaseController
from difflib import SequenceMatcher

import ckan.plugins.toolkit as tk
import json


def _get_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


class TagsController(BaseController):
    def match_tags(self):
        vid = tk.request.GET.get("vocabulary_id", "")
        q = tk.request.GET.get("incomplete", "").lower()

        tags = tk.get_action("tag_list")(None, {"vocabulary_id": vid})
        scores = [_get_similarity(q, t.lower()) for t in tags]

        tk.response.headers["Content-Type"] = "application/json;"
        tk.response.body = json.dumps(
            {
                "ResultSet": {
                    "Result": [
                        {"Name": x} for _, x in sorted(zip(scores, tags), reverse=True)
                    ]
                }
            }
        )
