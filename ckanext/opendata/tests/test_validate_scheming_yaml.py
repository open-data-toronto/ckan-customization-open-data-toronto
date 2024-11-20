from typing import Optional

import pytest

from ckanext.opendata.util.types import DatasetField, _DataStoreColumns


def _get_default_dataset_field(
    choices_helper: Optional[str] = "",
    datastore_choices_columns: Optional[_DataStoreColumns] = None,
    datastore_choices_resource: Optional[str] = "",
    display_property: Optional[str] = "",
    display_snippet: Optional[str] = "",
    field_name: str = "test_field",
    form_placeholder: Optional[str] = "",
    form_snippet: Optional[str] = "",
    help_text: Optional[str] = "",
    label: str = "Test Field",
    output_validators: Optional[str] = "",
    required: Optional[bool] = False,
    validators: Optional[str] = "",
) -> DatasetField:
    return DatasetField(
        choices_helper=choices_helper,
        datastore_choices_columns=datastore_choices_columns,
        datastore_choices_resource=datastore_choices_resource,
        display_property=display_property,
        display_snippet=display_snippet,
        field_name=field_name,
        form_placeholder=form_placeholder,
        form_snippet=form_snippet,
        help_text=help_text,
        label=label,
        output_validators=output_validators,
        required=required,
        validators=validators,
    )


@pytest.mark.parametrize(
    "field_kwargs,is_valid",
    [
        ########################################################################
        # Error cases ({...}, False)                                           #
        ########################################################################
        # should be defined if datastore_choices_resource is defined
        (
            {
                "datastore_choices_resource": "some_resource",
                "datastore_choices_columns": None,
            },
            False,
        ),
        # should be followed by "scheming_multiple_choice" stead of
        # "scheming_choices"
        (
            {"validators": "string_to_choices scheming_choices"},
            False,
        ),
        # string_to_choices should be followed by "scheming_multiple_choice"
        # and not "scheming_choices"
        ({"validators": "string_to_choices scheming_choices"}, False),
        # scheming_multiple_choice follows string_to_choices
        ## order of validators is reversed
        ({"validators": "scheming_multiple_choice string_to_choices"}, False),
        ## missing string_to_choices first
        ({"validators": "scheming_multiple_choice"}, False),
        ## missing scheming_multiple_choice after
        ({"validators": "string_to_choices"}, False),
        ########################################################################
        # Valid cases ({...}, True)                                            #
        ########################################################################
        ({}, True),
        ({"validators": "string_to_choices scheming_multiple_choice"}, True),
    ],
)
def test_validate_dataset_fields(field_kwargs, is_valid):
    if is_valid:
        _get_default_dataset_field(**field_kwargs)
    else:
        with pytest.raises(ValueError):
            _get_default_dataset_field(**field_kwargs)
