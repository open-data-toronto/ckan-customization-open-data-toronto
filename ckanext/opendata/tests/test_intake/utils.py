from typing import Optional
from ckanext.opendata.util.intake.types import Ticket, RequestType

ODP_ADDR = "https://open.toronto.ca/dataset"


class TicketFactory:
    __n_instances = 0

    def __init__(self, ticket: Optional[Ticket]):
        self._values = self.get_default_values(self._get_id())
        if ticket is not None:
            self._values.update(**ticket)

    @classmethod
    def _get_id(cls) -> int:
        id_value = cls.__n_instances
        cls.__n_instances += 1
        return id_value

    @classmethod
    def get_default_values(cls, instance_id: int):
        return {
            "_id": f"{instance_id}",
            "Created": "2024-01-01T11:00:0",
            "Division": None,
            "First Response": "2024-01-01T11:00:0",
            "From Status": None,
            "Inquiry Source": "Inq Source",
            "Linked Ticket Id": "",
            "Public Description": "",
            "Request Type": RequestType.PUBLISH_NEW_OPEN_DATASET_PAGE,
            "Status Timestamp": None,
            "Ticket Id": f"DIA-{instance_id}",
            "Ticket Name": f"Ticket Name {instance_id}",
            "To Status": None,
        }

    def to_dict(self):
        return self._values
