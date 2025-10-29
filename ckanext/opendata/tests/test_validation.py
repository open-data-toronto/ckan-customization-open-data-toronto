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
        #lc = LocalCKAN(username=sysadmin.name)

        resource_alias = "topics"
        #search = lc.action.datastore_search(resource_id=resource_alias)
        search = helpers.call_action("datastore_search", context={}, id=resource_alias)
        resource_id = search["resource_id"]
        created_test_options = helpers.call_action("datastore_upsert", context={}, id=resource_id, records=SCHEMING_MOCK_TEST_OPTIONS, method="insert", force=True)
        #created_test_options = lc.action.datastore_upsert(
        #    resource_id=resource_id,
        #    records=SCHEMING_MOCK_TEST_OPTIONS,
        #    method="insert",
        #    force=True,
        #)
        yield created_test_options["records"]
        for option in SCHEMING_MOCK_TEST_OPTIONS:
            helpers.call_action("datastore_upsert", context={}, id=resource_id, filters={"value": option["value"]}, force=True)
        #    lc.action.datastore_delete(
        #        resource_id=resource_id,
        #        filters={"value": option["value"]},
        #        force=True,
        #    )

    @pytest.mark.parametrize(
        "topics",
        (
            # Inserting a valid value is valid
            SCHEMING_MOCK_TEST_OPTIONS[0]["value"],
            # Accepts multiple values
            [
                SCHEMING_MOCK_TEST_OPTIONS[0]["value"],
                SCHEMING_MOCK_TEST_OPTIONS[1]["value"],
            ],
        ),
    )
    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi", "scheming_datasets"])
    @pytest.mark.usefixtures("with_plugins")
    def test_valid_options(self, topics, org, sysadmin, topics_resource):
        expected_topics = topics if isinstance(topics, list) else [topics]
        with self._create_package(topics, org, sysadmin) as result:
            assert result["topics"] == expected_topics

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi", "scheming_datasets"])
    @pytest.mark.usefixtures("with_plugins")
    def test_accepts_none(self, org, sysadmin, topics_resource):
        with self._create_package(None, org, sysadmin) as result:
            assert "topics" not in result

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi", "scheming_datasets"])
    @pytest.mark.usefixtures("with_plugins")
    def test_accepts_empty_list(self, org, sysadmin, topics_resource):
        with self._create_package([], org, sysadmin) as result:
            assert result["topics"] == []

    #@pytest.mark.parametrize(
    #    "topics",
    #    (
    #        SCHEMING_MOCK_TEST_OPTIONS[0]["label"],
    #        # Inserting other values that do not exist in datastore is not valid
    #        SCHEMING_DNE_MOCK_TEST_OPTION_1["value"],
    #        SCHEMING_DNE_MOCK_TEST_OPTION_2["value"],
    #        # reject even if one of them is valid but any other is not valid
    #        [
    #            SCHEMING_DNE_MOCK_TEST_OPTION_2["value"],  # not valid
    #            SCHEMING_MOCK_TEST_OPTIONS[0]["value"],  # valid
    #        ],
    #    ),
    #)
    #@pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    #@pytest.mark.usefixtures("with_plugins")
    #def test_invalid_options_are_rejected(self, topics, org, sysadmin, topics_resource):
    #    with pytest.raises(ckan.logic.ValidationError) as exc_info:
    #        with self._create_package(topics, org, sysadmin) as result:
    #            assert exc_info.value.error_dict.get("topics") is not None
