import json


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


def match_indentation(current_json: str | None, new_dict: dict) -> str:
    """
    Match the indentation of the original JSON file and updates it with the annotations.
    NOTE: If the existing JSON file already has an "Annotations" key, we will not raise an error - the contents will simply be updated.

    Parameters
    ----------
    current_json : str
        Target/original data dictionary as a JSON string, or None if the file does not exist
    annotated_file : dict
        (Annotated) data dictionary to be uploaded

    Returns
    -------
    str
    """
    if current_json:
        # Figure out original indentation
        indent = 0
        for line in current_json.splitlines():
            if not line.startswith("{"):
                for char in line:
                    if char != " ":
                        break
                    indent += 1
                break
    else:
        return json.dumps(new_dict, indent=4)

    return json.dumps(new_dict, indent=indent)
