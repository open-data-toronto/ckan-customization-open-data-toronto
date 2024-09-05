from typing import List, TypedDict, Optional
import re
from datetime import datetime
from typing import List, Dict, Optional
from typing_extensions import TypedDict
from datetime import datetime


UPDATE_TICKET_REQUEST_TYPE = "Update Existing Open Dataset Page"

Ticket = TypedDict(
    "NewEntry",
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
    },
)

PublicDescription = Optional[str]

GroupedEntry = TypedDict(
    "GroupedEntry",
    {
        "ticket_group_name": str,
        "ticket_group_id": str,
        "public_description": PublicDescription,
        "tickets": List[Ticket]
    },
)

Intakes = Dict[str, GroupedEntry]
PreparedIntake = TypedDict("PreparedIntake", {"new": Intakes, "existing": Intakes})

class PreparedIntake(TypedDict):
    new: Intakes
    existing: Intakes

class SummarizeIntakesData(TypedDict):
    search: Optional[str]

class SummarizedIntake(TypedDict):
    public_description: PublicDescription
    inquiry_source: str
    last_updated: datetime
    status: str
    ticket_count: int
    ticket_group_id: str
    ticket_group_name: str
    ticket_ids: List[str]





class DetailedIntake(TypedDict):
    divisions: List[str]
    public_description: PublicDescription
    ticket_group_name: str
    ticket_group_id: str
    last_update: datetime
    jira_ticket_ids: List[str]
    inquiry_source: List[str]
    request_types: List
    to_statuses: List
    from_statuses: List
    details: List
