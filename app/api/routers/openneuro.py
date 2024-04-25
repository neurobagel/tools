import base64
import json
import os
import pathlib

import requests
from fastapi import APIRouter

MY_PAT = os.environ.get("MY_PAT")

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


@router.put("/upload")
async def upload():
    path = pathlib.Path("app/api/routers/example_synthetic.json")

    url = "https://api.github.com/repos/neurobagel/neurobagel_examples/contents/data-upload/example_synthetic.json"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + MY_PAT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    existing_file = requests.get(url, headers=headers)
    existing_file_sha = existing_file.json()["sha"]

    with open(path, "r") as f:
        new_data = json.load(f)

    # Validation here

    # Now we assume the validation is done, so we b64 encoding
    new_data_b64 = base64.b64encode(
        json.dumps(new_data, indent=4).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "now everything is correct",
        "content": new_data_b64,
        "sha": existing_file_sha,
    }

    # Need to `json.dumps` first b/c the default form encoding is not liked by the GitHub API
    response = requests.put(url, headers=headers, data=json.dumps(payload))
    print(response)

    return {"message": "Finished uploading to OpenNeuro-JSONLD."}
