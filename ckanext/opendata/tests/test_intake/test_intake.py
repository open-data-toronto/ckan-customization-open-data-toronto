from datetime import datetime, timedelta
from typing import List, Optional

import ckan.tests.helpers as helpers
import pytest

from ckanext.opendata.util.intake.types import (
    PreparedIntake,
    Ticket,
    TicketGroup
)

from ckanext.opendata.util.intake.utils import(
    group_tickets,
    join_linked_tickets,
    summarize_intake,
)

from ..utils import mock_actions
from .utils import ODP_ADDR, TicketFactory
from .validators import (
    _validate_prepared_intake,
    _validate_ticket,
    _validate_ticket_group,
)

# useful vars
yesterday = datetime.strftime(datetime.today() - timedelta(days=1), "%Y-%m-%dT%H:%M:%S")
two_days_ago = datetime.strftime(datetime.today() - timedelta(days=2), "%Y-%m-%dT%H:%M:%S")
one_year_ago = datetime.strftime(datetime.today() - timedelta(days=365), "%Y-%m-%dT%H:%M:%S")

### generate test data

# basic group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1","Created": two_days_ago, "Ticket Resolved?": "true"}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1","Created": two_days_ago, "Ticket Resolved?": "true"}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Created": two_days_ago, "Status Timestamp": yesterday, "Ticket Resolved?": "true"}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1"}).to_dict()
ticket_3 = TicketFactory({"Ticket Id": "DIA-3", "Ticket Name": "Ticket 3","Created": one_year_ago, "Request Type": "type2"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "To Status": "WIP"}).to_dict()

basic_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_3, ticket_4]
basic_ticket_ids = [rec["Ticket Id"] for rec in basic_ticket_recs]
basic_correct_vals = {
    "grouped_ticket_count": 4,
    "linked_ticket_count": 4,
    "tickets_one_day_old_count": 1,
    "tickets_resolved_yesterday_or_unresolved_count": 3,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 3,
}

# linked group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": yesterday}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1"}).to_dict()
ticket_3 = TicketFactory({"Ticket Id": "DIA-3", "Ticket Name": "Ticket 3","Created": one_year_ago, "To Status": "WIP"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "Request Type": "type2"}).to_dict()
ticket_5 = TicketFactory({"Ticket Id": "DIA-5", "Ticket Name": "Ticket 5","Created": one_year_ago}).to_dict()

linked_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_3, ticket_4, ticket_5]
linked_ticket_ids = [rec["Ticket Id"] for rec in linked_ticket_recs]
linked_correct_vals = {
    "grouped_ticket_count": 5,
    "linked_ticket_count": 4,
    "tickets_one_day_old_count": 1,
    "tickets_resolved_yesterday_or_unresolved_count": 4,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 4,
}

# another linked group
ticket_1 = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": None}).to_dict()
ticket_1a = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": None}).to_dict()
ticket_1b = TicketFactory({"Ticket Id": "DIA-1", "Ticket Name": "Ticket 1", "Linked Ticket Id": "DIA-2", "Created": two_days_ago, "Request Type": "type3", "category": "done"}).to_dict()
ticket_2 = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1", "category": None}).to_dict()
ticket_2a = TicketFactory({"Ticket Id": "DIA-2", "Linked Ticket Id": "DIA-1", "Ticket Name": "Ticket 2","Created": yesterday, "Request Type": "type1", "category": "done"}).to_dict()
ticket_4 = TicketFactory({"Ticket Id": "DIA-4", "Ticket Name": "Ticket 4","Created": one_year_ago, "Request Type": "type2", "Ticket Resolved?": "true"}).to_dict()

more_linked_ticket_recs = [ticket_1, ticket_1a, ticket_1b, ticket_2, ticket_2a, ticket_4]
more_linked_ticket_ids = [rec["Ticket Id"] for rec in more_linked_ticket_recs]
more_linked_correct_vals = {
    "grouped_ticket_count": 3,
    "linked_ticket_count": 2,
    "tickets_one_day_old_count": 0,
    "tickets_resolved_yesterday_or_unresolved_count": 1,
    "type1_tickets_count": 1,
    "type1_and_type2_tickets_count": 2,
    "unresolved_ticket_count": 1,
}

#TODO: make tests that
#   groups, checks number of groups
#   links, checks number of linked groups
#   calculates group info, checks its correct
#   filters by each parameter, checks count of returned groups
#   filters by groups of parameters, checks count of returned groups
#       
# It repeats this for different permutations of input tickets
#   No links
#   Some links
#   Different ticket attributes

pytestmark = pytest.mark.parametrize(
    "ticket_recs,ticket_ids,correct_vals", 
    [
        (basic_ticket_recs, basic_ticket_ids, basic_correct_vals),
        (linked_ticket_recs, linked_ticket_ids, linked_correct_vals),
        (more_linked_ticket_recs, more_linked_ticket_ids, more_linked_correct_vals),
    ]
)


# Test grouping by ticket_id 
def test_grouping_tickets_by_ticket_id(ticket_recs, ticket_ids, correct_vals):
    grouped_tickets = group_tickets(ticket_recs, ticket_ids)
    assert len(grouped_tickets.keys()) == correct_vals["grouped_ticket_count"]

# Test linking ticket groups by linked ticket_id
def test_linking_tickets_by_linked_ticket_id(ticket_recs, ticket_ids, correct_vals):
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    assert len(linked_tickets.keys()) == correct_vals["linked_ticket_count"]

# Test calculating summary stats
def test_creating_summarized_intake(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {}
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)      
    assert isinstance(summarized_intake.get("all_statuses", False), list)
    assert isinstance(summarized_intake.get("all_request_types", False), list)
    assert isinstance(summarized_intake.get("all_divisions", False), list)

# Test filtering by each parameter
def test_filtering_on_ticket_id(ticket_recs, ticket_ids, correct_vals):
    # test with exact ticket_id
    status_definitions = {}
    data_dict = {"ticket_id":"DIA-1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

    # test with imprecise ticket_id
    data_dict = {"ticket_id":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

def test_filtering_max_age(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"max_age":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["tickets_one_day_old_count"]

def test_filtering_max_days_since_resolution(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"max_days_since_resolution":"1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["tickets_resolved_yesterday_or_unresolved_count"]

def test_filtering_name(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"name":"Ticket 4"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == 1

def test_filtering_one_type(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"type":"type1"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_tickets_count"]

def test_filtering_two_types(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"type":"type1~type2"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_and_type2_tickets_count"]

def test_filtering_status(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"status":"the_active_status"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["type1_and_type2_tickets_count"]

def test_filtering_status(ticket_recs, ticket_ids, correct_vals):
    status_definitions = {}
    data_dict = {"resolved":"false"}       
    linked_tickets = join_linked_tickets(group_tickets(ticket_recs, ticket_ids))
    summarized_intake = summarize_intake(status_definitions, linked_tickets, data_dict)
    assert len(summarized_intake["intake"]) == correct_vals["unresolved_ticket_count"]
 
