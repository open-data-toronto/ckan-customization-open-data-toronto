from datetime import datetime
from typing import List, Optional, TypedDict

Ticket = TypedDict(
    "Ticket",
    {
        "_id": str,
        "Created": str,
        "Division": Optional[str],
        "First Response": Optional[str],
        "From Status": Optional[str],
        "Inquiry Source": str,
        "Linked Ticket Id": str,
        "Public Description": Optional[str],
        "Request Type": str,
        "Status Timestamp": Optional[str],
        "Ticket Id": str,
        "Ticket Name": str,
        "To Status": Optional[str],
        "Ticket Resolved?": str,
    },
)


class TicketGroup(TypedDict):
    ticket_group_id: str
    ticket_group_name: str
    jira_ticket_ids: list
    last_update: datetime
    start_date: datetime
    request_types: list
    last_status: str
    divisions: list
    statuses: list
    details: List[Ticket]


PreparedIntake = TypedDict("PreparedIntake", {
    "intake": TicketGroup, 
    "all_statuses": list,
    "all_request_types": list,
    "all_divisions": list,
    }
)