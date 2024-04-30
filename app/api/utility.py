import json


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
