from warnings import warn

import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest


@pytest.mark.integration
@pytest.mark.depends_on_db(
    "Assumes search terms parametrized below yield some retired datasets and "
    "some non-retired datasets (test case skips if this is not the case)"
)
@pytest.mark.parametrize("search", ["water", "services", "year"])
def test_solr_sort_deprioritizes_is_retired_integration(search):
    query = {"search": search, "rows": "9999"}

    result = helpers.call_action("search_packages", **query)
    records = result["results"]

    is_retireds = [record.get("is_retired") for record in records]

    is_false = lambda x: x in ["False", "false", False] or x is None
    is_true = lambda x: x in ["True", "true", True]

    try:
        first_is_retired_index = next(
            i for i, item in enumerate(is_retireds) if is_true(item)
        )
    except StopIteration as exc:
        msg = (
            f"Skipping integration test as data matching the query {query} does "
            "not match the test conditions"
        )
        warn(msg)
        pytest.skip(msg)

    # Assert that "true" (ie is retired) records come last
    assert all(is_true(item) for item in is_retireds[first_is_retired_index:])
    assert all(is_false(item) for item in is_retireds[:first_is_retired_index])


# Skipped for now as clean_db/local_clean_db fixtures will corrupt the database
# due to improperly configured table permissions
# TODO remove or unskip once proper testing database is available
@pytest.mark.skip
@pytest.mark.usefixtures("with_request_context")
class TestExtendedApiPlugin:
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
