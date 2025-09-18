# This file is adapted from https://github.com/neurobagel/bagel-cli/blob/main/bagel/utilities/pheno_utils.py
# and contains only the functions needed for validation of a Neurobagel data dictionary itself.

import warnings
from typing import List, Tuple

import jsonschema
import pydantic

from . import dictionary_models, mappings

DICTIONARY_SCHEMA = dictionary_models.DataDictionary.model_json_schema()


def get_columns_about(data_dict: dict, concept: str) -> list:
    """
    Returns all column names that have been annotated as "IsAbout" the desired concept.
    Parameters
    ----------
    data_dict: dict
        A valid Neurobagel annotated data dictionary must be provided.
    concept: str
        A (shorthand) IRI for a concept that a column can be "about"

    Returns
    list
        List of column names that are "about" the desired concept

    -------

    """
    return [
        col
        for col, content in get_annotated_columns(data_dict)
        if content["Annotations"]["IsAbout"]["TermURL"] == concept
    ]


def get_annotated_columns(data_dict: dict) -> List[Tuple[str, dict]]:
    """
    Return a list of all columns that have Neurobagel 'Annotations' in a data dictionary,
    where each column is represented as a tuple of the column name (dictionary key from the data dictionary) and
    properties (all dictionary contents from the data dictionary).
    """
    return [
        (col, content)
        for col, content in data_dict.items()
        if "Annotations" in content
    ]


def is_column_categorical(column: str, data_dict: dict) -> bool:
    """Determine whether a column in a Neurobagel data dictionary is categorical"""
    column_annotation = data_dict[column]["Annotations"]

    try:
        dictionary_models.CategoricalNeurobagel.model_validate(
            column_annotation
        )
        return True
    except pydantic.ValidationError:
        return False


# TODO: Check all columns and then return list of offending columns' names
def categorical_cols_have_bids_levels(data_dict: dict) -> bool:
    for col, content in get_annotated_columns(data_dict):
        if (
            is_column_categorical(col, data_dict)
            and content.get("Levels") is None
        ):
            return False

    return True


def get_mismatched_categorical_levels(data_dict: dict) -> list:
    """
    Returns list of any categorical columns from a data dictionary that have different entries
    for the "Levels" key between the column's BIDS and Neurobagel annotations.
    """
    mismatched_cols = []
    for col, content in get_annotated_columns(data_dict):
        if is_column_categorical(col, data_dict):
            known_levels = list(
                content["Annotations"]["Levels"].keys()
            ) + content["Annotations"].get("MissingValues", [])
            if set(content.get("Levels", {}).keys()).difference(known_levels):
                mismatched_cols.append(col)

    return mismatched_cols


def validate_data_dict(data_dict: dict) -> None:
    try:
        jsonschema.validate(data_dict, DICTIONARY_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValueError(
            "The data dictionary is not a valid Neurobagel data dictionary. "
            f"Entry that failed validation: {e.path[-1] if e.path else 'Entire document'}\n"
            f"Details: {e.message}\n"
            "TIP: Ensure each annotated column contains an 'Annotations' key."
        ) from e

    if get_annotated_columns(data_dict) == []:
        raise LookupError(
            "The data dictionary must contain at least one column with Neurobagel annotations."
        )

    if (
        len(
            get_columns_about(
                data_dict, concept=mappings.NEUROBAGEL["participant"]
            )
        )
        == 0
    ):
        raise LookupError(
            "The data dictionary must contain at least one column annotated as being about participant ID."
        )

    # TODO: remove this validation when we start handling multiple participant and / or session ID columns
    if (
        len(
            get_columns_about(
                data_dict, concept=mappings.NEUROBAGEL["participant"]
            )
        )
        > 1
    ) | (
        len(
            get_columns_about(
                data_dict, concept=mappings.NEUROBAGEL["session"]
            )
        )
        > 1
    ):
        raise ValueError(
            "The data dictionary has more than one column about participant ID or session ID. "
            "Please ensure only one column is annotated for participant and session IDs."
        )

    if (
        len(get_columns_about(data_dict, concept=mappings.NEUROBAGEL["sex"]))
        > 1
    ):
        warnings.warn(
            "The data dictionary indicates more than one column about sex. "
            "Neurobagel cannot resolve multiple sex values per subject-session, and so will use only the first identified column for sex data."
        )

    if (
        len(get_columns_about(data_dict, concept=mappings.NEUROBAGEL["age"]))
        > 1
    ):
        warnings.warn(
            "The data dictionary indicates more than one column about age. "
            "Neurobagel cannot resolve multiple age values per subject-session, so will use only the first identified column for age data."
        )

    # NOTE: We don't yet expect/allow subject group annotations, but we keep this logic in the data dictionary check
    # for consistency with the CLI, since our data model technically supports subject group.
    if (
        len(
            get_columns_about(
                data_dict, concept=mappings.NEUROBAGEL["subject_group"]
            )
        )
        > 1
    ):
        warnings.warn(
            "The data dictionary indicates more than one column about subject group. "
            "Neurobagel cannot resolve multiple subject group values per subject-session, and so will use only the first identified column for subject group data."
        )

    if not categorical_cols_have_bids_levels(data_dict):
        warnings.warn(
            "The data dictionary contains at least one column that looks categorical but lacks a BIDS 'Levels' attribute."
        )

    if mismatched_cols := get_mismatched_categorical_levels(data_dict):
        warnings.warn(
            f"The data dictionary contains columns with mismatched levels between the BIDS and Neurobagel annotations: {mismatched_cols}"
        )
