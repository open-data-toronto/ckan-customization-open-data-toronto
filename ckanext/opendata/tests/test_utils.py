from typing import List

import pytest
from opendata.util.utils import ListFacet, calculate_list_facets


class TestCalculateListFacets:
    @staticmethod
    def _get_facet_by_name(facets: List[ListFacet], name: str) -> ListFacet:
        filtered = [facet for facet in facets if facet["name"] == name]
        assert len(filtered) > 0, "Not found"
        assert len(filtered) < 2, "Multiple found!"
        return filtered[0]

    @pytest.mark.parametrize(
        "name",
        # Accepts both `json` formatted, or list of strings
        ('["Health"]', ["Health"]),
    )
    @pytest.mark.usefixtures("with_plugins")
    def test_aggregates_facets(self, name):
        in_facets = [
            ListFacet(name=name, display_name=name, count=1),
            ListFacet(
                name='["Health", "Public safety"]',
                display_name='["Health", "Public safety"]',
                count=2,
            ),
        ]
        result = calculate_list_facets(in_facets)
        assert self._get_facet_by_name(result, "Health")["count"] == 3

    @pytest.mark.usefixtures("with_plugins")
    def test_counts_single_occurences(self):
        in_facets = [
            ListFacet(name='["Health"]', display_name='["Health"]', count=1),
            ListFacet(
                name='["Health", "Public safety"]',
                display_name='["Health", "Public safety"]',
                count=2,
            ),
        ]
        result = calculate_list_facets(in_facets)
        assert self._get_facet_by_name(result, "Public safety")["count"] == 2

    @pytest.mark.usefixtures("with_plugins")
    def test_returns_correct_number_of_items(self):
        in_facets = [
            ListFacet(
                name='["Health", "Something"]', display_name='["Health"]', count=1
            ),
            ListFacet(
                name='["Health", "Public safety"]',
                display_name='["Health", "Public safety"]',
                count=2,
            ),
        ]
        result = calculate_list_facets(in_facets)
        n_unique_facets = 3  # Health, Something, Public safety
        assert len(result) == n_unique_facets

    @pytest.mark.usefixtures("with_plugins")
    def test_takes_first_name_as_display_name(self):
        in_facets = [
            ListFacet(name='["Health"]', display_name='["Healthabcds"]', count=1),
            ListFacet(
                name='["Health", "Public safety"]',
                display_name='["Health1234", "Public safety"]',
                count=2,
            ),
        ]
        result = calculate_list_facets(in_facets)

        # the `display_name` of the result should match the `name` of the first
        # encountered facet with that `name` in the input (see NOTE in
        # calculate_list_facets for details)
        assert self._get_facet_by_name(result, "Health")["display_name"] == "Health"

    @pytest.mark.usefixtures("with_plugins")
    def test_accepts_empty(self):
        in_facets = []
        result = calculate_list_facets(in_facets)
        assert len(result) == 0
    
    @pytest.mark.parametrize(
        "not_json",
        ("{not json}", 1, False),
    )
    @pytest.mark.usefixtures("with_plugins")
    def test_warns_invalid_json(self, not_json):
        facets = [ListFacet(name=not_json, display_name=not_json, count=1)]
        with pytest.warns():
            calculate_list_facets(facets)

    @pytest.mark.parametrize(
        "not_json",
        ("{not json}", 1, False),
    )
    @pytest.mark.usefixtures("with_plugins")
    def test_ignores_invalid_json(self, not_json):
        facets = [ListFacet(name=not_json, display_name=not_json, count=1)]
        assert len(calculate_list_facets(facets)) == 0
