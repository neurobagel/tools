import base64
import json
import os
from typing import Annotated

import requests
from fastapi import APIRouter, Body

# TODO: Error out when PAT doesn't exist in environment
GH_PAT = os.environ.get("GH_PAT")

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


@router.put("/upload")
async def upload(data_dictionary: Annotated[dict, Body()]):
    # TODO: Populate URL based on path parameter
    url = "https://api.github.com/repos/neurobagel/test_json/contents/example_synthetic.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + GH_PAT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # TODO: If not exists, create a new file instead
    target_file = requests.get(url, headers=headers)
    target_file_sha = target_file.json()["sha"]

    # Validation here

    # Now we assume the validation is done, so we can convert the dict to a JSON string and then to base64
    new_data_b64 = base64.b64encode(
        # TODO: Make indentation dynamic
        json.dumps(data_dictionary, indent=4).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "[bot] Updating participants.json",
        "content": new_data_b64,
        "sha": target_file_sha,
    }

    # Need to `json.dumps` first b/c the default form encoding is not liked by the GitHub API
    response = requests.put(url, headers=headers, data=json.dumps(payload))

    if not response.ok:
        return {"error": response.content}

    return {"message": "Finished uploading to OpenNeuro-JSONLD."}
