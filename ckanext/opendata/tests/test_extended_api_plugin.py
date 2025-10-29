import io
from contextlib import contextmanager
from typing import Dict
from warnings import warn

import ckan.plugins.toolkit as tk
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest
from opendata.constants import DatastoreCacheFormats
from werkzeug.datastructures import FileStorage

from .utils import mock_actions


class TestDatastoreCache:
    @pytest.fixture
    def datastore_resource(self, sysadmin, package):

        context = {
            "user": sysadmin.name,
            "auth_user_obj": sysadmin,
        }

        csv_data = [
            {"column1": "value1a", "column2": "value2a"},
            {"column1": "value1b", "column2": "value2b"},
        ]
        csv_header = f'{",".join(csv_data[0].keys())}'
        csv_values = "\n".join([",".join(x.values()) for x in csv_data])
        csv = f"{csv_header}\n{csv_values}"

        file_obj = io.BytesIO(csv.encode("utf-8"))
        file_obj.name = "example.csv"

        resource = None
        datastore_record = None
        try:
            resource = helpers.call_action(
                "resource_create",
                context=context,
                package_id=package["id"],
                name="test_fixture_resource",
                format="CSV",
                description="description of test resource. this resource should be cleaned up (deleted) by test fixtures",
                upload=FileStorage(stream=file_obj, filename=file_obj.name),
            )
            datastore_record = helpers.call_action(
                "datastore_create",
                context=context,
                resource_id=resource["id"],
                force=True,
                records=csv_data,
                fields=[
                    {"id": "column1", "type": "text"},
                    {"id": "column2", "type": "text"},
                ],
            )
            yield resource, datastore_record
        finally:
            resource_id = None if resource is None else resource.get("id")
            if resource_id is not None:
                try:
                    if datastore_record is not None:
                        helpers.call_action(
                            "datastore_delete",
                            context,
                            resource_id=resource_id,
                            force=True,
                        )
                finally:
                    # whether or not deleting datastore works, we still want to delete
                    # the resource
                    helpers.call_action("resource_delete", context, id=resource_id)

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_enforces_authorization(self, record_test_name):
        record_test_name("Datastore Cache API enforces authorization")
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action("datastore_cache")

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_enforces_package_or_resource_id(self, record_test_name):
        record_test_name("Datastore Cache API performs package/resoruce validation")
        context = {"auth_user_obj": "some_user"}
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "datastore_cache",
                context=context,
                package_id=None,
                resource_id=None,
            )

    @staticmethod
    def _is_datastore_resource(resource_id: str) -> bool:
        resource = helpers.call_action("resource_show", id=resource_id)
        return resource["is_datastore_cache_file"]

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_creates_cache_resources(
        self, record_test_name, sysadmin, datastore_resource
    ):
        record_test_name("Datastore Cache API creates cached resources")

        resource, datastore_record = datastore_resource
        context = {"auth_user_obj": sysadmin}
        result = helpers.call_action(
            "datastore_cache",
            context=context,
            resource_id=resource["id"],
        )
        for format in DatastoreCacheFormats.non_spatial.value:
            resource_id = result.get(format)
            assert resource_id is not None
            assert self._is_datastore_resource(resource_id)


class TestDatastoreCreate:

    _mock_records = [
        {"title": "some title", "value": 1},
        {"title": "some title 2", "value": 2},
        {"title": "some title 3", "value": 3},
    ]
    _fields = [
        {"id": "title", "type": "text"},
        {"id": "value", "type": "numeric"},
    ]

    @contextmanager
    def _datastore_records(self, sysadmin, resource, records, fields):
        context = {"user": sysadmin.name, "auth_user_obj": sysadmin}
        datastore_resource = None
        try:
            datastore_resource = helpers.call_action(
                "datastore_create",
                context=context,
                force=True,
                resource_id=resource["id"],
                records=records,
                fields=fields,
            )
            yield datastore_resource
        finally:
            if datastore_resource is not None:
                helpers.call_action(
                    "datastore_delete",
                    context=context,
                    resource_id=resource["id"],
                    force=True,
                )

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_enforces_authorization(self, record_test_name):
        record_test_name("Datastore Create API enforces authorization")
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action("datastore_create")

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_creates_datastore_records(self, record_test_name, sysadmin, resource):
        """
        test that our chained action successfully calls datastore_create
        """
        record_test_name("Datastore Create API creates datastore records")
        with self._datastore_records(
            sysadmin, resource, self._mock_records, self._fields
        ):
            result = helpers.call_action(
                "datastore_search",
                context={},
                resource_id=resource["id"],
                fields=["title", "value"],
            )
        assert result["records"] == self._mock_records

    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_creates_cached_files(self, record_test_name, sysadmin, resource):
        """
        test that datastore cache files get created
        """
        record_test_name("Datastore Create API creates cached records")

        with self._datastore_records(
            sysadmin, resource, self._mock_records, self._fields
        ):
            package = helpers.call_action(
                "package_show",
                id=resource["package_id"],
            )

        resources = package["resources"]
        has_datastore_cache = any(
            resource.get("datastore_cache") is not None for resource in resources
        )
        assert has_datastore_cache


