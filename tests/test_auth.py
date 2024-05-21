import base64
import json

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPBasicCredentials

from app.api.routers.openneuro import verify_credentials

# NOTE: Example valid credentials are defined in the pytest.ini file.


@pytest.mark.parametrize(
    "username, password",
    [
        ("johndoe", "wrongpass"),
        ("correct_username", "wrongpass"),
        ("wronguser", "correct_password"),
    ],
)
def test_invalid_credentials_raise_error(username, password):
    with pytest.raises(HTTPException):
        verify_credentials(
            HTTPBasicCredentials(username=username, password=password)
        )


def test_valid_credentials_raise_no_error():
    verify_credentials(
        HTTPBasicCredentials(
            username="correct_username", password="correct_password"
        )
    )


@pytest.mark.parametrize(
    "username, password",
    [
        ("johndoe", "wrongpass"),
        ("correct_username", "wrongpass"),
        ("wronguser", "correct_password"),
    ],
)
def test_invalid_credentials_return_unauthorized_status(
    username,
    password,
    test_app,
    example_new_dict,
):
    current_credentials = f"{username}:{password}"
    # HTTP Basic Auth requires the credentials to be base64 encoded in the "Authorization" header
    encoded_current_credentials = base64.b64encode(
        current_credentials.encode("utf-8")
    ).decode("utf-8")

    response = test_app.put(
        "/openneuro/upload?dataset_id=ds12345",
        headers={"Authorization": "Basic " + encoded_current_credentials},
        content=json.dumps(example_new_dict),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
