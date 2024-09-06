from pydantic import BaseModel


class Contributor(BaseModel):
    """Data model for a contributor who wants to create/make changes to a dataset's data dictionary."""

    name: str
    email: str
    affiliation: str | None = None
    gh_username: str | None = None
    changes_summary: str


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
