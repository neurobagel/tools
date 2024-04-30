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
    bids_only = {
        "participant_id": {
            "Description": "Participant ID",
        },
        "age": {
            "Description": "Age of participant",
        },
    }
    bids_with_annotations = new_dict

    assert (
        utils.only_annotation_changes(
            current_dict=bids_only,
            new_dict=bids_with_annotations,
        )
        is True
    )

    sex_number_coded_annotated = {
        "participant_id": {
            "Description": "Participant ID",
        },
        "sex": {
            "Description": "Sex",
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
    }

    sex_number_coded_annotated_with_missing_value = (
        sex_number_coded_annotated.copy()
    )
    sex_number_coded_annotated_with_missing_value["sex"]["Annotations"][
        "MissingValues"
    ] = ["NaN"]

    sex_letter_coded_annotated = {
        "participant_id": {
            "Description": "Participant ID",
        },
        "sex": {
            "Description": "Sex",
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
    }

    assert (
        utils.only_annotation_changes(
            current_dict=sex_number_coded_annotated,
            new_dict=sex_number_coded_annotated_with_missing_value,
        )
        is True
    )
    assert (
        utils.only_annotation_changes(
            current_dict=sex_number_coded_annotated,
            new_dict=sex_letter_coded_annotated,
        )
        is False
    )
