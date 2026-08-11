from opendata.plugin import UpdateSchemaPlugin


class TestUpdateDatastoreInfoField:
    """
    Some ETL configs store data dictionary label/notes as null instead of "",
    which crashes datatables_view's core template (it calls len() on the value).
    update_datastore_info_field sanitizes these at read time via IDataDictionaryForm.
    """

    @staticmethod
    def _update(field):
        return UpdateSchemaPlugin().update_datastore_info_field(field, {})

    def test_replaces_null_label_and_notes_with_empty_string(self):
        field = {"id": "ADDRESS_POINT_ID", "type": "float", "info": {"label": None, "notes": None}}
        result = self._update(field)
        assert result["info"]["label"] == ""
        assert result["info"]["notes"] == ""

    def test_preserves_existing_non_null_values(self):
        field = {"id": "CIVIC_CENTRE", "type": "text", "info": {"label": "Civic Centre", "notes": "Civic centre code"}}
        result = self._update(field)
        assert result["info"]["label"] == "Civic Centre"
        assert result["info"]["notes"] == "Civic centre code"

    def test_handles_missing_info_key(self):
        field = {"id": "OBJECTID", "type": "text"}
        result = self._update(field)
        assert result == {"id": "OBJECTID", "type": "text"}

    def test_handles_empty_info_dict(self):
        field = {"id": "OBJECTID", "type": "text", "info": {}}
        result = self._update(field)
        assert result["info"] == {}

    def test_treats_absent_key_same_as_null(self):
        field = {"id": "OBJECTID", "type": "text", "info": {"notes": None}}
        result = self._update(field)
        assert result["info"]["notes"] == ""
        assert result["info"]["label"] == ""

    def test_datastore_create_schema_is_unchanged(self):
        schema = {"fields": []}
        assert UpdateSchemaPlugin().update_datastore_create_schema(schema) is schema
