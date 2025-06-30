import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import ckan.plugins.toolkit as tk

from .types import (
    DetailedIntake,
    GroupedEntry,
    Intakes,
    PublicDescription,
    SummarizedIntake,
    Ticket,
    CLOSING_STATUSES,
)

########################################################################################
# Private
########################################################################################

DictKey = TypeVar("DictKey")
DictValue = TypeVar("DictValue")


def _subset_dict_by(
    dictionary: Dict[DictKey, DictValue],
    predicate: Callable[[DictKey, DictValue], bool],
) -> Dict[DictKey, DictValue]:
    """subset_dict_by

    :param dictionary: the dictionary to subset by
    :type dictionary: Dict[DictKey, DictValue]
    :param predicate: function that, given a key and value of the dictionary returns a
      boolean indicating if the key should be removed from the returned dictionary
    :type predicate: Callable[[DictKey, DictValue], bool]
    :return: the original dictionary with keys removed for elements not matching the
      predicate.
    :rtype: Dict[DictKey, DictValue]
    """
    return {k: v for k, v in dictionary.items() if predicate(k, v)}


def _extract_ticket_name(s: str) -> str:
    match = re.search(r"^https://open.toronto.ca/dataset/([^/]+)/?$", s)
    if match:
        return match.group(1)
    return s


def _get_ticket_group_name(ticket_group_id: str, tickets: List[Ticket]) -> str:
    for ticket in tickets:
        if ticket["Ticket Id"] == ticket_group_id:
            #return _extract_ticket_name(ticket["Ticket Name"])
            return ticket["Ticket Name"]
    raise ValueError(f"Ticket with id {ticket_group_id} not found")


def _get_leftmost_is_truthy(in_dict: Dict[Any, Any], *keys) -> Any:
    for key in keys:
        val = in_dict[key]
        if val:
            return val

def _is_closed_ticket(ticket: Dict[str, Any]) -> bool:
    _CLOSED_STATUSES = ["Closed", "Published", "Retired"]
    return ticket["To Status"] in _CLOSED_STATUSES
    


########################################################################################
# Public Utils
########################################################################################


def get_intake_tickets(context) -> List[Ticket]:
    open_data_intake_package_id = "open-data-intake"
    package = tk.get_action("package_show")(
        context, {"id": open_data_intake_package_id}
    )
    try:
        resource_id = next(
            resource["id"]
            for resource in package["resources"]
            if resource["name"] == "Open Data Intake Records"
        )
    except StopIteration:
        raise ValueError("Could not find Open Data Intake Resource")
    return tk.get_action("datastore_search")(
        context, {"resource_id": resource_id, "limit": 32000}
    )["records"]


