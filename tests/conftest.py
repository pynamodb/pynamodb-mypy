import pytest


@pytest.fixture
def assert_mypy_output(pytestconfig):
    from .mypy_helpers import assert_mypy_output
    return lambda program: assert_mypy_output(program, use_pdb=pytestconfig.getoption('usepdb'))
