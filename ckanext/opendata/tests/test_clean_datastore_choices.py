import json
import logging
from enum import Enum

import pytest

from ckanext.opendata.clean_datastore_choices import SchemingMigration


class MockCivicIssues(str, Enum):
    affordable_housing = "Affordable housing"
    mobility = "Mobility"
    fiscal_responsibility = "Fiscal responsibility"


class MockCivicIssuesOld(str, Enum):
    affordable_housing = "affordable_housing"
    mobility = "mobility"
    fiscal_responsibility = "fiscal_responsibility"


updated_values = {
    MockCivicIssuesOld.affordable_housing: MockCivicIssues.affordable_housing,
    MockCivicIssuesOld.mobility: MockCivicIssues.mobility,
    MockCivicIssuesOld.fiscal_responsibility: MockCivicIssues.fiscal_responsibility,
}


@pytest.mark.parametrize(
    "case,expected_json",
    [
        # Empty cases
        ("{}", json.dumps([])),
        ('{""}', json.dumps([])),
        # Case insensitive
        (
            f'{{"{MockCivicIssuesOld.affordable_housing.capitalize()}"}}',
            json.dumps([MockCivicIssues.affordable_housing]),
        ),
        # {"something","something else"}
        (
            f'{{"{MockCivicIssuesOld.affordable_housing}","{MockCivicIssuesOld.mobility}"}}',
            json.dumps([MockCivicIssues.affordable_housing, MockCivicIssues.mobility]),
        ),
        # {no quotes,"with quotes"}
        (
            f'{{{MockCivicIssuesOld.affordable_housing},"{MockCivicIssuesOld.mobility}"}}',
            json.dumps([MockCivicIssues.affordable_housing, MockCivicIssues.mobility]),
        ),
        # {space-between-items, space-before}
        (
            f"{{{MockCivicIssuesOld.affordable_housing}, {MockCivicIssuesOld.mobility}}}",
            json.dumps([MockCivicIssues.affordable_housing, MockCivicIssues.mobility]),
        ),
        # sorted ("Affordable housing" before "Mobility")
        (
            f"{{{MockCivicIssuesOld.mobility}, {MockCivicIssuesOld.affordable_housing}}}",
            json.dumps([MockCivicIssues.affordable_housing, MockCivicIssues.mobility]),
        ),
        # without dupes
        (
            f"{{{MockCivicIssuesOld.mobility},{MockCivicIssuesOld.mobility}}}",
            json.dumps([MockCivicIssues.mobility]),
        ),
        # parses valid json (does also sort and map values as needed)
        (
            f'["{MockCivicIssuesOld.mobility}", "{MockCivicIssues.affordable_housing}"]',
            json.dumps([MockCivicIssues.affordable_housing, MockCivicIssues.mobility]),
        ),
    ],
)

@pytest.mark.usefixtures("with_plugins")
def test_map_to_new_values(case, expected_json):
    dummy_logger = logging.Logger("test_map_to_new_values")
    result = SchemingMigration._map_to_new_values(dummy_logger, case, updated_values)
    assert result == expected_json
