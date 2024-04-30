import base64
import json
import os
import warnings
from typing import Annotated, Union

import requests
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from .. import utility as utils
from ..dictionary_utils import validate_data_dict
from ..models import (
    FailedUpload,
    SuccessfulUpload,
    SuccessfulUploadWithWarnings,
)

# TODO: Error out when PAT doesn't exist in environment
GH_PAT = os.environ.get("GH_PAT")

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


@router.put(
    "/upload",
    response_model=Union[SuccessfulUpload, SuccessfulUploadWithWarnings],
    responses={400: {"model": FailedUpload}},
)
async def upload(data_dictionary: Annotated[dict, Body()]):
    # TODO: Populate URL based on path parameter (and switch to OpenNeuroDatasets-JSONLD target)
    # TODO: Check if **repo** itself exists first
    url = "https://api.github.com/repos/neurobagel/test_json/contents/example_synthetic.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + GH_PAT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # TODO: If not exists, create a new file instead (use different GitHub API endpoint)
    current_file = requests.get(url, headers=headers)
    current_content_json = base64.b64decode(
        current_file.json()["content"]
    ).decode("utf-8")
    current_content_dict = json.loads(current_content_json)
    current_sha = current_file.json()["sha"]

    upload_warnings = []

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

    if utils.any_non_annotation_changes(current_content_dict, data_dictionary):
        # TODO: Also add as note to commit message?
        upload_warnings.append(
            "The uploaded data dictionary may contain changes that are not related to Neurobagel annotations."
        )

    new_content_json = utils.match_indentation(
        current_content_json, data_dictionary
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

    # To send our data over the network, we need to turn it into
    # ascii text by encoding with base64. Base64 takes bytestrings
    # as input. So first we encode to bytestring (with utf), then we
    # base64 encode, and finally decode from base64 bytestring back
    # to plaintext with utf decode.
    new_content_b64 = base64.b64encode(
        # TODO: Make indentation dynamic
        new_content_json.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "[bot] Updating participants.json",
        "content": new_content_b64,
        "sha": current_sha,
    }

    # We use json.dumps to ensure the payload is not form-encoded (the GitHub API expects JSON)
    response = requests.put(url, headers=headers, data=json.dumps(payload))

    if not response.ok:
        return {"error": response.content}

    if upload_warnings:
        return SuccessfulUploadWithWarnings(
            contents=data_dictionary, warnings=upload_warnings
        )

    return SuccessfulUpload(contents=data_dictionary)
