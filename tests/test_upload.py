import io

import pytest


@pytest.mark.parametrize(
    "invalid_username",
    [
        "Neurobagel User",
        "@neurobagel-user",
        "neurobagel-bot[bot]",
        "-neurobagel-user",
        "neurobagel--user",
    ],
)
def test_invalid_gh_usernames_produce_error(test_app, invalid_username):
    """Given an invalid GitHub username, an informative 422 error is produced."""
    test_data_dict_file = io.BytesIO(
        b'{"TestCol": {"Description": "This is a test."}}'
    )

    response = test_app.put(
        "/openneuro/upload",
        params={"dataset_id": "ds12345"},
        files={"data_dictionary": test_data_dict_file},
        data={
            "changes_summary": "Test summary",
            "name": "Neurobagel User",
            "email": "neurobageluser@email.com",
            "gh_username": invalid_username,
        },
    )

    assert response.status_code == 422
    assert (
        "GitHub username (gh_username) contains invalid characters."
        in response.text
    )
