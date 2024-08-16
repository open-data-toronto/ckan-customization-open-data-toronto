from typing import List, TypedDict, Optional


class SummarizeIntakesData(TypedDict):
    search: Optional[str]

class Intake(TypedDict):
    ticket_group_name: str
    ticket_ids: List[str]
    last_updated: str
    status: str
    inquiry_source: str
    ticket_count: int

def _search_intakes_by_ticket_id(
        intakes:List[Intake],
        ticket_id:int
    ) -> List[Intake]:
    """_search_intakes_by_ticket_id

    Args:
        intakes (List[Intake]): list of intakes to search
        ticket_id (int): ticket id

    Returns:
        List[Intake]: intakes filtered by ticket id and sorted
    """
    results = []
    for intake in intakes:
        in_ticket_ids = f"DIA-{ticket_id}" in intake["ticket_ids"]
        in_query_str = str(ticket_id) in intake["ticket_ids"]
        if in_ticket_ids or in_query_str:
            results.append((in_ticket_ids, in_query_str, intake))

    sorted_results = sorted(results, key=lambda x: (x[0],x[1]))
    return [intake for _,_,intake in sorted_results]

def _search_intakes_by_text(intakes:List[Intake], search:str) -> List[Intake]:
    """_search_intakes_by_text

    Args:
        intakes (List[Intake]): list of intakes to search
        search (str): search query

    Returns:
        List[Intake]: intakes filtered and sorted by text in search term
    """
    results = [
        intake for intake in intakes if
        search in intake['ticket_group_name'].lower()
    ]
    sorted_results = sorted(
        results,
        key=lambda intake: intake['ticket_group_name']
    )
    return sorted_results

def search_intakes(intakes:List[Intake], search:str) -> List[Intake]:
    """_serach_intakes

    Args:
        intakes (List[Intake]): list of intakes to search
        search (str): search query

    Returns:
        List[Intake]: intakes filtered and sorted based on search term
    """
    try:
        int_query = int(search)
        return _search_intakes_by_ticket_id(intakes, int_query)
    except ValueError:
        return _search_intakes_by_text(intakes, search)

