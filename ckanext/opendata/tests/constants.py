from datetime import datetime

SCHEMING_MOCK_TEST_OPTIONS = [
    {"value": "option_value_1", "label": "Option Label 1"},
    {"value": "option_value_2", "label": "Option Label 2"},
    {"value": "option_value_3", "label": "Option Label 3"},
]
SCHEMING_DNE_MOCK_TEST_OPTION_1 = {
    # For uniquness
    "value": f"option_value_{datetime.now().timestamp()}",
    "label": "Option Label DNE",
}
SCHEMING_DNE_MOCK_TEST_OPTION_2 = {"value": "", "label": ""}
