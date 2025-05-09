import base64
import json
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

DATASETS_ORG = "OpenNeuroDatasets-JSONLD"

router = APIRouter(prefix="/openneuro", tags=["openneuro"])


# TODO: Factor out main logic into a CRUD function for easier mocking in tests
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
    affiliation: Annotated[str | None, Form()] = None,
    gh_username: Annotated[str | None, Form()] = None,
):
    # TODO: Consider switching to using this Pydantic model directly for the /upload route form data
    # (see https://fastapi.tiangolo.com/tutorial/request-form-models/ for reference)
    #
    # This would require a slightly bigger refactor than just updating the function signature,
    # since currently, in order to use a Form model and File together, the File must be declared inside the Pydantic model
    # (see https://stackoverflow.com/a/79405574)
    # In that case, the model would include everything other than the dataset_id (incl. the data dictionary file),
    # meaning the model would likely need a rename (e.g., Contributor -> Contribution)
    # and any instances of the Contributor model in the codebase would need to be updated accordingly.
    contributor = Contributor(
        name=name,
        email=email,
        affiliation=affiliation,
        gh_username=gh_username,
        changes_summary=utils.convert_literal_newlines(changes_summary),
    )

    # TODO: Handle network errors
    upload_warnings = []
    file_exists = False

    uploaded_file_contents = await data_dictionary.read()
    try:
        uploaded_dict = json.loads(uploaded_file_contents)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error="The uploaded file is not a valid JSON file."
            ).model_dump(),
        )

    # Create a GitHub instance with the appropriate authentication
    # (See https://pygithub.readthedocs.io/en/stable/examples/Authentication.html#app-installation-authentication)
    auth = Auth.AppAuth(utils.APP_ID, utils.APP_PRIVATE_KEY)
    gi = GithubIntegration(auth=auth)

    # Get the installation ID for the Neurobagel Bot app (for the OpenNeuroDatasets-JSONLD organization)
    installation = gi.get_org_installation(DATASETS_ORG)
    installation_id = installation.id

    g = gi.get_github_for_installation(installation_id)

    # Check if the dataset exists
    try:
        repo = g.get_repo(f"{DATASETS_ORG}/{dataset_id}")
    except UnknownObjectException as e:
        # TODO: Should we explicitly handle 301 Moved permanently responses? These would not be caught by a 404
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"{e.status}: {e.data['message']}. Please ensure you have provided a correct existing dataset ID."
            ).model_dump(),
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
            status_code=400, content=FailedUpload(error=str(e)).model_dump()
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
        # TODO: See if we actually need this check - it seems redundant with a subsequent check which compares
        # the actual existing and uploaded JSON contents after having matched indentation (new_content_json == current_content_json)
        #
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
                content=FailedUpload(error=str(e)).model_dump(),
            )

        # NOTE: Comparing base64 strings doesn't seem to be sufficient for detecting changes. Might be because of differences in encoding?
        # So, we'll compare the JSON strings instead (we do this instead of comparing the dictionaries directly to be able to detect changes in indentation, etc.).
        if new_content_json == current_content_json:
            return JSONResponse(
                status_code=400,
                content=FailedUpload(
                    error="The content selected for upload is the same as in the target file."
                ).model_dump(),
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
        # TODO: Delete the branch if the commit or PR creation fails?
        return JSONResponse(
            status_code=400,
            content=FailedUpload(
                error=f"Something went wrong when updating or creating participants.json in {repo.html_url}. {e.status}: {e.data['message']}"
            ).model_dump(),
        )

    if upload_warnings:
        return SuccessfulUploadWithWarnings(
            pull_request_url=pr.html_url, warnings=upload_warnings
        )
    return SuccessfulUpload(pull_request_url=pr.html_url)
