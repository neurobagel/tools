import re

from fastapi import HTTPException
from pydantic import BaseModel, validator

GH_USERNAME_REGEX = re.compile(
    r"""
    ^(?!.*--)            # no consecutive hyphens
    [A-Za-z0-9]          # first character must be alphanumeric
    ([A-Za-z0-9-]{0,37}  # start of optional group of up to 37 alnum characters or hyphens (1-39 char total)
    [A-Za-z0-9])?$       # must end with an alphanumeric character
""",
    re.VERBOSE,
)


class Contributor(BaseModel):
    """Data model for a contributor who wants to create/make changes to a dataset's data dictionary."""

    name: str
    email: str
    affiliation: str | None = None
    gh_username: str | None = None
    changes_summary: str

    @validator("gh_username")
    def valid_github_username(cls, v):
        """
        Ensure that the GitHub username looks valid according to GitHub's rules -
        this also ensures that the resulting branch name generated for the PR is valid:
        https://docs.github.com/en/enterprise-cloud@latest/admin/managing-iam/iam-configuration-reference/username-considerations-for-external-authentication#about-username-normalization

        NOTE: We currently don't actually check whether the user exists, which is possible but would require
        a separate API call (e.g., https://pygithub.readthedocs.io/en/stable/utilities.html?highlight=githubexception#raw-requests)
        (However, the regex would still be needed, as bot usernames are usually not valid GH usernames)
        """
        if v and not GH_USERNAME_REGEX.fullmatch(v):
            raise HTTPException(
                status_code=422,
                detail="GitHub username (gh_username) contains invalid characters. Please double check that you have entered a valid GitHub username.",
            )
        return v


# NOTE: Because we have multiple successful response models, we need extra="forbid" to
# ensure that instances of SuccessfulUploadWithWarning are not unintentionally
# converted/filtered to the parent SuccessfulUpload by FastAPI when returning a response.
class SuccessfulUpload(BaseModel, extra="forbid"):
    """Data model for a response to a successful upload of a file."""

    message = "Successfully uploaded file to OpenNeuroDatasets-JSONLD."
    pull_request_url: str


class SuccessfulUploadWithWarnings(SuccessfulUpload):
    """Data model for a response to a successful upload of a file with warnings."""

    warnings: list


class FailedUpload(BaseModel):
    """Data model for a response to a failed upload of a file."""

    message = "Failed to upload the file to OpenNeuroDatasets-JSONLD."
    error: str
