[![codecov](https://codecov.io/gh/neurobagel/tools/graph/badge.svg?token=3E2e6vNiih)](https://codecov.io/gh/neurobagel/tools)
[![Python versions](https://img.shields.io/badge/python-3.10-4682B4?style=flat)](https://www.python.org)
[![License](https://img.shields.io/github/license/neurobagel/tools?color=CD5C5C&style=flat)](LICENSE)

# tools
Other helpful tools for interfacing with Neurobagel

## Steps to deploy
1. Create a file containing a [private key](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps) for the Neurobagel Bot app
2. Create a .env file with the following variables:
    - `NB_BOT_ID`: the **app ID** of the Neurobagel Bot app, which you can find on the [settings page for the app](https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration#navigating-to-your-github-app-settings)
    - `HOST_NB_BOT_KEY_PATH`: the path to the private key file on your machine (if not provided, will default to `./private_key.pem`)
    - (OPTIONAL) `NB_UPLOADER_API_ROOT_PATH`: if using a proxy server that serves this app from a path/subdirectory, the path prefix declared for this app (that should be stripped by the proxy), e.g., `/upload`. 
    **Should not include a trailing slash!** 
3. Navigate to the root of the repository and run:
    ```bash
    docker compose up -d
    ```

## Setting up a development environment
If running the OpenNeuro Uploader API as a Python app, ensure that the following environment variables are set:
- `NB_BOT_ID`: the **app ID** of the Neurobagel Bot app (found on the [settings page for the app](https://docs.github.com/en/apps/maintaining-github-apps/modifying-a-github-app-registration#navigating-to-your-github-app-settings))
- `NB_BOT_KEY_PATH`: path to a file containing a [private key](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps) for the Neurobagel Bot app
