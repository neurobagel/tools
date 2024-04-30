import pytest

from app.api import utility as utils


@pytest.fixture()
def new_dict():
    return {
        "participant_id": {
            "Description": "Participant ID",
            "Annotations": {
                "IsAbout": {
                    "TermURL": "nb:ParticipantID",
                    "Label": "Unique subject identifier",
                },
                "Identifies": "participant",
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
            },
        },
    }


@pytest.mark.parametrize("example_json", ["0_indents.json", "3_indents.json"])
def test_match_annotations(
    new_dict,
    read_json_as_str,
    original_dicts_path,
    updated_dicts_path,
    example_json,
):
    current_json = read_json_as_str(original_dicts_path / example_json)
    expected_json = read_json_as_str(updated_dicts_path / example_json)

    assert utils.match_indentation(current_json, new_dict) == expected_json


def test_only_annotation_changes(new_dict):
    assert utils.only_annotation_changes(
        current_dict={
            "participant_id": {
                "Description": "Participant ID",
            },
            "age": {
                "Description": "Age of participant",
            },
        },
        new_dict=new_dict,
    )

    assert utils.only_annotation_changes(
        current_dict={
            "participant_id": {
                "Description": "Participant ID",
            },
            "sex": {
                "Description": "Sex variable",
                "Levels": {"0": "Male", "1": "Female"},
                "Annotations": {
                    "IsAbout": {"TermURL": "nb:Sex", "Label": "Sex"},
                    "Levels": {
                        "0": {"TermURL": "snomed:248153007", "Label": "Male"},
                        "1": {
                            "TermURL": "snomed:248152002",
                            "Label": "Female",
                        },
                    },
                    "MissingValues": [],
                },
            },
        },
        new_dict={
            "participant_id": {
                "Description": "Participant ID",
            },
            "sex": {
                "Description": "Sex variable",
                "Levels": {"0": "Male", "1": "Female"},
                "Annotations": {
                    "IsAbout": {"TermURL": "nb:Sex", "Label": "Sex"},
                    "Levels": {
                        "0": {"TermURL": "snomed:248153007", "Label": "Male"},
                        "1": {
                            "TermURL": "snomed:248152002",
                            "Label": "Female",
                        },
                    },
                    "MissingValues": ["NaN"],
                },
            },
        },
    )

    assert not utils.only_annotation_changes(
        current_dict={
            "participant_id": {
                "Description": "Participant ID",
            },
            "sex": {
                "Description": "Sex variable",
                "Levels": {"M": "Male", "F": "Female"},
                "Annotations": {
                    "IsAbout": {"TermURL": "nb:Sex", "Label": "Sex"},
                    "Levels": {
                        "M": {"TermURL": "snomed:248153007", "Label": "Male"},
                        "F": {
                            "TermURL": "snomed:248152002",
                            "Label": "Female",
                        },
                    },
                    "MissingValues": [],
                },
            },
        },
        new_dict={
            "participant_id": {
                "Description": "Participant ID",
            },
            "sex": {
                "Description": "Sex variable",
                "Levels": {"0": "Male", "1": "Female"},
                "Annotations": {
                    "IsAbout": {"TermURL": "nb:Sex", "Label": "Sex"},
                    "Levels": {
                        "0": {"TermURL": "snomed:248153007", "Label": "Male"},
                        "1": {
                            "TermURL": "snomed:248152002",
                            "Label": "Female",
                        },
                    },
                    "MissingValues": [],
                },
            },
        },
    )
