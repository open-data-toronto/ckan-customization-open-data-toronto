from typing import Dict, Generator

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest
from ckan.model import Session, User
from ckanapi import LocalCKAN

from .constants import SCHEMING_MOCK_TEST_OPTIONS


# Require that when @pytest.mark.depends_on_db fixture is used, a comment is provided
# to specify what is required in the db for that integration test to function.
def pytest_collection_modifyitems(config, items):
    for item in items:
        marker = item.get_closest_marker("depends_on_db")
        if marker:
            reason = marker.kwargs.get("reason", marker.args[0])
            if not reason:
                pytest.fail(f"depends_on_db marker needs a reason, but got: {reason}")

            item.user_properties.append(("depends_on_db", reason))


def pytest_report_header(config):
    return "Tests depending on particular DB items to be present are marked with `depends_on_db`"


def pytest_itemcollected(item):
    marker = item.get_closest_marker("depends_on_db")
    if marker:
        reason = marker.kwargs.get("reason", marker.args[0])
        item.add_marker(pytest.mark.usefixtures("depends_on_db"))
        item._nodeid += f" [depends_on_db: {reason}]"


################################################################################
# Fixtures                                                                     #
################################################################################


@pytest.fixture(scope="session")
def sysadmin() -> Generator[Dict, None, None]:
    sysadmin = factories.Sysadmin()
    yield sysadmin
    # unfortunately there is no user_purge action and user_delete is a
    # soft-delete. So instead we manually delete the user.
    # Not ideal as we may bypass any plugins modifying this behavior
    user_id = sysadmin["id"]
    user = Session.query(User).get(user_id)
    Session.delete(user)
    Session.commit()


@pytest.fixture(scope="session")
def org(sysadmin: Dict) -> Generator[Dict, None, None]:
    context = {"user": sysadmin["name"]}
    org_dict = factories.Organization()
    yield org_dict
    helpers.call_action("organization_purge", context=context, id=org_dict["id"])


@pytest.fixture(scope="session")
@pytest.mark.depends_on_db(
    "relies on datastore choices for dataset_category, owner_division, and "
    "refresh_rate"
)
def package(sysadmin: Dict) -> Generator[Dict, None, None]:
    context = {"user": sysadmin["name"]}
    kwargs = {
        "name": "ckanext-scheming-test-dataset",
        "notes": "Test dataset from scheming plugin. This should be cleaned up "
        "and removed automatically by test fixtures.",
        "title": "Scheming Test Dataset",
        # DB depends:
        "dataset_category": "Document",
        "owner_division": "311 Toronto",
        "refresh_rate": "Daily",
    }
    package_dict = helpers.call_action("package_create", context=context, **kwargs)
    yield package_dict
    helpers.call_action("dataset_purge", context=context, id=package_dict["id"])


@pytest.fixture(scope="session")
def topics_resource(sysadmin: Dict) -> Generator[Dict, None, None]:
    lc = LocalCKAN(username=sysadmin["name"])

    resource_alias = "topics"
    search = lc.action.datastore_search(resource_id=resource_alias)
    resource_id = search["resource_id"]
    created_test_options = lc.action.datastore_upsert(
        resource_id=resource_id,
        records=SCHEMING_MOCK_TEST_OPTIONS,
        method="insert",
        force=True,
    )
    yield created_test_options["records"]
    for option in SCHEMING_MOCK_TEST_OPTIONS:
        lc.action.datastore_delete(
            resource_id=resource_id,
            filters={"value": option["value"]},
            force=True,
        )
