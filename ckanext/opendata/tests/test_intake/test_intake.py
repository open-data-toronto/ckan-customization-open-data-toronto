import ckan.tests.helpers as helpers
import pytest
from typing import Optional, List
from ckanext.opendata.util.intake.types import (
    Ticket,
    UPDATE_TICKET_REQUEST_TYPE,
    DetailedIntake,
    SummarizedIntake,
)
from ckan.logic import NotFound
from ckanext.opendata.util.intake.utils import _extract_ticket_name
from ckanext.opendata.util.intake.types import Ticket
from .utils import ODP_ADDR, MockIntake, TicketFactory
from .validators import (
    validate_prepared_intake,
    validate_detailed_intake,
    validate_summarized_intake,
)

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
        "tickets": [ticket_1, ticket_1a, ticket_1b, ticket_multi],
    },
    ticket_2["Ticket Id"]: {
        "ticket_group_name": ticket_2["Ticket Name"],
        "ticket_group_id": ticket_2["Ticket Id"],
        "tickets": [ticket_2, ticket_multi],
    },
    ticket_3["Ticket Id"]: {
        "ticket_group_name": ticket_3["Ticket Name"],
        "ticket_group_id": ticket_3["Ticket Id"],
        "tickets": [ticket_3],
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


class TestIntakeActions:

    def _mock_tickets(self, ticket_kwargs: Optional[Ticket] = None) -> List[Ticket]:
        return [TicketFactory(ticket_kwargs).to_dict() for _ in range(10)]

    def test_summarize_new_intake(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            {"Request Type": "Publish New Open Dataset Page"}
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

    def test_detail_new_intake(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'new' tickets
            {"Request Type": "Publish New Open Dataset Page"}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        ticket_group_id = tickets[0]["Ticket Id"]
        result: DetailedIntake = helpers.call_action(
            "detail_new_intake", {}, ticket_group_id=ticket_group_id
        )
        validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'existing' tickets
            {"Request Type": UPDATE_TICKET_REQUEST_TYPE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        ticket_group_id = tickets[0]["Ticket Id"]
        result: DetailedIntake = helpers.call_action(
            "detail_existing_intake", {}, ticket_group_id=ticket_group_id
        )
        validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id(self, mocker):
        tickets = self._mock_tickets(
            # ensure there are mocked 'existing' tickets
            {"Request Type": UPDATE_TICKET_REQUEST_TYPE}
        )
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=tickets
        )
        ticket_group_name = tickets[0]["Ticket Name"]
        result: DetailedIntake = helpers.call_action(
            "detail_existing_intake", {}, ticket_group_name=ticket_group_name
        )
        validate_detailed_intake(result)

    def test_detail_existing_intake_by_group_id(self, mocker):
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets", return_value=[]
        )
        ticket_group_name = "dne"
        with pytest.raises(NotFound):
            helpers.call_action(
                "detail_existing_intake", {}, ticket_group_name=ticket_group_name
            )

    def test_prepare_intake(self, mocker):
        mocker.patch(
            "ckanext.opendata.api.intake_utils.get_intake_tickets",
            return_value=self._mock_tickets(),
        )
        result = helpers.call_action("prepare_intake", {})
        validate_prepared_intake(result)


@pytest.mark.parametrize(
    "test,expected",
    [
        (f"{ODP_ADDR}/something/", "something"),
        (f"{ODP_ADDR}/something", "something"),
        (f"/something", "/something"),
        (f"/something/", "/something/"),
        (f"anything here <asdf;lkj", "anything here <asdf;lkj"),
    ],
)
def test_extract_ticket_name(test, expected):
    result = _extract_ticket_name(test)
    assert result == expected
