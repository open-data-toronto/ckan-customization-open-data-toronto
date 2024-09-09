from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TypedDict


class RequestType(str, Enum):
    MAKE_OPEN_DATA_INQUIRY = "Make Open Data Inquiry"
    PUBLISH_NEW_OPEN_DATASET_PAGE = "Publish New Open Dataset Page"
    UPDATE_EXISTING_OPEN_DATASET_PAGE = "Update Existing Open Dataset Page"


PublicDescription = Optional[str]

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
        "Public Description": PublicDescription,
        "Request Type": str,
        "Status Timestamp": Optional[str],
        "Ticket Id": str,
        "Ticket Name": str,
        "To Status": Optional[str],
    },
)

GroupedEntry = TypedDict(
    "GroupedEntry",
    {
        "ticket_group_name": str,
        "ticket_group_id": str,
        "public_description": PublicDescription,
        "tickets": List[Ticket],
    },
)

Intakes = Dict[str, GroupedEntry]
PreparedIntake = TypedDict("PreparedIntake", {"new": Intakes, "existing": Intakes})


class PreparedIntake(TypedDict):
    new: Intakes
    existing: Intakes


class SummarizeIntakesParameter(TypedDict):
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
