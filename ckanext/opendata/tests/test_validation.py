from contextlib import contextmanager
from typing import Dict, List, Optional, Union

import ckan.logic
import ckan.tests.helpers as helpers
import pytest

from .constants import (
    SCHEMING_DNE_MOCK_TEST_OPTION_1,
    SCHEMING_DNE_MOCK_TEST_OPTION_2,
    SCHEMING_MOCK_TEST_OPTIONS,
)


class TestPackageCreateValidation:
    @staticmethod
    @contextmanager
    def _create_package(topic: str, org: Dict, sysadmin: Dict):
        context = {"ignore_auth": False, "user": sysadmin.name}
        data = {
            "name": "test-package",
            "private": False,
            "owner_org": org["id"],
            # DB-dependent fields:
            "topics": topic,
            "dataset_category": "Document",
            "owner_division": "311 Toronto",
            "refresh_rate": "Daily",
        }
        result = None

        try:
            result = helpers.call_action("package_create", context, **data)
            yield result
        finally:
            # Test cleanup: delete any created records via ckan action.
            # This is a bit ugly: the db itself would be a test fixture with its own
            # setup/teardown so this wouldn't be an issue but current dev
            # environments do not have a 2nd postgres instance that can be used.
            # TODO: switch to a db test fixture to handle test lifecycle.
            if result is not None:
                helpers.call_action("package_delete", context, id=result["name"])

    @pytest.fixture
    def topics_resource(sysadmin: Dict):
        resource_alias = "topics"
        search = helpers.call_action("datastore_search", context={}, id=resource_alias)
        resource_id = search["resource_id"]
        created_test_options = helpers.call_action("datastore_upsert", context={}, id=resource_id, records=SCHEMING_MOCK_TEST_OPTIONS, method="insert", force=True)
        yield created_test_options["records"]
        for option in SCHEMING_MOCK_TEST_OPTIONS:
            helpers.call_action("datastore_upsert", context={}, id=resource_id, filters={"value": option["value"]}, force=True)
