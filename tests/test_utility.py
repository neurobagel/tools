import pytest

from app.api import utility as utils


@pytest.mark.parametrize(
    "original_json, indent_char, indent_num",
    [
        ("0_indents.json", None, 0),
        ("3_indents.json", " ", 3),
        ("2tab_indents.json", "\t", 2),
    ],
)
def test_get_indentation(
    read_json_as_str,
    original_dicts_path,
    original_json,
    indent_char,
    indent_num,
):
    json_str = read_json_as_str(original_dicts_path / original_json)
    assert (indent_char, indent_num) == utils.get_indentation(json_str)


@pytest.mark.parametrize(
    "original_json, expected_char, expected_multiline",
    [
        ("0_indents.json", "\n", True),
        ("0_indents_singleline_nonewline.json", None, False),
        ("0_indents_singleline_withnewline.json", "\n", False),
    ],
)
def test_get_newline_info(
    read_json_as_str,
    original_dicts_path,
    original_json,
    expected_char,
    expected_multiline,
):
    json_str = read_json_as_str(original_dicts_path / original_json)
    assert (expected_char, expected_multiline) == utils.get_newline_info(
        json_str
    )


@pytest.mark.parametrize(
    "indent_char, indent_num, newline_char, multiline, expected_json",
    [
        (None, 0, "\n", True, "0_indents.json"),
        (" ", 3, "\n", True, "3_indents.json"),
        ("\t", 2, "\n", True, "2tab_indents.json"),
        (None, 0, None, False, "0_indents_singleline_nonewline.json"),
        (None, 0, "\n", False, "0_indents_singleline_nonewline.json"),
    ],
)
def test_dict_to_formatted_json(
    read_json_as_str,
    example_new_dict,
    updated_dicts_path,
    indent_char,
    indent_num,
    newline_char,
    multiline,
    expected_json,
):
    expected_json = read_json_as_str(updated_dicts_path / expected_json)
    assert (
        utils.dict_to_formatted_json(
            data_dict=example_new_dict,
            indent_char=indent_char,
            indent_num=indent_num,
            newline_char=newline_char,
            multiline=multiline,
        )
        == expected_json
    )


def test_only_annotation_changes(example_new_dict):
    bids_only = {
        "participant_id": {
            "Description": "Participant ID",
        },
        "age": {
            "Description": "Age of participant",
        },
    }
    bids_with_annotations = example_new_dict

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
