"""
Utilities for writing tests.

Note this module should not contain tests themselves.
"""

import ckan.tests.helpers as helpers


def mock_actions(mocker, **kwargs):
    def _get_action(action):
        mocked_const = kwargs.get(action)
        if mocked_const is None:
            return helpers.get_action(action)
        return lambda *args, **kwargs: mocked_const

    mocker.patch("ckan.plugins.toolkit.get_action", _get_action)
