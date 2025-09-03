from datetime import datetime, timedelta
from typing import List, Optional

import ckan.tests.helpers as helpers
import pytest

from ckanext.opendata.util.intake.types import (
    PreparedIntake,
    Ticket,
    TicketGroup
)

from ckanext.opendata.util.intake.utils import(
    group_tickets,
    join_linked_tickets,
    summarize_intake,
)

from ..utils import mock_actions
from .utils import ODP_ADDR, TicketFactory
from .validators import (
    _validate_prepared_intake,
    _validate_ticket,
    _validate_ticket_group,
)

# useful vars
yesterday = datetime.strftime(datetime.today() - timedelta(days=1), "%Y-%m-%dT%H:%M:%S")
two_days_ago = datetime.strftime(datetime.today() - timedelta(days=2), "%Y-%m-%dT%H:%M:%S")
one_year_ago = datetime.strftime(datetime.today() - timedelta(days=365), "%Y-%m-%dT%H:%M:%S")

### generate test data

# basic group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1","Created": two_days_ago, "Ticket Resolved?": "true"}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1","Created": two_days_ago, "Ticket Resolved?": "true"}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Created": two_days_ago, "Status Timestamp": yesterday, "Ticket Resolved?": "true"}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1"}).to_dict()
ticket_3 = TicketFactory({"Ticket Id": "DIA-3", "Ticket Name": "Ticket 3","Created": one_year_ago, "Request Type": "type2"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "To Status": "WIP"}).to_dict()

basic_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_3, ticket_4]
basic_ticket_ids = [rec["Ticket Id"] for rec in basic_ticket_recs]
basic_correct_vals = {
    "grouped_ticket_count": 4,
    "linked_ticket_count": 4,
    "tickets_one_day_old_count": 1,
    "tickets_resolved_yesterday_or_unresolved_count": 3,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 3,
}

# linked group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1"}).to_dict()
ticket_3 = TicketFactory({"Ticket Id": "DIA-3", "Ticket Name": "Ticket 3","Created": one_year_ago, "To Status": "WIP"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "Request Type": "type2"}).to_dict()
ticket_5 = TicketFactory({"Ticket Id": "DIA-5", "Ticket Name": "Ticket 5","Created": one_year_ago}).to_dict()

linked_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_3, ticket_4, ticket_5]
linked_ticket_ids = [rec["Ticket Id"] for rec in linked_ticket_recs]
linked_correct_vals = {
    "grouped_ticket_count": 5,
    "linked_ticket_count": 4,
    "tickets_one_day_old_count": 1,
    "tickets_resolved_yesterday_or_unresolved_count": 4,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 4,
}

# another linked group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": None}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": None}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": "done"}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1", "category": None}).to_dict()
ticket_2a = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1", "category": "done"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "Request Type": "type2", "Ticket Resolved?": "true"}).to_dict()

more_linked_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_2a, ticket_4]
more_linked_ticket_ids = [rec["Ticket Id"] for rec in more_linked_ticket_recs]
more_linked_correct_vals = {
    "grouped_ticket_count": 3,
    "linked_ticket_count": 2,
    "tickets_one_day_old_count": 0,
    "tickets_resolved_yesterday_or_unresolved_count": 1,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 1,
}

#TODO: make tests that
#   groups, checks number of groups
#   links, checks number of linked groups
#   calculates group info, checks its correct
#   filters by each parameter, checks count of returned groups
#   filters by groups of parameters, checks count of returned groups
#       
# It repeats this for different permutations of input tickets
#   No links
#   Some links
#   Different ticket attributes

pytestmark = pytest.mark.parametrize(
    "ticket_recs,ticket_ids,correct_vals", 
    [
        (basic_ticket_recs, basic_ticket_ids, basic_correct_vals),
        (linked_ticket_recs, linked_ticket_ids, linked_correct_vals),
        (more_linked_ticket_recs, more_linked_ticket_ids, more_linked_correct_vals),
    ]
)


# Test grouping by ticket_id 
def test_grouping_tickets_by_ticket_id(ticket_recs, ticket_ids, correct_vals):
    grouped_tickets = group_tickets(ticket_recs, ticket_ids)
    assert len(grouped_tickets.keys()) == correct_vals["grouped_ticket_count"]

# Test linking ticket groups by linked ticket_id
def test_linking_tickets_by_linked_ticket_id(ticket_recs, ticket_ids, correct_vals):
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    assert len(linked_tickets.keys()) == correct_vals["linked_ticket_count"]

# Test calculating summary stats
def test_creating_summarized_intake(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {}
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)      
    assert isinstance(summarized_intake.get("all_statuses", False), list)
    assert isinstance(summarized_intake.get("all_request_types", False), list)
    assert isinstance(summarized_intake.get("all_divisions", False), list)

