import base64
import json
import os
import warnings
from typing import Annotated, Union

import requests
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from ..models import (
    FailedUpload,
    SuccessfulUpload,
    SuccessfulUploadWithWarning,
)
from ..utils import validate_data_dict

# TODO: Error out when PAT doesn't exist in environment
GH_PAT = os.environ.get("GH_PAT")

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


@router.put(
    "/upload",
    response_model=Union[SuccessfulUpload, SuccessfulUploadWithWarning],
    responses={400: {"model": FailedUpload}},
)
async def upload(data_dictionary: Annotated[dict, Body()]):
    # TODO: Populate URL based on path parameter (and switch to OpenNeuroDatasets-JSONLD target)
    url = "https://api.github.com/repos/neurobagel/test_json/contents/example_synthetic.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + GH_PAT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    validation_warning = None

    # Catch UserWarnings as exceptions so we can store them in the response
    warnings.simplefilter("error", UserWarning)
    try:
        validate_data_dict(data_dictionary)
    except UserWarning as w:
        validation_warning = str(w)
    except (LookupError, ValueError) as e:
        # NOTE: No validation is performed on a JSONResponse (https://fastapi.tiangolo.com/advanced/response-directly/#return-a-response),
        # but that's okay since we mostly want to see the FailedUpload messages
        return JSONResponse(
            status_code=400, content=FailedUpload(error=str(e)).dict()
        )

    # TODO: If not exists, create a new file instead (use different GitHub API endpoint)
    target_file = requests.get(url, headers=headers)
    target_file_sha = target_file.json()["sha"]

    # Convert the dict to a JSON string and then to base64
    new_data_b64 = base64.b64encode(
        # TODO: Make indentation dynamic
        json.dumps(data_dictionary, indent=4).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "[bot] Updating participants.json",
        "content": new_data_b64,
        "sha": target_file_sha,
    }

    # We use json.dumps to ensure the payload is not form-encoded (the GitHub API expects JSON)
    response = requests.put(url, headers=headers, data=json.dumps(payload))

    if not response.ok:
        return {"error": response.content}

    if validation_warning is not None:
        return SuccessfulUploadWithWarning(
            contents=data_dictionary, warning=validation_warning
        )

    return SuccessfulUpload(contents=data_dictionary)
