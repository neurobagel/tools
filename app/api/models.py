from pydantic import BaseModel


class Contributor(BaseModel):
    """Data model for a contributor who wants to create/make changes to a dataset's data dictionary."""

    name: str
    email: str
    # TODO: Include in UI - should be required?
    affiliation: str = None
    gh_username: str = None
    # TODO: Make required in UI (?)
    changes_summary: str


# NOTE: Because we have multiple successful response models, we need extra="forbid" to
# ensure that instances of SuccessfulUploadWithWarning are not unintentionally
# converted/filtered to the parent SuccessfulUpload by FastAPI when returning a response.
class SuccessfulUpload(BaseModel, extra="forbid"):
    """Data model for a response to a successful upload of a file."""

    message = "Successfully uploaded file to OpenNeuro-JSONLD."
    # TODO: Get rid of contents. This doesn't preserve indentation anyways and so is not very useful.
    contents: dict


class SuccessfulUploadWithWarnings(SuccessfulUpload):
    """Data model for a response to a successful upload of a file with warnings."""

    warnings: list


class FailedUpload(BaseModel):
    """Data model for a response to a failed upload of a file."""

    message = "Failed to upload the file to OpenNeuroDatasets-JSONLD."
    error: str