# Test filtering by each parameter
def test_filtering_on_ticket_id(ticket_recs, ticket_ids, correct_vals):
    # test with exact ticket_id
    status_definitions = {}
    data_dict = {"ticket_id":"DIA-1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

    # test with imprecise ticket_id
    data_dict = {"ticket_id":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

def test_filtering_max_age(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"max_age":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["tickets_one_day_old_count"]

def test_filtering_max_days_since_resolution(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"max_days_since_resolution":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["tickets_resolved_yesterday_or_unresolved_count"]

def test_filtering_name(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"name":"Ticket 4"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

def test_filtering_one_type(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"type":"type1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_tickets_count"]

def test_filtering_two_types(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"type":"type1~type2"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_and_type2_tickets_count"]

def test_filtering_status(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"status":"the_active_status"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_and_type2_tickets_count"]

def test_filtering_status(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"resolved":"false"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["unresolved_ticket_count"]
 

# Test filtering by multiple parameters


'''
mock_ticket_groups = {
    ticket_1["ticket_id"]: {
        "ticket_group_name": ticket_1["ticket_name"],
        "ticket_group_id": ticket_1["ticket_id"],
        "details": [ticket_1, ticket_1a, ticket_1b, ticket_multi],
    },
    ticket_2["ticket_id"]: {
        "ticket_group_name": ticket_2["ticket_name"],
        "ticket_group_id": ticket_2["ticket_id"],
        "details": [ticket_2, ticket_multi],
    },
    ticket_3["ticket_id"]: {
        "ticket_group_name": ticket_3["ticket_name"],
        "ticket_group_id": ticket_3["ticket_id"],
        "details": [ticket_3],
    },
}


@pytest.mark.parametrize("search", ["Ticket", "ticket", "TiCkEt"])
def test_summarize_new_intake_search_str(record_test_name, search, mocker):
    record_test_name(f"Summarize New Intake API accepts a search parameter[{search}]")

    context = {}
    data = {"search": search}
    mock_actions(mocker, prepare_intake={"new": mock_ticket_groups})
    result = helpers.call_action("summarize_new_intake", context, **data)
    assert len(result) == 3
    assert all(t["ticket_group_name"].startswith("Ticket") for t in result)


def test_summarize_new_intake_accepts_empty_search(record_test_name, mocker):
    record_test_name("Summarize New Intake API accepts no search parameter")

    context = {}
    data = {}

    mock_actions(mocker, prepare_intake={"new": mock_ticket_groups})
    result = helpers.call_action("summarize_new_intake", context, **data)
    assert len(result) == len(mock_ticket_groups)


@pytest.mark.parametrize(
    "ticket_id,expected_ticket_groups",
    [
        (
            ticket_multi["ticket_id"],
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # strip the "DIA-""
            ticket_multi["ticket_id"][4:],
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # Add arbitrary padding text
            f'padding:12 {ticket_multi["ticket_id"]} padding34',
            {"Ticket 1", "Ticket 2"},
        ),
        (
            "9999999",
            set(),
        ),
    ],
)
def test_summarize_new_intake_accepts_ticket_number_in_search(
    record_test_name,
    mocker,
    ticket_id,
    expected_ticket_groups,
):
    record_test_name(
        f"Summarize New Intake API accepts ticket number in search[{ticket_id}]"
    )
    context = {}
    data = {"search": ticket_id}

    mock_actions(mocker, prepare_intake={"new": mock_ticket_groups})

    result = helpers.call_action("summarize_new_intake", context, **data)

    result_ticket_names = [intake["ticket_group_name"] for intake in result]
    assert set(result_ticket_names) == expected_ticket_groups


def test_summarize_new_intake_reports_most_recent_status(record_test_name, mocker):
    record_test_name("Detail New Intake API indicates the most recent status")
    ticket_defaults = {
        "ticket_id": "DIA-summarize_new_intake_reports_most_recent_status",
        "Request Type": "Make Open Data Inquiry",
    }

    # Must use `now` as a time reference as internals filter out old (age>30) tickets
    now = datetime.now()
    ymd_hms = "%Y-%m-%dT%H:%M:%S"

    t1 = TicketFactory(
        {
            **ticket_defaults,
            "To Status": "Initiating",
            "Status Timestamp": (now - timedelta(days=1)).strftime(ymd_hms),
        }
    ).to_dict()
    last_status = "Closed"
    t2 = TicketFactory(
        {
            **ticket_defaults,
            "To Status": last_status,
            "Status Timestamp": now.strftime(ymd_hms),
        }
    ).to_dict()

    tickets = [t1, t2]
    mocker.patch(
        "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
    )
    result = helpers.call_action("summarize_new_intake", {})

    # expecting t2's status to be returned as t2 is after t1
    assert result[0]["status"] == last_status


class TestIntakeActions:
    def _mock_tickets(self, ticket_kwargs: Optional[Ticket] = None) -> List[Ticket]:
        return [TicketFactory(ticket_kwargs).to_dict() for _ in range(10)]

    #################
    # Summarize new #
    #################

    def test_summarize_new_intake(self, record_test_name, mocker):
        record_test_name("Summarize New Intake API returns a valid JSON response")
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            #{"Request Type": RequestType.PUBLISH_NEW_OPEN_DATASET_PAGE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        summarized_intakes: List[SummarizedIntake] = helpers.call_action(
            "summarize_new_intake",
            {},
        )
        for intake in summarized_intakes:
            validate_summarized_intake(intake)

    ##############
    # Detail new #
    ##############

    def test_detail_new_intake_repeat_statuses(self, record_test_name, mocker):
        record_test_name(
            "Detail New Intake API returns a valid JSON response when only a single ticket status is repeated"
        )

        t1 = TicketFactory(
            {
                "To Status": "Initiating",
                "Status Timestamp": "2024-01-01T11:00:0",
            }
        ).to_dict()
        t2 = TicketFactory(
            {
                "To Status": "Exploring",
                "Status Timestamp": "2024-01-02T11:00:0",
            }
        ).to_dict()
        t3 = TicketFactory(
            {
                "To Status": "Closed",
                "Status Timestamp": "2024-01-03T11:00:0",
            }
        ).to_dict()
        t4 = TicketFactory(
            {
                "To Status": "Exploring",
                "Status Timestamp": "2024-01-04T11:00:0",
            }
        ).to_dict()

        tickets = [t1, t2, t3, t4]

        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        ticket_group_id = tickets[0]["ticket_id"]
        result: DetailedIntake = helpers.call_action(
            "detail_new_intake", {}, ticket_group_id=ticket_group_id
        )
        validate_detailed_intake(result)

    def test_detail_new_intake_multiple_repeats(self, record_test_name, mocker):
        record_test_name(
            "Detail New Intake API returns a valid JSON response when many ticket statuses are repeated"
        )

        t1 = TicketFactory(
            {
                "To Status": "Initiating",
                "Status Timestamp": "2024-01-01T11:00:0",
            }
        ).to_dict()
        t2 = TicketFactory(
            {
                "To Status": "Exploring",
                "Status Timestamp": "2024-01-02T11:00:0",
            }
        ).to_dict()
        t3 = TicketFactory(
            {
                "To Status": "Closed",
                "Status Timestamp": "2024-01-03T11:00:0",
            }
        ).to_dict()
        t4 = TicketFactory(
            {
                "To Status": "Exploring",
                "Status Timestamp": "2024-01-04T11:00:0",
            }
        ).to_dict()
        t5 = TicketFactory(
            {
                "To Status": "Waiting on Open Data",
                "Status Timestamp": "2024-01-05T11:00:0",
            }
        ).to_dict()
        t6 = TicketFactory(
            {
                "To Status": "Initiating",
                "Status Timestamp": "2024-01-06T11:00:0",
            }
        ).to_dict()

        tickets = [t1, t2, t3, t4, t5, t6]

        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        ticket_group_id = tickets[0]["ticket_id"]
        result: DetailedIntake = helpers.call_action(
            "detail_new_intake", {}, ticket_group_id=ticket_group_id
        )
        validate_detailed_intake(result)

    ###################
    # Detail existing #
    ###################

    @pytest.mark.parametrize("query_by", ("ticket_group_id", "ticket_group_name"))
    def test_detail_existing_intake(self, record_test_name, query_by, mocker):
        record_test_name(f"Detail Existing Intake API can be queried by {query_by}")
        tickets = self._mock_tickets(
            # ensure there are mocked 'existing' tickets
            #{"Request Type": RequestType.UPDATE_EXISTING_OPEN_DATASET_PAGE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )

        query_key = "ticket_id" if query_by == "ticket_group_id" else "ticket_name"
        query = {query_by: tickets[0][query_key]}

        result: DetailedIntake = helpers.call_action(
            "detail_existing_intake", {}, **query
        )
        validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id_not_found(
        self, mocker, record_test_name
    ):
        record_test_name(
            "Detail Existing Intake API returns proper error message when not found"
        )

        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=[]
        )
        ticket_group_name = "dne"
        result = helpers.call_action(
            "detail_existing_intake", {}, ticket_group_name=ticket_group_name
        )
        # TODO if spec changes to expect 404
        # with pytest.raises(NotFound):
        #     helpers.call_action(
        #         "detail_existing_intake", {}, ticket_group_name=ticket_group_name
        #     )
        assert result == "Not found"

    ##################
    # prepare intake #
    ##################

    def test_prepare_intake(self, record_test_name, mocker):
        record_test_name("Prepare Intake API returns a valid JSON resposne")
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=self._mock_tickets(),
        )
        result = helpers.call_action("prepare_intake", {})
        validate_prepared_intake(result)


@pytest.mark.parametrize(
    "test,expected",
    [
        (f"{ODP_ADDR}/ticket-name/", "ticket-name"),
        (f"{ODP_ADDR}/ticket-name", "ticket-name"),
        (f"/ticket-name", "/ticket-name"),
        (f"/ticket-name/", "/ticket-name/"),
        ("ticket w special characters !%^&*", "ticket w special characters !%^&*"),
    ],
)
def test_extract_ticket_name(record_test_name, test, expected):
    record_test_name(f"Jira ticket_names are extracted from URLs as expected[{test}]")
    result = _extract_ticket_name(test)
    assert result == expected
'''