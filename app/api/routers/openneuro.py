import base64
import json
import os
import warnings
from typing import Annotated, Union

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from github import Auth, GithubIntegration
from github.GithubException import GithubException, UnknownObjectException

from .. import utility as utils
from ..dictionary_utils import validate_data_dict
from ..models import (
    Contributor,
    FailedUpload,
    SuccessfulUpload,
    SuccessfulUploadWithWarnings,
)

# TODO: Error out when these variables are not set
APP_ID = os.environ.get("NB_BOT_ID")
APP_PRIVATE_KEY_PATH = os.environ.get("NB_BOT_KEY_PATH")

DATASETS_ORG = "OpenNeuroDatasets-JSONLD"

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


# TODO: Factor out main logic into a CRUD function for easier mocking in tests
# For context on how we use dependencies here, see https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/
@router.put(
    "/upload",
    response_model=Union[SuccessfulUpload, SuccessfulUploadWithWarnings],
    responses={400: {"model": FailedUpload}},
)
async def upload(
    dataset_id: str,
    contributor: Contributor,
    data_dictionary: Annotated[dict, Body()],
):
    # TODO: Handle network errors
    gh_repo_url = f"https://github.com/OpenNeuroDatasets-JSONLD/{dataset_id}"

    upload_warnings = []
    file_exists = False

    # Load private key from file to avoid newline issues when a multiline key is set in .env
    with open(APP_PRIVATE_KEY_PATH, "r") as f:
        APP_PRIVATE_KEY = f.read()

    # Create a GitHub instance with the appropriate authentication
    auth = Auth.AppAuth(APP_ID, APP_PRIVATE_KEY)
    gi = GithubIntegration(auth=auth)

    # Get the installation ID for the Neurobagel Bot app (for the OpenNeuroDatasets-JSONLD organization)
    installation = gi.get_org_installation(DATASETS_ORG)
    installation_id = installation.id
    # TODO: Remove - for debugging
    print(installation_id)

    g = gi.get_github_for_installation(installation_id)

    # Check if the dataset exists
    try:
        repo = g.get_repo(f"{DATASETS_ORG}/{dataset_id}")
    except UnknownObjectException as e:
        # TODO: Should we explicitly handle 301 Moved permanently responses? These would not be caught by a 404
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"{e.status}: {e.data['message']}. Please ensure you have provided a correct existing repository ID."
            ).dict(),
        )

    # Get participants.json contents if the file exists
    try:
        current_file = repo.get_contents("participants.json")
        file_exists = True
        current_content_json = base64.b64decode(current_file.content).decode(
            "utf-8"
        )
        current_content_dict = json.loads(current_content_json)
    except UnknownObjectException:
        upload_warnings.append(
            "No existing participants.json file found in the repository. A new file will be created."
        )

    # Validate the uploaded data dictionary
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
        change_message_short = "Update participants.json"
        commit_message = f"[bot] {change_message_short}"

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

        # Match indentation
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
        change_message_short = "Add participants.json"
        commit_message = f"[bot] {change_message_short}"
        new_content_json = json.dumps(data_dictionary, indent=4)

    # Create a new branch to commit the data dictionary to
    branch_name = utils.create_random_branch_name(contributor.gh_username)
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}", sha=repo.get_branch("main").commit.sha
    )

    # # To send our data over the network, we need to turn it into
    # # ascii text by encoding with base64. Base64 takes bytestrings
    # # as input. So first we encode to bytestring (with utf), then we
    # # base64 encode, and finally decode from base64 bytestring back
    # # to plaintext with utf decode.
    # new_content_b64 = base64.b64encode(
    #     new_content_json.encode("utf-8")
    # ).decode("utf-8")

    # Commit uploaded data dictionary to the new branch, and open a PR
    try:
        if file_exists:
            # TODO: Remove - for debugging
            print(current_file.path)
            repo.update_file(
                current_file.path,
                commit_message,
                new_content_json,
                current_file.sha,
                branch=branch_name,
            )
        else:
            repo.create_file(
                "participants.json",
                commit_message,
                new_content_json,
                branch=branch_name,
            )

        # TODO: Update PR body
        pr_body = "FILLER"
        repo.create_pull(
            base="main",
            head=branch_name,
            title=change_message_short,
            body=pr_body,
        )
    except GithubException as e:
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"Something went wrong when updating or creating participants.json in {gh_repo_url}. {e.status}: {e.data['message']}"
            ).dict(),
        )

    if upload_warnings:
        return SuccessfulUploadWithWarnings(
            contents=data_dictionary, warnings=upload_warnings
        )
    return SuccessfulUpload(contents=data_dictionary)
