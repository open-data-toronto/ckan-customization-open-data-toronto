import ckan.tests.helpers as helpers
import pytest
from typing import Dict, Optional, List, Any
from ckanext.opendata.util.intake.types import Ticket, PreparedIntake, UPDATE_TICKET_REQUEST_TYPE, DetailedIntake, SummarizedIntake
from datetime import datetime
from ckan.logic import NotFound
from ckanext.opendata.util.intake.utils import _extract_ticket_name
from ckanext.opendata.util.intake.types import Intakes, GroupedEntry, Ticket


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
    ticket_1["Ticket Id"]: {
        "ticket_group_name": ticket_1["Ticket Name"],
        "ticket_group_id": ticket_1["Ticket Id"],
        "tickets": [ticket_1, ticket_1a, ticket_1b, ticket_multi]
    },
    ticket_2["Ticket Id"]: {
        "ticket_group_name": ticket_2["Ticket Name"],
        "ticket_group_id": ticket_2["Ticket Id"],
        "tickets": [ticket_2, ticket_multi]
    },
    ticket_3["Ticket Id"]: {
        "ticket_group_name": ticket_3["Ticket Name"],
        "ticket_group_id": ticket_3["Ticket Id"],
        "tickets": [ticket_3]
    },
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
    assert all(t["ticket_group_name"].startswith("Ticket") for t in result)


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
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # strip the "DIA-""
            ticket_multi["Ticket Id"][4:],
            {"Ticket 1", "Ticket 2"},
        ),
        (
            # Add arbitrary padding text
            f'other things here {ticket_multi["Ticket Id"]} numbers too 12',
            {"Ticket 1", "Ticket 2"},
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
        _id = self._get_id()
        defaults:Ticket = {
            "_id": f"{_id}",
            "Created": "2024-01-01T11:00:0",
            "Division": None,
            "First Response": "2024-01-01T11:00:0",
            "From Status": None,
            "Inquiry Source": "Inq Source",
            "Linked Ticket Id": "",
            "Public Description": "",
            "Request Type": "Publish New Open Dataset Page",
            "Status Timestamp": None,
            "Ticket Id": f"DIA-{_id}",
            "Ticket Name": f"Ticket Name {_id}",
            "To Status": None,
        }
        self._value = {**defaults, **ticket_values}

    @classmethod
    def _get_id(cls) -> int:
        id_value = cls._n
        cls._n += 1
        return id_value

    def to_dict(self) -> Ticket:
        return self._value

def _is_optional_str(s:Any) -> bool:
    return isinstance(s, str) or s is None


def _validate_ticket(ticket:Ticket):
    assert isinstance(ticket["_id"], str)
    assert isinstance(ticket["Ticket Id"], str)
    assert isinstance(ticket["Ticket Name"], str)
    assert isinstance(ticket["Inquiry Source"], str)
    assert _is_optional_str(ticket.get("Division"))
    assert isinstance(ticket["Request Type"], str)
    assert isinstance(ticket["Created"], str)
    assert _is_optional_str(ticket.get("First Response"))
    assert _is_optional_str(ticket.get("From Status"))
    assert _is_optional_str(ticket.get("To Status"))
    assert _is_optional_str(ticket.get("Status Timestamp"))
    assert isinstance(ticket["Linked Ticket Id"], str)
    assert _is_optional_str(ticket.get("Public Description"))


def _validate_grouped(grouped_entry:GroupedEntry):
    assert isinstance(grouped_entry["ticket_group_id"], str)
    assert isinstance(grouped_entry["ticket_group_name"], str)
    assert _is_optional_str(grouped_entry.get("public_description"))

    for ticket in grouped_entry["tickets"]:
        _validate_ticket(ticket)

def _validate_intake(intake:Intakes):
    for _, grouped_entry in intake.items():
        _validate_grouped(grouped_entry)

def _validate_prepared_intake(prepared_intake:PreparedIntake):
    _validate_intake(prepared_intake["existing"])
    _validate_intake(prepared_intake["new"])

def _validate_detailed_intake(intake:DetailedIntake):
    assert isinstance(intake["divisions"], list)
    assert isinstance(intake.get("description"), str) or intake.get("description") is None
    assert isinstance(intake["ticket_group_name"], str)
    assert isinstance(intake["ticket_group_id"], str)
    assert isinstance(intake["last_update"], datetime)
    assert isinstance(intake["jira_ticket_ids"], list)
    assert isinstance(intake["inquiry_source"], list)
    assert isinstance(intake["request_types"], list)
    assert isinstance(intake["to_statuses"], list)
    assert isinstance(intake["from_statuses"], list)
    assert isinstance(intake["details"], list)

def _validate_summarized_intake(intake:SummarizedIntake):
    assert isinstance(intake.get('description'), str) or intake.get('description') is None
    assert isinstance(intake.get('ticket_group_id', None), str)
    assert isinstance(intake.get('ticket_group_name',None), str)
    assert isinstance(intake.get('ticket_ids',None), List)
    assert all(isinstance(tid, str) and tid != "" for tid in intake["ticket_ids"])
    assert isinstance(intake.get('last_updated',None), datetime)
    assert isinstance(intake.get('status',None), str)
    assert isinstance(intake.get('inquiry_source',None), str)
    assert isinstance(intake.get('ticket_count',None), int)


class TestIntakeActions:

    def _mock_tickets(self, ticket_kwargs:Optional[Ticket]=None) -> List[Ticket]:
        return [
            TicketFactory(ticket_kwargs).to_dict() for _ in range(10)
        ]

    def test_summarize_new_intake(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            {"Request Type": "Publish New Open Dataset Page"}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=tickets
        )
        summarized_intakes:List[SummarizedIntake] = helpers.call_action(
            "summarize_new_intake",
            {},
        )
        for intake in summarized_intakes:
            _validate_summarized_intake(intake)

    def test_detail_new_intake(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            {"Request Type": "Publish New Open Dataset Page"}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=tickets
        )
        ticket_group_id = tickets[0]["Ticket Id"]
        result:DetailedIntake = helpers.call_action(
            "detail_new_intake",
            {},
            ticket_group_id=ticket_group_id
        )
        _validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'existing' tickets
            {"Request Type": UPDATE_TICKET_REQUEST_TYPE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=tickets
        )
        ticket_group_id = tickets[0]["Ticket Id"]
        result:DetailedIntake = helpers.call_action(
            "detail_existing_intake",
            {},
            ticket_group_id=ticket_group_id
        )
        _validate_detailed_intake(result)
    
    def test_detail_existing_intake_by_group_id(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'existing' tickets
            {"Request Type": UPDATE_TICKET_REQUEST_TYPE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=tickets
        )
        ticket_group_name = tickets[0]["Ticket Name"]
        result:DetailedIntake = helpers.call_action(
            "detail_existing_intake",
            {},
            ticket_group_name=ticket_group_name
        )
        _validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id(self, mocker):
        mocker.patch("ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=[])
        ticket_group_name = 'dne'
        with pytest.raises(NotFound):
            helpers.call_action(
                "detail_existing_intake",
                {},
                ticket_group_name=ticket_group_name
            )

    def test_prepare_intake(self, mocker):
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=self._mock_tickets()
        )
        result = helpers.call_action("prepare_intake", {})
        _validate_prepared_intake(result)



ODP_ADDR = "https://open.toronto.ca/dataset"
@pytest.mark.parametrize("test,expected",[
    (f"{ODP_ADDR}/something/", "something"),
    (f"{ODP_ADDR}/something", "something"),
    (f"/something", "/something"),
    (f"/something/", "/something/"),
    (f"anything here <asdf;lkj", "anything here <asdf;lkj"),
])
def test_extract_ticket_name(test, expected):
    result = _extract_ticket_name(test)
    assert result == expected