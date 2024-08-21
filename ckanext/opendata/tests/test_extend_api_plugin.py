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
            division:str='',
            description:str='',
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

@pytest.mark.parametrize(
        "search",
        ["Ticket","ticket","TiCkEt"]
)
def test_summarize_new_intake_search_str(search, mocker):
    context = {}
    data = {"search": search}

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

def test_summarize_new_intake_accepts_empty_search(mocker):
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

@pytest.mark.parametrize(
        "ticket_id,expected_ticket_groups",
        [
            (
                ticket_multi["Ticket Id"],
                {'Ticket Group 1', 'Ticket Group 2'},
            ),
            (
                # strip the "DIA-""
                ticket_multi["Ticket Id"][4:],
                {'Ticket Group 1', 'Ticket Group 2'},
            ),
            (
                # Add arbitrary padding text
                f'other things here {ticket_multi["Ticket Id"]} numbers too 12',
                {'Ticket Group 1', 'Ticket Group 2'},
            ),
            (
                "9999999",
                set(),
            )
        ]
)
def test_summarize_new_intake_accepts_ticket_number_in_search(
    mocker,
    ticket_id,
    expected_ticket_groups,
):
    context = {}
    data = {"search": ticket_id}

    mocked_prepare_intake_action = (
        lambda *args, **kwargs: {"new": mock_intake_items}
    )
    mocker.patch(
        'opendata.api.tk.get_action',
        return_value = mocked_prepare_intake_action
    )

    result = helpers.call_action('summarize_new_intake', context, **data)

    result_ticket_names = [intake["ticket_group_name"] for intake in result]
    assert set(result_ticket_names) == expected_ticket_groups
