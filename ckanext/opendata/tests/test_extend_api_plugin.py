import ckan.tests.helpers as helpers
import pytest
from typing import Dict, Optional


class MockIntake:
    __count = 0

    def __init__(
            self,
            ticket_id:str,
            ticket_name:str,
            _id:Optional[int]=None,
            inquiry_source:str='',
            request_type:str='',
            created:str='1970-01-01T12:00:00',
            first_response:str='',
            from_status:str='',
            to_status:str='',
            status_timestamp:str='1970-01-01T12:00:00',
            linked_ticket_id:str='',
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

@pytest.mark.parametrize(
        "query",
        ["Ticket","ticket","TiCkEt"]
)
def test_summarize_new_intake_uses_query(query, mocker):
    context = {}
    data = {"query": query}

    mocked_prepare_intake_action = (
        lambda *args, **kwargs: {"new": mock_intake_items}
    )

    mocker.patch(
        'opendata.api.tk.get_action',
        return_value = mocked_prepare_intake_action
    )
    result = helpers.call_action('summarize_new_intake', context, **data)
    assert len(result) == 3
    assert all(t['ticket_group_name'].startswith("Ticket Group ") for t in result)

def test_summarize_new_intake_accepts_no_query(mocker):
    context = {}
    data = {}
    mocked_prepare_intake_action = (
        lambda *args, **kwargs: {"new": mock_intake_items}
    )
    mocker.patch(
        'opendata.api.tk.get_action',
        return_value = mocked_prepare_intake_action
    )
    result = helpers.call_action('summarize_new_intake', context, **data)
    assert len(result) == len(mock_intake_items)

def test_summarize_new_intake_accepts_ticket_number_query(mocker):
    context = {}
    ticket_id = str(ticket_multi['Ticket Id'])
    data = {"query": ticket_id}

    mocked_prepare_intake_action = (
        lambda *args, **kwargs: {"new": mock_intake_items}
    )
    mocker.patch(
        'opendata.api.tk.get_action',
        return_value = mocked_prepare_intake_action
    )

    result = helpers.call_action('summarize_new_intake', context, **data)

    assert all([
        (
            f"DIA-{ticket_id}" in intake['ticket_ids']
            or str(ticket_id) in intake["ticket_group_name"]
        )
            for intake in result
    ])
