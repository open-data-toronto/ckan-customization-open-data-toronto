from typing import List, TypedDict, Optional
import re

from typing import List, Dict, Optional
from typing_extensions import TypedDict

Ticket = TypedDict(
    "Ticket",
    {
    "_id": str,
    "Ticket Id": str,
    "Ticket Name": str,
    "Inquiry Source": str,
    "Request Type": str,
    "Created": str,
    "First Response": str,
    "From Status": str,
    "To Status": str,
    "Status Timestamp": str,
    "Linked Ticket Id": str,
    }
)

Entry = TypedDict(
    "NewEntry",
    {
        "_id": int,
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

# GroupedEntry = TypedDict(
#     "GroupedEntry",{
#         "ticket_group_name": str,
#         # "parent_ticket_id": str,
#         "records": List[Entry]
#     }
# )

GroupedEntry = TypedDict(
    "GroupedEntry",{
        "ticket_group_name": str,
        # "parent_ticket_id": str,
        "records": List[Entry]
    }
)


# New = Dict[str, List[Entry]]
# Existing = Dict[str, List[Entry]]

Intakes = Dict[str, List[Entry]]
PreparedIntake = TypedDict("PreparedIntake", {"new": Intakes, "existing": Intakes})

from pydantic import BaseModel, create_model


class Prep(BaseModel):
    new: Intakes
    existing: Intakes


class SummarizeIntakesData(TypedDict):
    search: Optional[str]

class Intake(TypedDict):
    ticket_group_name: str
    ticket_ids: List[str]
    last_updated: str
    status: str
    inquiry_source: str
    ticket_count: int

def search_intakes(intakes:List[Intake], search:str) -> List[Intake]:
    """_serach_intakes

    Args:
        intakes (List[Intake]): list of intakes to search
        search (str): search query

    Returns:
        List[Intake]: intakes filtered and sorted based on search term
    """
  
    # "0asdf12 other_things!@#$ 34" -> [0, 12, 34]
    ticket_ids_in_search = [
        f"DIA-{ticket_id}" for ticket_id in re.findall(r'\d+', search)
    ]

    intake_matches_ticket_id = lambda intake: any(
        ticket in intake['ticket_ids']
        for ticket in ticket_ids_in_search
    )

    filtered_intakes = [
        intake for intake in intakes if 
        intake_matches_ticket_id(intake)
        or search in intake['ticket_group_name'].lower()
    ]

    sorted_intakes = sorted(
        filtered_intakes, key= lambda x: x['ticket_group_name']
    )

    return sorted_intakes