class TestQualityShow:
    
    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_raises_for_missing_package_id(self, record_test_name):
        record_test_name("Data Quality Score API performs validation")

        with pytest.raises(tk.ValidationError):
            # No package_id provided, expect a ValidationError
            helpers.call_action("quality_show")
    
    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_silently_fails_when_dqs_resource_dne(self, record_test_name, mocker):
        # TODO is this the desired behavior? 404 might be more appropriate...
        # 'silent failure' -> harder to detect and debug
        record_test_name(
            "Data Quality Score API fails when DQS resource does not exist"
        )

        mock_dqs_package = {"id": "catalogue-quality-scores", "resources": []}
        mock_actions(mocker, package_show=mock_dqs_package)
        result = helpers.call_action("quality_show", context={}, package_id="any")
        assert result is None
    
    @pytest.mark.ckan_config("ckan.plugins", ["datastore", "iotrans", "extendedapi"])
    @pytest.mark.usefixtures("with_plugins")
    def test_returns_list_of_relevant_datasets_if_score_exists(
        self, record_test_name, mocker
    ):
        record_test_name("Data Quality Score API returns dataset quality scores")

        resource_id = "test-dqs-resource-1234"
        package_id = "test-packge-id-1234"

        mock_dqs_package = {
            "id": "catalogue-quality-scores",
            "resources": [
                {
                    "name": "quality-scores-explanation-codes-and-scores",
                    "id": resource_id,
                }
            ],
        }
        expected_result = [{"package": package_id, "resource_id": resource_id}]
        mock_datastore_search = {
            "records": expected_result
            + [{"package": "not_expected", "resource_id": "test-rid-2"}]
        }

        mock_actions(
            mocker,
            package_show=mock_dqs_package,
            datastore_search=mock_datastore_search,
        )

        result = helpers.call_action("quality_show", context={}, package_id=package_id)
        assert result == expected_result


