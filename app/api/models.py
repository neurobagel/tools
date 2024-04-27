from pydantic import BaseModel


# NOTE: Because we have multiple successful response models, we need extra="forbid" to
# ensure that instances of SuccessfulUploadWithWarning are not unintentionally
# converted/filtered to the parent SuccessfulUpload by FastAPI when returning a response.
class SuccessfulUpload(BaseModel, extra="forbid"):
    """Data model for a response to a successful upload of a file."""

    message = "Successfully uploaded file to OpenNeuro-JSONLD."
    # TODO: Get rid of contents. This doesn't preserve indentation anyways and so is not very useful.
    contents: dict


class SuccessfulUploadWithWarning(SuccessfulUpload):
    """Data model for a response to a successful upload of a file with warnings."""

    warning: str


class FailedUpload(BaseModel):
    """Data model for a response to a failed upload of a file."""

    message = "Failed to upload the file to OpenNeuroDatasets-JSONLD."
    error: str
