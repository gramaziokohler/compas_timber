import os
import pytest

from compas.data import json_load


@pytest.fixture
def expected_curves():
    filepath = os.path.join(os.path.dirname(__file__), "expected_curves.json")
    return json_load(filepath)
