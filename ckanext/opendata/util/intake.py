from typing import List, TypedDict, Optional
import re
from datetime import datetime
from typing import List, Dict, Optional
from typing_extensions import TypedDict


UPDATE_TICKET_REQUEST_TYPE = "Update Existing Open Dataset Page"

Ticket = TypedDict(
    "NewEntry",
    {
        "_id": str,
        "Ticket Id": str,
        "Ticket Name": str,
        "Inquiry Source": str,
        "Division": Optional[str],
        "Request Type": str,
        "Created": str,
        "First Response": Optional[str],
        "From Status": Optional[str],
        "To Status": Optional[str],
        "Status Timestamp": Optional[str],
        "Linked Ticket Id": str,
    },
)

GroupedEntry = TypedDict(
    "GroupedEntry",
    {"ticket_group_name": str, "ticket_group_id": str, "tickets": List[Ticket]},
)

Intakes = Dict[str, GroupedEntry]
PreparedIntake = TypedDict("PreparedIntake", {"new": Intakes, "existing": Intakes})

class PreparedIntake(TypedDict):
    new: Intakes
    existing: Intakes

class SummarizeIntakesData(TypedDict):
    search: Optional[str]

class SummarizedIntake(TypedDict):
    description: Optional[str]
    inquiry_source: str
    last_updated: datetime
    status: str
    ticket_count: int
    ticket_group_id: str
    ticket_group_name: str
    ticket_ids: List[str]


def search_intakes(intakes: List[SummarizedIntake], search: str) -> List[SummarizedIntake]:
    """_serach_intakes

    Args:
        intakes (List[Intake]): list of intakes to search
        search (str): search query

    Returns:
        List[Intake]: intakes filtered and sorted based on search term
    """

    # "0asdf12 other_things!@#$ 34" -> [0, 12, 34]
    ticket_ids_in_search = [
        f"DIA-{ticket_id}" for ticket_id in re.findall(r"\d+", search)
    ]

    intake_matches_ticket_id = lambda intake: any(
        ticket in intake["ticket_ids"] for ticket in ticket_ids_in_search
    )

    filtered_intakes = [
        intake
        for intake in intakes
        if intake_matches_ticket_id(intake)
        or search in intake["ticket_group_name"].lower()
    ]

    sorted_intakes = sorted(filtered_intakes, key=lambda x: x["ticket_group_name"])

    return sorted_intakes

from datetime import datetime


class DetailedIntake(TypedDict):
    divisions: List[str]
    description: Optional[str]
    ticket_group_name: str
    ticket_group_id: str
    last_update: datetime
    jira_ticket_ids: List[str]
    inquiry_source: List[str]
    request_types: List
    to_statuses: List
    from_statuses: List
    details: List