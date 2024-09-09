import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "ckanext")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "ckanext", "opendata", "tests")
    ),
)


@pytest.fixture
def record_test_name(record_xml_attribute):
    def record_name(s: str) -> None:
        record_xml_attribute("name", s)

    return record_name
