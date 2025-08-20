from datetime import datetime
from typing import Any, List

from ckanext.opendata.util.intake.types import (
    TicketGroup,
    PreparedIntake,
    Ticket,
)


def _is_optional_str(s: Any) -> bool:
    return isinstance(s, str) or s is None


def _validate_ticket(ticket: Ticket):
    assert isinstance(ticket["_id"], str)
    assert isinstance(ticket["Ticket Id"], str)
    assert isinstance(ticket["Ticket Name"], str)
    assert isinstance(ticket["Inquiry Source"], str)
    assert _is_optional_str(ticket.get("Division"))
    assert isinstance(ticket["Request Type"], str)
    assert isinstance(ticket["Created"], str)
    assert isinstance(ticket["Ticket Resolved?"], str)
    assert _is_optional_str(ticket.get("First Response"))
    assert _is_optional_str(ticket.get("From Status"))
    assert _is_optional_str(ticket.get("To Status"))
    assert _is_optional_str(ticket.get("Status Timestamp"))
    assert isinstance(ticket["Linked Ticket Id"], str)
    assert _is_optional_str(ticket.get("Public Description"))


def _validate_ticket_group(grouped_entry: TicketGroup):
    assert isinstance(grouped_entry["ticket_group_id"], str)
    assert isinstance(grouped_entry["ticket_group_name"], str)
    assert isinstance(grouped_entry["last_update"], datetime)
    assert isinstance(grouped_entry["start_date"], datetime)
    assert isinstance(grouped_entry["request_types"], list)
    assert isinstance(grouped_entry["last_status"], str)
    assert _is_optional_str(grouped_entry.get("divisions"))
    assert isinstance(grouped_entry["statuses"], list)

    for ticket in grouped_entry["details"]:
        _validate_ticket(ticket)

def _validate_prepared_intake(intake: PreparedIntake):
    assert isinstance(intake["all_statuses"], list)
    assert isinstance(intake["all_request_types"], list)
    assert isinstance(intake["all_divisions"], list)
    _validate_ticket_group(intake["intake"])

