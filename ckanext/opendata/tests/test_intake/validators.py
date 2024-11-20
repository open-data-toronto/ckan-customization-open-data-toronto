from datetime import datetime
from typing import Any, List

from ckanext.opendata.util.intake.types import (
    DetailedIntake,
    GroupedEntry,
    Intakes,
    PreparedIntake,
    SummarizedIntake,
    Ticket,
    DetailTitle,
    CLOSING_STATUSES
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
    assert _is_optional_str(ticket.get("First Response"))
    assert _is_optional_str(ticket.get("From Status"))
    assert _is_optional_str(ticket.get("To Status"))
    assert _is_optional_str(ticket.get("Status Timestamp"))
    assert isinstance(ticket["Linked Ticket Id"], str)
    assert _is_optional_str(ticket.get("Public Description"))


def _validate_grouped(grouped_entry: GroupedEntry):
    assert isinstance(grouped_entry["ticket_group_id"], str)
    assert isinstance(grouped_entry["ticket_group_name"], str)
    assert _is_optional_str(grouped_entry.get("public_description"))

    for ticket in grouped_entry["tickets"]:
        _validate_ticket(ticket)


def _validate_intake(intake: Intakes):
    for grouped_entry in intake.values():
        _validate_grouped(grouped_entry)


def validate_prepared_intake(prepared_intake: PreparedIntake):
    _validate_intake(prepared_intake["existing"])
    _validate_intake(prepared_intake["new"])


def validate_detailed_intake(intake: DetailedIntake):
    assert isinstance(intake["divisions"], list)
    assert (
        isinstance(intake.get("description"), str) or intake.get("description") is None
    )
    assert isinstance(intake["ticket_group_name"], str)
    assert isinstance(intake["ticket_group_id"], str)
    assert isinstance(intake["last_update"], datetime)
    assert isinstance(intake["jira_ticket_ids"], list)
    assert isinstance(intake["inquiry_source"], list)
    assert isinstance(intake["request_types"], list)
    assert isinstance(intake["to_statuses"], list)
    assert isinstance(intake["from_statuses"], list)
    assert isinstance(intake["details"], list)

    for index in range(len(intake["details"])):
        # ensure future statuses cant have timestamps
        detail_ts = intake["details"][index]["timestamp"]
        detail_activity_state = intake["details"][index]["activity_state"] 
        assert detail_ts or (detail_activity_state == "future")
        assert not (detail_ts and (detail_activity_state == "future"))

        # make sure orders and dates are correct
        # we'll skip "future" details
        if intake["details"][index]["activity_state"] == "future":
            continue

        # for every item after this one...
        for other_i in range(index, len(intake["details"])):
            if intake["details"][other_i]["activity_state"] == "future":
                continue
            assert (
                intake["details"][index]["timestamp"]
                <= intake["details"][other_i]["timestamp"]
            )

    # ensure that final status isn't "active" if it's Closed, or similar
    if intake["details"][-1]["title"] in CLOSING_STATUSES:
        assert intake["details"][-1]["activity_state"] == "done"

def validate_summarized_intake(intake: SummarizedIntake):
    assert (
        isinstance(intake.get("description"), str) or intake.get("description") is None
    )
    assert isinstance(intake.get("ticket_group_id", None), str)
    assert isinstance(intake.get("ticket_group_name", None), str)
    assert isinstance(intake.get("ticket_ids", None), List)
    assert all(isinstance(tid, str) and tid != "" for tid in intake["ticket_ids"])
    assert isinstance(intake.get("last_updated", None), datetime)
    assert isinstance(intake.get("status", None), str)
    assert isinstance(intake.get("inquiry_source", None), str)
    assert isinstance(intake.get("ticket_count", None), int)
