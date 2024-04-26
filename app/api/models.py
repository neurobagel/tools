from pydantic import BaseModel


class SuccessfulUpload(BaseModel, extra="forbid"):
    """Data model for a response to a successful upload of a file."""

    message = "Successfully uploaded file to OpenNeuro-JSONLD."
    contents: dict


class SuccessfulUploadWithWarning(SuccessfulUpload):
    """Data model for a response to a successful upload of a file with warnings."""

    contents: dict
    warning: str


class FailedUpload(BaseModel):
    """Data model for a response to a failed upload of a file."""

    message = "Failed to upload the file to OpenNeuro-JSONLD."
    error: str
