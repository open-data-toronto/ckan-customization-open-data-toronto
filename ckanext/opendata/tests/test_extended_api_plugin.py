from warnings import warn

import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest


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
