import json
import random
import string
from typing import Union

from .models import Contributor


def create_random_branch_name(gh_username: str | None = None) -> str:
    """
    Generate a random branch name for a pull request in the format 'update-xxxxxx', or optionally,
    '<username>/update-xxxxxx' if a GitHub username is provided.
    """
    # Define the allowed characters for a branch name
    characters = string.ascii_lowercase + string.digits
    # Generate a random string of the specified length
    branch_name = "update-" + "".join(
        random.choice(characters) for _ in range(6)
    )
    if gh_username:
        branch_name = f"{gh_username}/{branch_name}"

    return branch_name


def create_commit_message(contributor: Contributor, commit_body: str) -> str:
    """Generate a commit message based on the auto-generated main commit body and available contributor info."""
    return (
        f"[bot] {commit_body}\n\n"
        + f"Co-authored-by: {contributor.name} <{contributor.email}>"
    )


def convert_literal_newlines(input_str: str) -> str:
    """
    Convert literal newline characters in a string to a normal newline.

    This is useful because form fields received by FastAPI are treated as raw text, meaning that any \n
    characters in the form data are not automatically interpreted and are treated as literal characters.

    For example, this happens if a curl request contains `-F 'changes_summary=added annotations for:\n -age'` instead of
    `-F $'changes_summary=added annotations for:\n -age'`.
    """
    return input_str.replace("\\n", "\n")


def create_pull_request_body(
    contributor: Contributor, commit_body: str
) -> str:
    """
    Generate a body for the pull request based on the auto-generated main commit message and details provided by the contributor.
    """
    return (
        "### Overview of proposed changes (bot-generated):\n"
        + f"{commit_body}\n\n"
        + "### More details:\n"
        + f"{contributor.changes_summary}\n\n"
        + "### Changes proposed by:\n"
        + f"Name: {contributor.name} "
        + (f"(@{contributor.gh_username})" if contributor.gh_username else "")
        + "\n"
        + f"Affiliation: {contributor.affiliation}\n"
    )


def extract_non_annotations(data_dict: dict) -> dict:
    """
    Return a data dictionary without Neurobagel annotations.
    NOTE: This function cannot guarantee that removed "Annotations" are related to Neurobagel.
    """
    result = {}
    for column, fields in data_dict.items():
        for field, value in fields.items():
            if field != "Annotations":
                result[column] = {field: value}
    return result


def only_annotation_changes(current_dict: dict, new_dict: dict) -> bool:
    """
    Check if there are only changes in the JSON file that are related to annotations.

    Parameters
    ----------
    current_dict : dict
        Original JSON file as a dictionary
    new_dict : dict
        New JSON file as a dictionary

    Returns
    -------
    bool
    """
    return extract_non_annotations(current_dict) == extract_non_annotations(
        new_dict
    )


def get_indentation(json_str: str) -> tuple[Union[str, None], int]:
    """
    Extract the indentation of a JSON string, including the indentation character and level.
    NOTE: Does not account for differing indentation across *different lines* of the same file.

    Parameters
    ----------
    json_str : str
        JSON string

    Returns
    -------
    tuple[Union[str, None], int]
        Tuple containing:
            - indent_char : str or None
                The detected indent character
            - indent_num : int
                The indentation level

    ValueError
        Raised if multiple indentation characters in the same line are detected.
    """
    indent_num = 0
    indent_char = None

    for line_num, line in enumerate(json_str.splitlines()):
        if not line.startswith("{"):
            for char in line:
                if char not in (" ", "\t"):
                    break
                if indent_char is None:
                    indent_char = char
                if char != indent_char:
                    # NOTE: !r means the line will be represented as a string using Python syntax, including any quotes and escape characters.
                    # This makes it easier to identify any special characters or formatting issues.
                    raise ValueError(
                        f"Found mixed indentation of tabs and spaces in line {line_num}: {line!r}"
                    )
                indent_num += 1
            break

    return indent_char, indent_num


def get_newline_info(json_str: str) -> tuple[Union[str, None], bool]:
    """
    Extract newline character used in a JSON string, if any, based on the first detected line.
    NOTE: Does not account for use of mixed newline characters in a file.

    Parameters
    ----------
    json_str : str
        JSON string

    Returns
    -------
    tuple[Union[str, None], bool]
        Tuple containing:
            - newline_char : str or None
                The detected newline character
            - multiline : bool
                Whether the JSON string spans multiple lines
    """
    newline_char = None
    multiline = False

    for line_num, line in enumerate(json_str.splitlines(keepends=True)):
        if line_num > 0:
            multiline = True
            break
        for e in ("\r\n", "\n"):
            if line.endswith(e):
                newline_char = e
                break

    return newline_char, multiline


def replace_newline_characters(
    json_str: str, newline_char: Union[str, None]
) -> str:
    """
    Replace line endings in a JSON string with the specified newline character.
    """
    return json_str.replace("\r\n", newline_char).replace("\n", newline_char)


def dict_to_formatted_json(
    data_dict: dict,
    indent_char: Union[str, None],
    indent_num: int,
    newline_char: Union[str, None],
    multiline: bool,
) -> str:
    """
    Convert a dict to a JSON string with the specified indentation and newline characters.
    NOTE: This does not necessarily preserve existing item or field separators, e.g., "key": "value" vs "key":"value".
    """
    # If there is any indentation
    if indent_char is not None:
        indent = indent_char * indent_num
    # If there is no indentation AND the string spans a single line
    elif newline_char is None or not multiline:
        # This enables the most compact representation, without any newlines but keeping spaces between items
        # (See https://docs.python.org/3/library/json.html#json.dump)
        indent = None
    # If there is no indentation
    else:
        # This still keeps the default newlines
        indent = 0

    formatted_json = json.dumps(data_dict, indent=indent)

    if newline_char is not None:
        formatted_json = replace_newline_characters(
            formatted_json, newline_char
        )

    return formatted_json
