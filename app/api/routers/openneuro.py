import base64
import json
import os
import warnings
from typing import Annotated, Union

from fastapi import APIRouter, File, Form, UploadFile
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
    data_dictionary: Annotated[UploadFile, File()],
    changes_summary: Annotated[str, Form()],
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    # TODO: Should be required?
    affiliation: Annotated[str | None, Form()] = None,
    gh_username: Annotated[str | None, Form()] = None,
):
    # TODO: Switch to using this Pydantic model directly for the /upload route form data once we
    # upgrade the FastAPI version to >= 0.113.0 (and ensure that Pydantic v1 can still be used)
    # See https://fastapi.tiangolo.com/tutorial/request-form-models/
    contributor = Contributor(
        name=name,
        email=email,
        affiliation=affiliation,
        gh_username=gh_username,
        changes_summary=changes_summary,
    )

    # TODO: Handle network errors
    gh_repo_url = f"https://github.com/OpenNeuroDatasets-JSONLD/{dataset_id}"

    upload_warnings = []
    file_exists = False

    # Load private key from file to avoid newline issues when a multiline key is set in .env
    with open(APP_PRIVATE_KEY_PATH, "r") as f:
        APP_PRIVATE_KEY = f.read()

    uploaded_file_contents = await data_dictionary.read()
    try:
        uploaded_dict = json.loads(uploaded_file_contents)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error="The uploaded file is not a valid JSON file."
            ).dict(),
        )

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

    # Needed because some repos in OpenNeuroDatasets-JSONLD have "main" default, others have "master"
    default_branch = repo.default_branch

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
        validate_data_dict(uploaded_dict)
    except UserWarning as w:
        upload_warnings.append(str(w))
    except (LookupError, ValueError) as e:
        # NOTE: No validation is performed on a JSONResponse (https://fastapi.tiangolo.com/advanced/response-directly/#return-a-response),
        # but that's okay since we mostly want to see the FailedUpload messages
        return JSONResponse(
            status_code=400, content=FailedUpload(error=str(e)).dict()
        )

    if file_exists:
        commit_body = "Update participants.json"

        if not utils.only_annotation_changes(
            current_content_dict, uploaded_dict
        ):
            upload_warnings.append(
                "The uploaded data dictionary may contain changes that are not related to Neurobagel annotations."
            )
            commit_body += (
                "\n- includes changes unrelated to Neurobagel annotations"
            )
        # Compare dictionaries directly to check for identical contents (ignoring formatting and item order)
        if current_content_dict == uploaded_dict:
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
                data_dict=uploaded_dict,
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
                    error="The content selected for upload is the same as in the target file."
                ).dict(),
            )
    else:
        commit_body = "Add participants.json"
        new_content_json = json.dumps(uploaded_dict, indent=4)

    # Create a new branch to commit the data dictionary to
    branch_name = utils.create_random_branch_name(contributor.gh_username)
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=repo.get_branch(default_branch).commit.sha,
    )

    # Commit uploaded data dictionary to the new branch, and open a PR
    commit_message = utils.create_commit_message(
        contributor=contributor, commit_body=commit_body
    )
    try:
        if file_exists:
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

        pr_body = utils.create_pull_request_body(
            contributor=contributor, commit_body=commit_body
        )
        pr = repo.create_pull(
            base=default_branch,
            head=branch_name,
            # Get the first line of the commit body as the PR title
            title=commit_body.splitlines()[0],
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
            pull_request_url=pr.html_url, warnings=upload_warnings
        )
    return SuccessfulUpload(pull_request_url=pr.html_url)
