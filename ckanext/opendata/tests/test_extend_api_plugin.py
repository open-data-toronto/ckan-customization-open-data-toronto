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


@pytest.mark.parametrize(
        "query",
        ["events","event","EvEnT"]
)
def test_summarize_new_intake_uses_query(query):
    context = {}
    data = {"query": query}
    result = helpers.call_action('summarize_new_intake', context, **data)
    assert len(result) == 1
    assert result[0]['ticket_group_name'] == 'Events at Nathan Phillips Square'

def test_summarize_new_intake_accepts_no_query():
    context = {}
    data = {}
    result = helpers.call_action('summarize_new_intake', context, **data)
    assert len(result) == 22

def test_summarize_new_intake_accepts_ticket_number_query():
    context = {}
    ticket_id = "343"
    data = {"query": ticket_id}
    result = helpers.call_action('summarize_new_intake', context, **data)

    assert all([
        (
            f"DIA-{ticket_id}" in intake['ticket_ids']
            or str(ticket_id) in intake["ticket_group_name"]
        )
            for intake in result
    ])
