import pytest

from tests.mypy_helpers import MypyAssert


@pytest.fixture
def assert_mypy_output(pytestconfig: pytest.Config) -> MypyAssert:
    from .mypy_helpers import assert_mypy_output

    return lambda program: assert_mypy_output(program, use_pdb=pytestconfig.getoption("usepdb"))
