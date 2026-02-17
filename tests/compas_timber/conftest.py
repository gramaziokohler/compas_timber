from compas.tolerance import TOL
import pytest


@pytest.fixture(autouse=True)
def reset_tolerance():
    """
    Reset the global tolerance before each test.
    This fixture is automatically applied to all tests.
    It enforces test isolation by ensuring that no test depends on tolerance values modified by other tests.
    Tests that require a non-default tolerance must set it explicitly within their own scope.
    """
    TOL.reset()
    TOL.unit = "MM"
