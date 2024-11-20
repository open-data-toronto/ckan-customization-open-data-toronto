from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, model_validator

################################################################################
# Scheming Validation                                                          #
################################################################################


class _DataStoreColumns(BaseModel):
    value: str
    label: str


class DatasetField(BaseModel):
    choices_helper: Optional[str] = ""
    datastore_choices_columns: Optional[_DataStoreColumns] = None
    datastore_choices_resource: Optional[str] = ""
    display_property: Optional[str] = ""
    display_snippet: Optional[str] = ""
    field_name: str
    form_placeholder: Optional[str] = ""
    form_snippet: Optional[str] = ""
    help_text: Optional[str] = ""
    label: str
    output_validators: Optional[str] = ""
    required: Optional[bool] = False
    validators: Optional[str] = ""

    @staticmethod
    def _follows_in_list(items: List[Any], first_item: Any, follows_item: Any) -> bool:
        try:
            first_index = items.index(first_item)
        except ValueError:
            first_index = None
        return (first_index is not None) and (follows_item in items[first_index:])

    @model_validator(mode="after")
    @classmethod
    def datastore_requires_choices(cls, data: Any) -> Any:
        ds_resource_defined = data.datastore_choices_resource != ""
        ds_choice_cols_defined = data.datastore_choices_columns is not None
        if ds_resource_defined != ds_choice_cols_defined:
            raise ValueError(
                "Both datastore_choices_resource and datastore_choices_columns "
                "must be defined if using datastore choices."
            )
        return data

    @model_validator(mode="after")
    @classmethod
    def scheming_choices_does_not_follow_string_to_choices(cls, data: Any) -> Any:
        validators = data.validators
        split_validators = validators.split(" ")

        if cls._follows_in_list(
            split_validators, "string_to_choices", "scheming_choices"
        ):
            raise ValueError(
                "scheming_choices validator should not follow after"
                " string_to_choices as this will result in comparison of Lists "
                "to string choices. Did you mean to use "
                "scheming_multiple_choice?"
            )
        return data

    @model_validator(mode="after")
    @classmethod
    def scheming_multiple_choice_follows_string_to_choices(cls, data: Any) -> Any:
        validators = data.validators
        split_validators = validators.split(" ")

        if (
            ("scheming_multiple_choice" in split_validators)
            or ("string_to_choices" in split_validators)
        ) and not cls._follows_in_list(
            split_validators, "string_to_choices", "scheming_multiple_choice"
        ):
            raise ValueError(
                "string_to_choices and scheming_multiple_choice must be used "
                "together such that scheming_multiple_choice follows "
                "string_choices."
            )
        return data


class _ResourceFields(BaseModel):
    # No validation applied on Resource Fields at present. Consider adding if
    # required.
    pass


class SchemingSchema(BaseModel):
    scheming_version: Literal[2]
    dataset_type: str
    about: Optional[str] = ""
    about_url: Optional[str] = ""

    dataset_fields: List[DatasetField]
    resource_fields: List[_ResourceFields]
