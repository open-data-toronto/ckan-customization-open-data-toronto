import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

import ckan.plugins.toolkit as tk

from .types import (
    TicketGroup,
    Ticket,
)

import difflib

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


def _prep_for_fuzzy_match(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "")


def _get_ticket_group_name(ticket_group_id: str, tickets: List[Ticket]) -> str:
    for ticket in tickets:
        if ticket["Ticket Id"] == ticket_group_id:
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

def _get_datastore_records(context, resource_name):
    open_data_intake_package_id = "open-data-intake"
    package = tk.get_action("package_show")(
        context, {"id": open_data_intake_package_id}
    )
    try:
        resource_id = next(
            resource["id"]
            for resource in package["resources"]
            if resource["name"] == resource_name
        )
    except StopIteration:
        raise ValueError(f"Could not find {resource_name} Resource")
    return tk.get_action("datastore_search")(
        context, {"resource_id": resource_id, "limit": 32000}
    )["records"]
    
def _split_string_into_set(this_set, value):
    if value:
        this_set.update(value.split(", "))
        return this_set
    else:
        return this_set

########################################################################################
# Public Utils
########################################################################################

def parse_package_name(input_url):
    return input_url.replace("https://open.toronto.ca/dataset/", "").replace("/", "")

def summarize_intake(status_definitions, linked_tickets, data_dict):
    # prepare output, raw intake data
    output = {"intake": {}}

    all_statuses = set()
    all_request_types = set()
    all_divisions = set()
    all_inquiry_sources = set()

    # loop through groups to add summary info for each
    for ticket_group_id in linked_tickets.keys():
        group = linked_tickets[ticket_group_id]
        
        ticket_group_name = None
        last_update = None
        last_status = None
        last_status_colour = None
        start_date = None
        jira_ticket_ids = set()
        request_types = set()
        divisions = set()
        inquiry_sources = set()
        statuses = set()
        resolved = "true"

        for i in range(len(group)):

            # map status and definition from ckan "statuses" dataset
            group[i]["Status Definition"] = status_definitions.get(group[i]["To Status"], {}).get("description", None)
            group[i]["Status Colour"] = status_definitions.get(group[i]["To Status"], {}).get("colour", None)

            # last update, status
            ticket_last_updated = get_leftmost_datetime(group[i], "Status Timestamp", "Created")
            if last_update is None or ticket_last_updated > last_update:
                last_update = ticket_last_updated
                last_status = group[i]["To Status"]
                last_status_colour = group[i]["Status Colour"]

            # start date
            ticket_start_date = datetime.strptime(group[i]["Created"], "%Y-%m-%dT%H:%M:%S")
            if start_date is None or ticket_start_date < start_date:
                start_date = ticket_start_date

            # ticket group name
            if group[i]["Ticket Id"] == ticket_group_id:
                ticket_group_name = group[i]["Ticket Name"]

            # map status and definition from ckan "statuses" dataset
            group[i]["Status Definition"] = status_definitions.get(group[i]["To Status"], {}).get("description")

            # is the ticket resolved or active?
            if group[i]["Ticket Resolved?"] == "false":
                resolved = "false"

            jira_ticket_ids.add(group[i]["Ticket Id"])
            request_types.add(group[i]["Request Type"])
            statuses.add(group[i]["To Status"])
            divisions = _split_string_into_set(divisions, group[i]["Division"])
            inquiry_sources = _split_string_into_set(inquiry_sources, group[i]["Inquiry Source"])

        # if there were inputs to the API call, use them to filter...

        # ticket id
        if (
            data_dict.get("ticket_id", False) and not 
            fuzzy_match_ticket_ids(data_dict.get("ticket_id", False), list(jira_ticket_ids))
        ):
            continue

        # max age
        if data_dict.get("max_age", False):
            try:
                max_age = int(data_dict["max_age"])
            except ValueError as e:
                raise ValueError("max_age parameter must be an integer. " + str(e))
            age = (datetime.today() - start_date).days
            if age > max_age:
                continue

        # TODO: max days since resolution

        # ticket group name
        if (
                data_dict.get("name", False) and not
                parse_package_name(ticket_group_name) == data_dict["name"]
        ):
            continue

        # custom logic for the requests page - it will never have update tickets on it
        # WARNING: if we change the name of an update ticket in Jira, this will break
        # TODO: consider ways around this by externalizing the name of update tickets
        if (
            data_dict.get("page", None) == "requests" and 
            "I’d like to update an existing dataset or page" in request_types
        ):
            continue

        # ticket type (publish, update, inquiry, etc) 
        if data_dict.get("type", False):
            input_ticket_types = set(data_dict["type"].split("~"))
            all_current_request_types = set(request_types)

            # if none overlap, then continue
            if not all_current_request_types.intersection(input_ticket_types):
                continue

        # division
        if data_dict.get("division", False) and data_dict.get("division", None) not in list(divisions):
            continue

        # current jira status
        if data_dict.get("status", False) and data_dict.get("status", None) != last_status:
            continue

        # whether the ticket is resolved or not
        if data_dict.get("resolved", False) and data_dict.get("resolved", None) != resolved:
            continue

        # the "all_" sets should also consider the filters above
        all_request_types = all_request_types.union(request_types)
        all_divisions = all_divisions.union(divisions)
        all_statuses = all_statuses.union(statuses)
        all_inquiry_sources = all_inquiry_sources.union(inquiry_sources)

        output["intake"][ticket_group_id] = {
            "ticket_group_id": ticket_group_id,
            "ticket_group_name": ticket_group_name,
            "jira_ticket_ids": list(jira_ticket_ids),
            "last_update": last_update,
            "start_date": start_date,
            "request_types": list(request_types),
            "last_status": last_status,
            "last_status_colour": last_status_colour,
            "divisions": list(divisions),
            "inquiry_sources": list(inquiry_sources),
            "statuses": list(statuses),
            "details": sorted(group, key= lambda x: x["Status Timestamp"]),
        }

    output["all_statuses"] = list(all_statuses)
    output["all_request_types"] = list(all_request_types)
    output["all_divisions"] = list(all_divisions)
    output["all_inquiry_sources"] = list(all_inquiry_sources)

    return output


