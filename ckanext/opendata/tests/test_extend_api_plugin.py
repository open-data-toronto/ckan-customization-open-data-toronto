import ckan.tests.helpers as helpers
import pytest
from typing import Dict, Optional, List
from ckanext.opendata.util.intake import Ticket, PreparedIntake, UPDATE_TICKET_REQUEST_TYPE, DetailedIntake
from datetime import datetime

class MockIntake:
    __count = 0

    def __init__(
        self,
        ticket_id: str,
        ticket_name: str,
        _id: Optional[int] = None,
        inquiry_source: str = "",
        request_type: str = "",
        created: str = "1970-01-01T12:00:00",
        first_response: str = "",
        from_status: str = "",
        to_status: str = "",
        status_timestamp: str = "1970-01-01T12:00:00",
        linked_ticket_id: str = "",
        division: str = "",
        description: str = "",
    ):
        if _id is None:
            self._id = self.__count
        else:
            self._id = _id
        self.__count += 1
        self.ticket_id = ticket_id
        self.ticket_name = ticket_name
        self.inquiry_source = inquiry_source
        self.request_type = request_type
        self.created = created
        self.first_response = first_response
        self.from_status = from_status
        self.to_status = to_status
        self.status_timestamp = status_timestamp
        self.linked_ticket_id = linked_ticket_id
        self.division = division
        self.description = description

    def to_dict(self) -> Dict:
        return {
            "_id": self._id,
            "Ticket Id": self.ticket_id,
            "Ticket Name": self.ticket_name,
            "Inquiry Source": self.inquiry_source,
            "Request Type": self.request_type,
            "Created": self.created,
            "First Response": self.first_response,
            "From Status": self.from_status,
            "To Status": self.to_status,
            "Status Timestamp": self.status_timestamp,
            "Linked Ticket Id": self.linked_ticket_id,
            "Division": self.division,
            "Description": self.description,
        }


ticket_1 = MockIntake(ticket_id="DIA-1", ticket_name="Ticket 1").to_dict()
ticket_1a = MockIntake(ticket_id="DIA-1a", ticket_name="Ticket 1").to_dict()
ticket_1b = MockIntake(ticket_id="DIA-1b", ticket_name="Ticket 1").to_dict()
ticket_2 = MockIntake(ticket_id="DIA-2", ticket_name="Ticket 2").to_dict()
ticket_3 = MockIntake(ticket_id="DIA-3", ticket_name="Ticket 3").to_dict()
ticket_multi = MockIntake(ticket_id="DIA-4", ticket_name="Ticket Multi").to_dict()

mock_intake_items = {
    "Ticket Group 1": [ticket_1, ticket_1a, ticket_1b, ticket_multi],
    "Ticket Group 2": [ticket_2, ticket_multi],
    "Ticket Group 3": [ticket_3],
    "Other Group 3": [ticket_3],
}


@pytest.mark.parametrize("search", ["Ticket", "ticket", "TiCkEt"])
def test_summarize_new_intake_search_str(search, mocker):
    context = {}
    data = {"search": search}

    mocked_prepare_intake_action = lambda *args, **kwargs: {"new": mock_intake_items}

    mocker.patch(
        "opendata.api.tk.get_action", return_value=mocked_prepare_intake_action
    )
    result = helpers.call_action("summarize_new_intake", context, **data)
    assert len(result) == 3
    assert all(t["ticket_group_name"].startswith("Ticket Group ") for t in result)


def test_summarize_new_intake_accepts_empty_search(mocker):
    context = {}
    data = {}
    mocked_prepare_intake_action = lambda *args, **kwargs: {"new": mock_intake_items}
    mocker.patch(
        "opendata.api.tk.get_action", return_value=mocked_prepare_intake_action
    )
    result = helpers.call_action("summarize_new_intake", context, **data)
    assert len(result) == len(mock_intake_items)


@pytest.mark.parametrize(
    "ticket_id,expected_ticket_groups",
    [
        (
            ticket_multi["Ticket Id"],
            {"Ticket Group 1", "Ticket Group 2"},
        ),
        (
            # strip the "DIA-""
            ticket_multi["Ticket Id"][4:],
            {"Ticket Group 1", "Ticket Group 2"},
        ),
        (
            # Add arbitrary padding text
            f'other things here {ticket_multi["Ticket Id"]} numbers too 12',
            {"Ticket Group 1", "Ticket Group 2"},
        ),
        (
            "9999999",
            set(),
        ),
    ],
)
def test_summarize_new_intake_accepts_ticket_number_in_search(
    mocker,
    ticket_id,
    expected_ticket_groups,
):
    context = {}
    data = {"search": ticket_id}

    mocked_prepare_intake_action = lambda *args, **kwargs: {"new": mock_intake_items}
    mocker.patch(
        "opendata.api.tk.get_action", return_value=mocked_prepare_intake_action
    )

    result = helpers.call_action("summarize_new_intake", context, **data)

    result_ticket_names = [intake["ticket_group_name"] for intake in result]
    assert set(result_ticket_names) == expected_ticket_groups


