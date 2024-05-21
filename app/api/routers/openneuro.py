import base64
import json
import os
import secrets
import warnings
from typing import Annotated, Union

import requests
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .. import utility as utils
from ..dictionary_utils import validate_data_dict
from ..models import (
    FailedUpload,
    SuccessfulUpload,
    SuccessfulUploadWithWarnings,
)

# TODO: Error out when these variables are not set
GH_PAT = os.environ.get("GH_PAT")
API_USERNAME = bytes(os.environ.get("API_USERNAME"), encoding="utf-8")
API_PASSWORD = bytes(os.environ.get("API_PASSWORD"), encoding="utf-8")

router = APIRouter(prefix="/openneuro", tags=["openneuro"])

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Check if the provided credentials are valid. If not, raise an HTTPException."""
    current_username_bytes = credentials.username.encode("utf-8")
    is_correct_username = secrets.compare_digest(
        current_username_bytes, API_USERNAME
    )

    current_password_bytes = credentials.password.encode("utf-8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, API_PASSWORD
    )

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


# TODO: Factor out main logic into a CRUD function for easier mocking in tests
# For context on how we use dependencies here, see https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/
@router.put(
    "/upload",
    response_model=Union[SuccessfulUpload, SuccessfulUploadWithWarnings],
    responses={400: {"model": FailedUpload}},
    dependencies=[Depends(verify_credentials)],
)
async def upload(dataset_id: str, data_dictionary: Annotated[dict, Body()]):
    # TODO: Handle network errors
    gh_repo_url = f"https://github.com/OpenNeuroDatasets-JSONLD/{dataset_id}"
    repo_url = (
        f"https://api.github.com/repos/OpenNeuroDatasets-JSONLD/{dataset_id}"
    )
    file_url = f"{repo_url}/contents/participants.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + GH_PAT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    upload_warnings = []
    file_exists = False

    response = requests.get(repo_url, headers=headers)
    # TODO: Should we explicitly handle 301 Moved permanently responses? These would fall under response.ok.
    if not response.ok:
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"{response.status_code}: {response.reason}. Please ensure you have provided the correct repository ID."
            ).dict(),
        )

    current_file = requests.get(file_url, headers=headers)
    if current_file.ok:
        file_exists = True
        current_content_json = base64.b64decode(
            current_file.json()["content"]
        ).decode("utf-8")
        current_content_dict = json.loads(current_content_json)
        current_sha = current_file.json()["sha"]
    # TODO: Should we be more specific here, i.e., checking for a 404 status code?
    else:
        upload_warnings.append(
            "No existing participants.json file found in the repository. A new file will be created."
        )

    # Catch validation UserWarnings as exceptions so we can store them in the response
    warnings.simplefilter("error", UserWarning)
    try:
        validate_data_dict(data_dictionary)
    except UserWarning as w:
        upload_warnings.append(str(w))
    except (LookupError, ValueError) as e:
        # NOTE: No validation is performed on a JSONResponse (https://fastapi.tiangolo.com/advanced/response-directly/#return-a-response),
        # but that's okay since we mostly want to see the FailedUpload messages
        return JSONResponse(
            status_code=400, content=FailedUpload(error=str(e)).dict()
        )

    if file_exists:
        commit_message = "[bot] Update participants.json"

        if not utils.only_annotation_changes(
            current_content_dict, data_dictionary
        ):
            upload_warnings.append(
                "The uploaded data dictionary may contain changes that are not related to Neurobagel annotations."
            )
            commit_message += (
                "\n- includes changes unrelated to Neurobagel annotations"
            )
        # Compare dictionaries directly to check for identical contents (ignoring formatting and item order)
        if current_content_dict == data_dictionary:
            upload_warnings.append(
                "The (unformatted) dictionary contents of the uploaded JSON file are the same as the existing JSON file."
            )

        try:
            current_indent_char, current_indent_level = utils.get_indentation(
                current_content_json
            )
            current_newline_char, is_multiline = utils.get_newline_info(
                current_content_json
            )
            new_content_json = utils.dict_to_formatted_json(
                data_dict=data_dictionary,
                indent_char=current_indent_char,
                indent_num=current_indent_level,
                newline_char=current_newline_char,
                multiline=is_multiline,
            )
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content=FailedUpload(error=str(e)).dict(),
            )

        # NOTE: Comparing base64 strings doesn't seem to be sufficient for detecting changes. Might be because of differences in encoding?
        # So, we'll compare the JSON strings instead (we do this instead of comparing the dictionaries directly to be able to detect changes in indentation, etc.).
        if new_content_json == current_content_json:
            return JSONResponse(
                status_code=400,
                content=FailedUpload(
                    error="The content selected for upload is the same in as the target file."
                ).dict(),
            )
    else:
        commit_message = "[bot] Create participants.json"
        new_content_json = json.dumps(data_dictionary, indent=4)

    # To send our data over the network, we need to turn it into
    # ascii text by encoding with base64. Base64 takes bytestrings
    # as input. So first we encode to bytestring (with utf), then we
    # base64 encode, and finally decode from base64 bytestring back
    # to plaintext with utf decode.
    new_content_b64 = base64.b64encode(
        new_content_json.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": new_content_b64,
        **{"sha": current_sha if file_exists else {}},
    }

    # We use json.dumps to ensure the payload is not form-encoded (the GitHub API expects JSON)
    response = requests.put(
        file_url, headers=headers, data=json.dumps(payload)
    )

    if not response.ok:
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"Something went wrong when updating or creating participants.json in {gh_repo_url}. {response.status_code}: {response.reason}"
            ).dict(),
        )
    if upload_warnings:
        return SuccessfulUploadWithWarnings(
            contents=data_dictionary, warnings=upload_warnings
        )
    return SuccessfulUpload(contents=data_dictionary)
