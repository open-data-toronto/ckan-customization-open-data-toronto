from typing import Optional, Dict
from typing import Dict, Optional
from ckanext.opendata.util.intake.types import Ticket, RequestType

ODP_ADDR = "https://open.toronto.ca/dataset"


class MockIntake:
    __count = 0

    def __init__(
        self,
        ticket_id: str,
        ticket_name: str,
        _id: Optional[int] = None,
        inquiry_source: str = "",
        request_type: str = "",
        created: str = "1970-01-01T12:00:00",
        first_response: str = "",
        from_status: str = "",
        to_status: str = "",
        status_timestamp: str = "1970-01-01T12:00:00",
        linked_ticket_id: str = "",
        division: str = "",
        description: str = "",
    ):
        if _id is None:
            self._id = self.__count
        else:
            self._id = _id
        self.__count += 1
        self.ticket_id = ticket_id
        self.ticket_name = ticket_name
        self.inquiry_source = inquiry_source
        self.request_type = request_type
        self.created = created
        self.first_response = first_response
        self.from_status = from_status
        self.to_status = to_status
        self.status_timestamp = status_timestamp
        self.linked_ticket_id = linked_ticket_id
        self.division = division
        self.description = description

    def to_dict(self) -> Dict:
        return {
            "_id": self._id,
            "Ticket Id": self.ticket_id,
            "Ticket Name": self.ticket_name,
            "Inquiry Source": self.inquiry_source,
            "Request Type": self.request_type,
            "Created": self.created,
            "First Response": self.first_response,
            "From Status": self.from_status,
            "To Status": self.to_status,
            "Status Timestamp": self.status_timestamp,
            "Linked Ticket Id": self.linked_ticket_id,
            "Division": self.division,
            "Description": self.description,
        }


class TicketFactory:
    _n = 0

    def __init__(self, ticket_values: Ticket = None):
        if ticket_values is None:
            ticket_values = {}
        _id = self._get_id()
        defaults: Ticket = {
            "_id": f"{_id}",
            "Created": "2024-01-01T11:00:0",
            "Division": None,
            "First Response": "2024-01-01T11:00:0",
            "From Status": None,
            "Inquiry Source": "Inq Source",
            "Linked Ticket Id": "",
            "Public Description": "",
            "Request Type": RequestType.PUBLISH_NEW_OPEN_DATASET_PAGE,
            "Status Timestamp": None,
            "Ticket Id": f"DIA-{_id}",
            "Ticket Name": f"Ticket Name {_id}",
            "To Status": None,
        }
        self._value = {**defaults, **ticket_values}

    @classmethod
    def _get_id(cls) -> int:
        id_value = cls._n
        cls._n += 1
        return id_value

    def to_dict(self) -> Ticket:
        return self._value
