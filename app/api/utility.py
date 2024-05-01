import json
from typing import Union


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


def get_newline_character(json_str: str) -> Union[str, None]:
    """
    Extract newline character used in a JSON string, if any.
    NOTE: Does not account for use of mixed newline characters in a file.
    """
    newline_char = None

    for line in json_str.splitlines(keepends=True):
        for e in ("\r\n", "\n"):
            if line.endswith(e):
                newline_char = e
                break
        # # Might not be necessary? Maybe to help remove empty lines?
        # if newline_char:
        #     line = line.rstrip(newline_char)

    return newline_char


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
) -> str:
    """
    Convert a dict to a JSON string with the specified indentation and newline characters.
    """
    indent = indent_char * indent_num if indent_char else None
    indented_json = json.dumps(data_dict, indent=indent)

    return replace_newline_characters(indented_json, newline_char)
