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
)

from ..utils import mock_actions
from .utils import ODP_ADDR, TicketFactory
from .validators import (
    _validate_prepared_intake,
    _validate_ticket,
    _validate_ticket_group,
)

# generate tickets
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1",}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1",}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1",}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Ticket Name": "Ticket 2",}).to_dict()
ticket_3 = TicketFactory({"Ticket Id": "DIA-3", "Ticket Name": "Ticket 3",}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4",}).to_dict()

ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_3, ticket_4]
ticket_ids = [rec["Ticket Id"] for rec in ticket_recs]

#TODO: make a pattern class that
#   groups 
#   links
#   calculates group info
#   filters by each parameter
#   filters by groups of parameters
#       
# It repeats this for different permutations of input tickets
#   No links
#   Some links
#   Missing statuses
#   Missing divisions

# Test grouping by ticket id 
def test_grouping_tickets_by_ticket_id():
    grouped_tickets = group_tickets(ticket_recs, ticket_ids)
    assert len(grouped_tickets.keys()) == 4

# Test linking ticket groups by linked ticket id
def test_linking_tickets_by_linked_ticket_id():
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    print(linked_tickets)
    assert len(linked_tickets.keys()) == 4 

# Test calculating summary stats

# Test filtering by each parameter

# Test filtering by multiple parameters


'''
mock_ticket_groups = {
    ticket_1["Ticket Id"]: {
        "ticket_group_name": ticket_1["Ticket Name"],
        "ticket_group_id": ticket_1["Ticket Id"],
        "details": [ticket_1, ticket_1a, ticket_1b, ticket_multi],
    },
    ticket_2["Ticket Id"]: {
        "ticket_group_name": ticket_2["Ticket Name"],
        "ticket_group_id": ticket_2["Ticket Id"],
        "details": [ticket_2, ticket_multi],
    },
    ticket_3["Ticket Id"]: {
        "ticket_group_name": ticket_3["Ticket Name"],
        "ticket_group_id": ticket_3["Ticket Id"],
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
            ticket_multi["Ticket Id"],
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # strip the "DIA-""
            ticket_multi["Ticket Id"][4:],
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # Add arbitrary padding text
            f'padding:12 {ticket_multi["Ticket Id"]} padding34',
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
        "Ticket Id": "DIA-summarize_new_intake_reports_most_recent_status",
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
        ticket_group_id = tickets[0]["Ticket Id"]
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
        ticket_group_id = tickets[0]["Ticket Id"]
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

        query_key = "Ticket Id" if query_by == "ticket_group_id" else "Ticket Name"
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
    record_test_name(f"Jira Ticket Names are extracted from URLs as expected[{test}]")
    result = _extract_ticket_name(test)
    assert result == expected
'''