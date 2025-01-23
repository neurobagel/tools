import pytest
from fastapi import status

from app.main import app


@pytest.mark.parametrize(
    "path",
    ["/", ""],
)
def test_root(test_app, path, monkeypatch):
    """Given a GET request to the root endpoint, Check for 200 status and expected content."""

    monkeypatch.setattr(app, "root_path", "")
    response = test_app.get(path, follow_redirects=False)

    assert response.status_code == status.HTTP_200_OK
    assert all(
        substring in response.text
        for substring in [
            "Neurobagel-annotated OpenNeuro Datasets",
            '<a href="/docs">API documentation</a>',
        ]
    )


@pytest.mark.parametrize(
    "test_path,expected_status_code",
    [("", 200), ("/upload", 200), ("/wrongroot", 404)],
)
def test_docs_work_using_defined_root_path(
    test_app, test_path, expected_status_code, monkeypatch
):
    """
    Test that when the API root_path is set to a non-empty string,
    the interactive docs and OpenAPI schema are only reachable with the correct path prefix
    (e.g., mimicking access through a proxy) or without the prefix entirely (e.g., mimicking local access or by a proxy itself).

    Note: We test the OpenAPI schema as well because when the root path is not set correctly,
    the docs break from failure to fetch openapi.json.
    (https://fastapi.tiangolo.com/advanced/behind-a-proxy/#proxy-with-a-stripped-path-prefix)
    """

    monkeypatch.setattr(app, "root_path", "/upload")
    docs_response = test_app.get(f"{test_path}/docs", follow_redirects=False)
    schema_response = test_app.get(
        f"{test_path}/openapi.json", follow_redirects=False
    )
    assert docs_response.status_code == expected_status_code
    assert schema_response.status_code == expected_status_code


@pytest.mark.parametrize(
    "test_path,expected_status_code",
    [("", 200), ("/upload/", 200), ("/upload", 404)],
)
def test_docs_when_root_path_includes_trailing_slash(
    test_app, test_path, expected_status_code, monkeypatch
):
    """
    Test that when the API root_path is set with a trailing slash, the interactive docs and OpenAPI schema are only reachable
    using a path prefix with the extra trailing slash also included, or without the prefix entirely.

    This provides a sanity check that the app does not ignore/redirect trailing slashes in the root_path when requests are received.
    """

    monkeypatch.setattr(app, "root_path", "/upload")
    docs_response = test_app.get(f"{test_path}/docs", follow_redirects=False)
    schema_response = test_app.get(
        f"{test_path}/openapi.json", follow_redirects=False
    )
    assert docs_response.status_code == expected_status_code
    assert schema_response.status_code == expected_status_code
