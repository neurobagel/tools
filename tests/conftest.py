from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def test_app():
    client = TestClient(app)
    yield client


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


@pytest.fixture()
def example_new_dict():
    return {
        "participant_id": {
            "Description": "Participant ID",
            "Annotations": {
                "IsAbout": {
                    "TermURL": "nb:ParticipantID",
                    "Label": "Unique subject identifier",
                },
                "VariableType": "Identifier",
            },
        },
        "age": {
            "Description": "Age of participant",
            "Annotations": {
                "IsAbout": {"TermURL": "nb:Age", "Label": "Age"},
                "Transformation": {
                    "TermURL": "nb:FromFloat",
                    "Label": "float value",
                },
                "MissingValues": [],
                "VariableType": "Continuous",
            },
        },
    }
