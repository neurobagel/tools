from pathlib import Path

import pytest


@pytest.fixture()
def read_json_as_str():
    """Read in a JSON file as a string."""

    def _read_json_as_str(path: Path) -> str:
        with open(path, "r") as f:
            return f.read()

    return _read_json_as_str


@pytest.fixture(scope="session")
def original_dicts_path():
    return Path(__file__).absolute().parent / "test_data" / "original"


@pytest.fixture(scope="session")
def updated_dicts_path():
    return Path(__file__).absolute().parent / "test_data" / "updated"