class TestSearchFacet:
    @staticmethod
    def _get_mock_package_search_response() -> Dict:
        """_get_mock_package_search_response

        :return: A dict that mocks what the response of `package_search` looks like for
          the use case of testing `search_facets`.

          Note: this is intentionally supplied as a function that returns a new object
          each call rather than a constant because `search_facet` mutates this object in
          place. If we were to use a constant this mutation would break test isolation
          (e.g. test 1 runs, mutates this mocked object, then test 2 runs with the
          mocked object which has been modified).

        :rtype: Dict
        """
        # made a method instead of a constant because the search_facet action mutates
        # this object in place (breaks test isolation when multiple tests uses this)

        return {
            "count": 0,
            # We don't really need to mock these
            "facets": {
                "dataset_category": {
                    "Document": 1,
                    "Map": 2,
                    "Table": 3,
                    "Website": 4,
                },
                "formats": {
                    '["ZIP", "JSON", "CSV"]': 1,
                    '["ZIP", "JSON"]': 1,
                    '["ZIP"]': 1,
                },
                # we don't need to mock all of these
                # 'owner_division':{},
                # 'refresh_rate':{},
                # 'civic_issues':{},
                # 'topics':{},
            },
            # A realistic mock given we typically pass `?rows=0`
            "results": [],
            "sort": "score desc, metadata_modified desc",
            "search_facets": {
                "dataset_category": {
                    "title": "dataset_category",
                    "items": [
                        {"name": "Document", "display_name": "Document", "count": 1},
                        {"name": "Map", "display_name": "Map", "count": 2},
                        {"name": "Table", "display_name": "Table", "count": 3},
                        {"name": "Website", "display_name": "Website", "count": 4},
                    ],
                },
                "formats": {
                    "title": "formats",
                    "items": [
                        {
                            "name": '["ZIP", "JSON", "CSV"]',
                            "display_name": '["ZIP", "JSON", "CSV"]',
                            "count": 1,
                        },
                        {
                            "name": '["ZIP", "JSON"]',
                            "display_name": '["ZIP", "JSON"]',
                            "count": 1,
                        },
                        {"name": '["ZIP"]', "display_name": '["ZIP"]', "count": 1},
                    ],
                },
            },
        }

    def _search_facet_with_mock_data(self, mocker, mock_data, data_dict=None):
        mock_actions(mocker, package_search=mock_data)
        if data_dict is None:
            data_dict = {"facet_field[]": ""}
        return helpers.call_action("search_facet", {}, **data_dict)
    
    @pytest.mark.usefixtures("with_plugins")
    def test_returns_valid_json(self, record_test_name, mocker):
        record_test_name("Search Facet API returns valid JSON response")

        mock_data = self._get_mock_package_search_response()
        facet_keys = set(mock_data["facets"].keys())
        search_facet_keys = set(mock_data["search_facets"].keys())
        result = self._search_facet_with_mock_data(mocker, mock_data)
        err_message = "search_facet result is not the correct shape"

        # count
        assert isinstance(result["count"], int), err_message
        # facets
        assert isinstance(result["facets"], dict), err_message
        assert set(result["facets"].keys()) == facet_keys, err_message
        # search_ facets
        assert isinstance(result["search_facets"], dict), err_message
        assert set(result["search_facets"].keys()) == search_facet_keys, err_message
        assert all(
            [
                set(v.keys()) == {"title", "items"}
                for v in result["search_facets"].values()
            ]
        ), err_message
        # sort
        assert isinstance(result["sort"], str), err_message

    @pytest.mark.usefixtures("with_plugins")
    def test_counts_mc_facets_correctly(self, record_test_name, mocker):
        """
        Test that counts for multiple-choice fields (e.g. topics/civic_issues/formats)
        aggregate correctly.
        """
        record_test_name(
            "Search Facet API correctly counts multiple-choice field facets"
        )

        result = self._search_facet_with_mock_data(
            mocker, self._get_mock_package_search_response()
        )
        format_facets = result["search_facets"]["formats"]["items"]

        # 'expected' based on pre-condition in self._mock_package_search_response
        expected_counts = {
            "ZIP": 3,
            "JSON": 2,
            "CSV": 1,
        }

        for format, count in expected_counts.items():
            counts = next(facet for facet in format_facets if facet["name"] == format)
            assert counts["display_name"] == format
            assert counts["count"] == count

    @pytest.mark.usefixtures("with_plugins")
    def test_counts_non_mc_facets_correctly(self, record_test_name, mocker):
        """
        Test that counts for single-response fields (e.g. 'publisher') aggregate'
        correctly.
        """
        record_test_name(
            "Search Facet API correctly counts non-multiple-choice field facets"
        )
        result = self._search_facet_with_mock_data(
            mocker, self._get_mock_package_search_response()
        )
        format_facets = result["search_facets"]["dataset_category"]["items"]

        # 'expected' based on pre-condition in self._mock_package_search_response
        expected_counts = {
            "Document": 1,
            "Map": 2,
            "Table": 3,
            "Website": 4,
        }

        for format, count in expected_counts.items():
            counts = next(facet for facet in format_facets if facet["name"] == format)
            assert counts["display_name"] == format
            assert counts["count"] == count

    @pytest.mark.parametrize(
        "params,expect_errors",
        (
            (dict(), True),  # facet_field[] not provided
            ({"facet_field": "dataset_category"}, True),  # facet_field not correct
            ({"facet_field[]": "topics"}, False),  # correct
        ),
    )
    @pytest.mark.usefixtures("with_plugins")
    def test_param_validation(self, mocker, params: dict, expect_errors):
        def run_test():
            self._search_facet_with_mock_data(
                mocker,
                self._get_mock_package_search_response(),
                params,
            )

        if expect_errors:
            with pytest.raises(tk.ValidationError):
                run_test()
        else:
            run_test()