class TicketFactory:
    _n = 0

    def __init__(self, ticket_values:Ticket=None):
        if ticket_values is None:
            ticket_values = {}
        _id = self._n
        self._n +=1
        defaults = {
            "_id": f"{_id}",
            "Ticket Id": f"DIA-{_id}",
            "Ticket Name": f"Ticket Name {_id}",
            "Inquiry Source": "Inq Source",
            "Request Type": "Publish New Open Dataset Page",
            "Created": "2024-01-01T11:00:0",
            "First Response": "2024-01-01T11:00:0",
            "From Status": None,
            "To Status": None,
            "Status Timestamp": None,
            "Linked Ticket Id": "",
        }
        self._value = {**defaults, **ticket_values}
    
    def to_dict(self) -> Ticket:
        return self._value



from opendata.util.intake import Intakes, GroupedEntry, Ticket

def _validate_ticket(ticket:Ticket):
    assert isinstance(ticket["_id"], str)
    assert isinstance(ticket["Ticket Id"], str)
    assert isinstance(ticket["Ticket Name"], str)
    assert isinstance(ticket["Inquiry Source"], str)
    assert isinstance(ticket.get("Division"), str) or ticket.get("Division")is None
    assert isinstance(ticket["Request Type"], str)
    assert isinstance(ticket["Created"], str)
    assert isinstance(ticket.get("First Response"), str) or ticket.get("First Response")is None
    assert isinstance(ticket.get("From Status"), str) or ticket.get("From Status")is None
    assert isinstance(ticket.get("To Status"), str) or ticket.get("To Status")is None
    assert isinstance(ticket.get("Status Timestamp"), str) or ticket.get("Status Timestamp")is None
    assert isinstance(ticket["Linked Ticket Id"], str)


def _validate_grouped(grouped_entry:GroupedEntry):
    assert isinstance(grouped_entry["ticket_group_id"], str)
    assert isinstance(grouped_entry["ticket_group_name"], str)
    for ticket in grouped_entry["tickets"]:
        _validate_ticket(ticket)

def _validate_intake(intake:Intakes):
    for _, grouped_entry in intake.items():
        _validate_grouped(grouped_entry)

def _validate_prepared_intake(prepared_intake:PreparedIntake):
    _validate_intake(prepared_intake["existing"])
    _validate_intake(prepared_intake["new"])

class TestIntakeActions:

    def _mock_tickets(self, ticket_kwargs:Optional[Ticket]=None) -> List[Ticket]:
        return [
            TicketFactory(ticket_kwargs).to_dict() for _ in range(10)
        ]

    def test_summarize_new_intake(self):
        pass

    def test_detail_new_intake(self):
        pass

    def test_detail_existing_intake(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            {"Request Type": UPDATE_TICKET_REQUEST_TYPE}
        )
        mocker.patch(
            "ckanext.opendata.api._get_intake_tickets",
            return_value=tickets
        )
        ticket_group_id = tickets[0]["Ticket Id"]
        result:DetailedIntake = helpers.call_action(
            "detail_existing_intake",
            {},
            ticket_group_id=ticket_group_id
        )

        assert isinstance(result["divisions"], list)
        assert isinstance(result.get("description"), str) or result.get("description") is None
        assert isinstance(result["ticket_group_name"], str)
        assert isinstance(result["last_update"], datetime)
        assert isinstance(result["jira_ticket_ids"], list)
        assert isinstance(result["inquiry_source"], list)
        assert isinstance(result["request_types"], list)
        assert isinstance(result["to_statuses"], list)
        assert isinstance(result["from_statuses"], list)
        assert isinstance(result["details"], list)

        
        # _validate_prepared_intake(result)

    def test_prepare_intake(self, mocker):
        mocker.patch(
            "ckanext.opendata.api._get_intake_tickets",
            return_value=self._mock_tickets()
        )
        result = helpers.call_action("prepare_intake", {})
        _validate_prepared_intake(result)

from opendata.api import _get_intake_tickets