def fuzzy_match_ticket_ids(this_ticket_id, all_ticket_ids):
    """
    fuzzy_match_ticket_ids

    Args:
        this_ticket_id (str): jira ticket id (ex: DIA-123)
        all_ticket_ids (list): list of jira ticket id strings

    Returns:
        true if this_ticket_id is fuzzily contained in all_ticket_ids
    """

    # if this_ticket_id is empty, return false
    if not this_ticket_id:
        return False

    # check if any ticket ids fuzzily match
    for that_ticket_id in all_ticket_ids:
        if re.sub(r'\D', '', this_ticket_id) == re.sub(r'\D', '', that_ticket_id):
            return True

    # if none matched, return false
    return False


def get_intake_tickets(context) -> List[Ticket]:
    return _get_datastore_records(context, "Open Data Intake Records")

def get_status_definitions(context):
    try:
        definitions = _get_datastore_records(context, "statuses")
    except ValueError:
        return {}
    #return dict((d["status"], d["description"]) for d in definitions)
    return {d["status"]: {"description": d["description"], "colour": d["colour"]} for d in definitions}

def fuzzy_match_ticket_name(search: str, ticket_group_name: str):
    """fuzzy_match_ticket_name

    Args:
        search (str): search query
        ticket_group_name (str): name to match the search against

    Returns:
        True or False if search variable somewhat matches ticket_group_name
    """

    search = _prep_for_fuzzy_match(search)
    ticket_group_name = _prep_for_fuzzy_match(ticket_group_name)

    # if search is in input string (after processing), return true
    if search in ticket_group_name:
        return True
    else:
        return False

    

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

def group_tickets(intake_tickets, ticket_ids) -> TicketGroup:
    grouped_tickets = {}
    for ticket_id in ticket_ids:
        grouped_tickets[ticket_id] = [
            rec for rec in intake_tickets if rec["Ticket Id"] == ticket_id
        ]
    return grouped_tickets

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


def name_ticket_groups(grouped_tickets: Dict[str, List[Ticket]]) -> TicketGroup:
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
):
    """get_ticket_group_public_description

    :param tickets: list of tickets
    :type tickets: List[Ticket]
    :return: user-facing public description
    :rtype: PublicDescription
    """
    descriptions = {ticket.get("Public Description") for ticket in tickets}
    description = [desc for desc in descriptions if desc is not None]
    return None if len(description) == 0 else description[-1]


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