class TestSearchPackages:
    @staticmethod
    def _is_false(item) -> bool:
        return item in ["False", "false", False] or item is None

    @staticmethod
    def _is_true(item) -> bool:
        return item in ["True", "true", True]

    @staticmethod
    def _find_or_skip(generator, msg: str):
        try:
            return next(generator)
        except StopIteration as exc:
            warn(msg)
            pytest.skip(msg)

    @pytest.mark.depends_on_db(
        "Assumes search terms parametrized below yield some retired datasets and "
        "some non-retired datasets (test case skips if this is not the case)"
    )
    @pytest.mark.integration
    @pytest.mark.parametrize("search", ["water", "services", "year"])
    @pytest.mark.usefixtures("with_plugins")
    def test_retired_last_true_integration(self, search):
        result = helpers.call_action(
            "search_packages", search=search, rows="9999", retired_last="true"
        )
        records = result["results"]

        is_retireds = [record.get("is_retired") for record in records]
        first_is_retired_index = self._find_or_skip(
            (i for i, item in enumerate(is_retireds) if self._is_true(item)),
            (
                f"Skipping integration test as data matching the query {search} does "
                "not match the test conditions"
            ),
        )
        # Assert that "true" (ie is retired) records come last
        assert all(self._is_true(item) for item in is_retireds[first_is_retired_index:])
        assert all(
            self._is_false(item) for item in is_retireds[:first_is_retired_index]
        )

    @pytest.mark.depends_on_db(
        "Assumes search terms parametrized below yield some retired datasets and "
        "some non-retired datasets (test case skips if this is not the case)"
    )
    @pytest.mark.integration
    @pytest.mark.usefixtures("with_plugins")
    def test_retired_last_false_integration(self):
        """
        What we're testing here:
        - when retired_last is set to false we want to ensure we're not overriding
          behavior of search in any way to have retireds filter to the end
        - to test that:
            - set retired_last=false
            - set the sort so that retireds are sorted _first_
            - confirm that the order things come back in are: retired datasets
              first, followed by non retired datasets
        """
        search = "water"
        result = helpers.call_action(
            "search_packages",
            retired_last="false",
            search=search,
            rows="9999",
            sort="or(not(exists(is_retired)),termfreq(is_retired,'false')) asc",
        )
        records = result["results"]
        is_retireds = [record.get("is_retired") for record in records]
        first_not_retired_index = self._find_or_skip(
            (i for i, item in enumerate(is_retireds) if self._is_false(item)),
            (
                f"Skipping integration test as data matching the query {search} does "
                "not match the test conditions"
            ),
        )
        # Assert that is_retired="false" (ie not retired) records come last
        assert all(
            self._is_false(item) for item in is_retireds[first_not_retired_index:]
        )
        assert all(
            self._is_true(item) for item in is_retireds[:first_not_retired_index]
        )

    # Skipped for now as clean_db/local_clean_db fixtures will corrupt the database
    # due to improperly configured table permissions
    # TODO remove or unskip once proper testing database is available
    @pytest.mark.skip
    @pytest.mark.usefixtures("with_request_context")
    @pytest.mark.usefixtures("local_clean_db", "with_plugins")
    @pytest.mark.usefixtures("with_plugins")
    def test_solr_sort_deprioritizes_is_retired(self):

        owner_org = factories.Organization()

        truthy_values = ["true", "True", True]
        falsey_values = ["false", "False", False, None]

        for i, is_retired in enumerate(truthy_values + falsey_values):
            factories.Dataset(
                owner_org=owner_org["id"],
                is_retired=is_retired,
                name=f"Data {i}",
            )

        result = helpers.call_action("search_packages", search="Data")

        # Last (n-truthy) should be the truthy values
        assert all(
            [
                ds["is_retired"] in truthy_values
                for ds in result[-1 * len(truthy_values) :]
            ]
        )

        # First n-falsey should be falsey values
        assert all(
            [ds["is_retired"] in falsey_values for ds in result[: len(falsey_values)]]
        )