def search_intakes(
    intakes: List[SummarizedIntake], search: str
) -> List[SummarizedIntake]:
    """search_intakes

    Args:
        intakes (List[SummarizedIntake]): list of intakes to search
        search (str): search query

    Returns:
        List[SummarizedIntake]: intakes filtered and sorted based on search term
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

#TODO -- make this logic check the last status in a group of ticket
def filter_out_closed_tickets(
    grouped_tickets: Dict[str, List[Ticket]]
) -> Dict[str, List[Ticket]]:
    """filter_out_closed_tickets

    :param grouped_tickets: tickets grouped by ticket_group_id
    :type grouped_tickets: Dict[str, List[Ticket]]
    :return: dictionary of ticket groups where ticket groups containing any closed
      tickets have been removed
    :rtype: Dict[str, List[Ticket]]
    """
    return _subset_dict_by(
        grouped_tickets,
        predicate=lambda _, tickets: not any(
            _is_closed_ticket(ticket) for ticket in tickets
        ),
    )


def join_linked_tickets(
    grouped_tickets: Dict[str, List[Ticket]]
) -> Dict[str, List[Ticket]]:
    """join_linked_tickets

    :param grouped_tickets: Join tickets with "Linked Ticket ID" to their parent
      ticket_group
    :type grouped_tickets: Dict[str, List[Ticket]]
    :return: dictionary with linked tickets joined to their 'linked' ticket group
    :rtype: Dict[str, List[Ticket]]
    """
    # join linked ticket objects together
    joined = {}
    ticket_ids = set(grouped_tickets.keys())
    for ticket_id in ticket_ids:

        # if there are any linked tickets, combine their records
        if grouped_tickets.get(ticket_id, False):

            # If this ticket has any linked tickets and hasn't already been popped we're
            # going to add it to `grouped`
            if any([x["Linked Ticket Id"] for x in grouped_tickets[ticket_id]]):

                #  pop it's associated records (ticket_id no longer in working)
                # This ticket id will no longer be considered in linked tickets
                records = grouped_tickets.pop(ticket_id)

                #  grab the linked tickets of the first record (maybe its consistent
                # between all records)
                #  for all linked tickets that haven't already been
                for linked_id in records[0]["Linked Ticket Id"].split(","):
                    # if it hasn't already been popped, grab that linked' ticket's
                    # records and append them to this records
                    if grouped_tickets.get(linked_id, False):
                        this = grouped_tickets.pop(linked_id)
                        for item in this:
                            records.append(item)

                joined[ticket_id] = records
    # adding records that dont have linked tickets
    for k, v in grouped_tickets.items():
        joined[k] = v
    return joined


def name_ticket_groups(grouped_tickets: Dict[str, List[Ticket]]) -> Intakes:
    """name_ticket_groups

    :param grouped_tickets: tickets grouped under ticket_group_ids
    :type grouped_tickets: Dict[str, List[Ticket]]
    :return: Intakes
    :rtype: Intakes
    """
    return {
        ticket_group_id: {
            "tickets": sorted(
                tickets,
                key=lambda x: get_leftmost_datetime(x, "Status Timestamp", "Created"),
            ),
            "ticket_group_id": ticket_group_id,
            "ticket_group_name": _get_ticket_group_name(ticket_group_id, tickets),
        }
        for ticket_group_id, tickets in grouped_tickets.items()
    }


def get_leftmost_datetime(in_dict: Dict[Any, Union[str, Any]], *keys) -> datetime:
    """get_leftmost_datetime

    :param in_dict: dictionary
    :type in_dict: Dict[Any, Union[str, Any]]
    :return: parsed datetime of first/leftmost truthy dictionary value checked in the
      order that *args are provided in
    :rtype: datetime
    """
    return datetime.strptime(
        _get_leftmost_is_truthy(in_dict, *keys),
        "%Y-%m-%dT%H:%M:%S",
    )


def get_divisions_from_intake_tickets(intakes: List[Dict]) -> List[str]:
    """get_divisions_from_intake_tickets

    :param intake: list of intakes
    :type intake: List[Dict]
    :return: list of unique divisions
    :rtype: List[str]
    """
    divisions = set(
        rec.get("Division")
        for rec in intakes
        if rec.get("Division") != "" and rec.get("Division") is not None
    )
    return list(divisions)


def get_ticket_group_public_description(
    tickets: List[Ticket],
) -> Optional[PublicDescription]:
    """get_ticket_group_public_description

    :param tickets: list of tickets
    :type tickets: List[Ticket]
    :return: user-facing public description
    :rtype: PublicDescription
    """
    descriptions = {ticket.get("Public Description") for ticket in tickets}
    description = [desc for desc in descriptions if desc is not None]
    return None if len(description) == 0 else description[-1]

'''
def detail_intake(grouped_entry: GroupedEntry) -> DetailedIntake:
    """detail_intake

    :param grouped_entry: ticket groups
    :type grouped_entry: GroupedEntry
    :return: grouped tickets formatted for frontend
    :rtype: DetailedIntake
    """
    # TODO finish this!
    tickets = grouped_entry#["tickets"]

    assert isinstance(tickets, list), f"Input must be a list of dicts!"
    assert len(tickets), f"Input must be populated!"

    # Let's make high level info for this ticket group
    last_update = None
    start_date = None
    jira_ticket_ids = set()
    #inquiry_source = set()
    request_types = set()
    #to_statuses = set()
    #from_statuses = set()

    for rec in tickets:
        # last update
        ticket_last_updated = get_leftmost_datetime(rec, "Status Timestamp", "Created")
        if last_update is None or ticket_last_updated > last_update:
            last_update = ticket_last_updated

        # start date
        ticket_start_date = datetime.strptime(rec["Created"], "%Y-%m-%dT%H:%M:%S")
        if start_date is None or ticket_start_date < start_date:
            start_date = ticket_start_date

        jira_ticket_ids.add(rec["Ticket Id"])
        #inquiry_source.add(rec["Inquiry Source"])
        request_types.add(rec["Request Type"])
        #to_statuses.add(rec["To Status"])
        #from_statuses.add(rec["From Status"])


    #ticket_group_id = grouped_entry["ticket_group_id"]
    #ticket_group_name = grouped_entry["ticket_group_name"]
    #public_description = get_ticket_group_public_description(tickets)
    #divisions = get_divisions_from_intake_tickets(tickets)

    ## add active state to last detail if its not a closing status
    #if details[-1]["title"] not in CLOSING_STATUSES:
    #    details[-1]["activity_state"] = "active"

    return {
        "details": tickets,
        #"divisions": divisions,
        #"from_statuses": list(from_statuses),
        #"inquiry_source": list(inquiry_source),
        "jira_ticket_ids": list(jira_ticket_ids),
        "last_update": last_update,
        #"public_description": public_description,
        "request_types": list(request_types),
        #"ticket_group_id": ticket_group_id,
        #"ticket_group_name": ticket_group_name,
        #"to_statuses": list(to_statuses),
    }
'''

def get_most_recent_ticket(tickets: List[Ticket]) -> Optional[Ticket]:
    """get_most_recent_ticket

    :param tickets: list of tickets
    :type tickets: List[Ticket]
    :return: the most recent based on timestamps in the tickets (Status Timestamp,
      otherwise 'Created' ts). None if no tickets are found.
    :rtype: Optional[Ticket]
    """
    if not tickets:
        return None
    return max(
        tickets,
        key=lambda x: get_leftmost_datetime(x, "Status Timestamp", "Created"),
    )
