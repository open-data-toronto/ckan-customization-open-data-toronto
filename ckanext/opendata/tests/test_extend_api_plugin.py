import ckan.tests.factories as factories
from ckan.model import Session, ApiToken, Group, Member, User
import ckan.tests.helpers as helpers
import ckan.logic
import pytest

@pytest.fixture
def org():
    org = factories.Organization()
    yield org
    group_id = org['id']
    group = Session.query(Group).filter_by(id=group_id).one_or_none()
    member = Session.query(Member).filter_by(group_id=group_id).one_or_none()
    Session.delete(member)
    Session.delete(group)
    Session.commit()

@pytest.fixture
def sysadmin():
    sysadmin = factories.Sysadmin()
    yield sysadmin
    user_id = sysadmin['id']
    user = Session.query(User).get(user_id)
    Session.delete(user)

    Session.commit()

@pytest.fixture
def open_data_intake():
    pkg = factories.Dataset(
        id="open-data-intake",
        name='open-data-intake',
        title='Open Data Intake',
        dataset_category="map",
        owner_division="311 Toronto",
        refresh_rate="Daily",
    )
    yield pkg
    pkg_id = pkg['id']
    pkg = Session.query(User).get(pkg_id)
    Session.delete(pkg)
    Session.commit()


import ckan.plugins.toolkit as tk
import ckan.logic as logic

# @pytest.mark.ckan_config('ckan.plugins','extendedapi')
def test_summarize_new_intake(open_data_intake):
    context = {}

    data = {
        "query": "something"
    }
    data = {}
    # with pytest.raises(ckan.logic.ValidationError):

    # action = logic.get_action('summarize_new_intake')
    # result = action(context, **data)

    # result = tk.get_action('summarize_new_intake')(context, data)
    result = helpers.call_action('summarize_new_intake', context, **data)
    # result = helpers.call_action('package_create', context, **data)

    breakpoint()
