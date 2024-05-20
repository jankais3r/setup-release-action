# standard imports
import json
import os
import re
import time

# lib imports
from dotenv import load_dotenv
import requests

# Load the environment variables from the Environment File
load_dotenv()

# root directory of this action
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Get the repository name from the environment variables
REPOSITORY_NAME = os.environ["GITHUB_REPOSITORY"]

# Get the GitHub API token from the environment variables
GITHUB_API_TOKEN = os.environ["INPUT_GITHUB_TOKEN"]

# Define the headers for the GitHub API
GITHUB_HEADERS = {'Authorization': f'token {GITHUB_API_TOKEN}'}


def append_github_step_summary(message: str):
    """
    Append a message to the GitHub Status Summary.

    Parameters
    ----------
    message : str
        The message to append to the GitHub Status Summary. This support markdown.
    """
    with open(os.path.abspath(os.environ["GITHUB_STEP_SUMMARY"]), "a") as f:
        f.write(f'{message}\n')


def set_github_action_output(output_name: str, output_value: str):
    """
    Set the output value by writing to the outputs in the Environment File, mimicking the behavior defined <here
    https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-output-parameter>__.

    Parameters
    ----------
    output_name : str
        Name of the output.
    output_value : str
        Value of the output.
    """
    with open(os.path.abspath(os.environ["GITHUB_OUTPUT"]), "a") as f:
        f.write(f'{output_name}<<EOF\n')
        f.write(output_value)
        f.write('\nEOF\n')


def check_release(version: str) -> bool:
    """
    Check if the release exists in the GitHub API.

    This function will check if the release exists in the GitHub API.

    Parameters
    ----------
    version : str
        Version number of the release.

    Returns
    -------
    bool
        True if the release exists, False otherwise.
    """
    # Get the release from the GitHub API
    version_prefix = os.getenv('INPUT_TAG_PREFIX', 'v')
    github_api_url = f'https://api.github.com/repos/{REPOSITORY_NAME}/releases/tags/{version_prefix}{version}'
    response = requests.get(github_api_url, headers=GITHUB_HEADERS)

    # Check if the release exists
    if response.status_code == 200:
        return True
    else:
        return False


def get_github_event() -> dict:
    """
    Get the GitHub event from the environment variables.

    Returns
    -------
    dict
        Dictionary containing the GitHub event.
    """
    github_event_path = os.getenv(
        'GITHUB_EVENT_PATH', os.path.join(ROOT_DIR, 'dummy_github_event.json')
    )
    with open(github_event_path, 'r') as f:
        github_event = json.load(f)
    return github_event


def get_repo_default_branch() -> str:
    """
    Get the default branch of the repository from the GitHub event context.

    Returns
    -------
    str
        Default branch of the repository.
    """
    # get default branch from event context
    github_event = get_github_event()
    return github_event['repository']['default_branch']


def get_push_event_details() -> dict:
    """
    Get the details of the GitHub push event from the API.

    This function will get the details of the GitHub push event from the API.

    Returns
    -------
    dict
        Dictionary containing the details of the push event.
    """
    # default
    push_event_details = dict(
        publish_release=False,
        release_commit='',
        release_version='',
    )

    github_api_url = f'https://api.github.com/repos/{REPOSITORY_NAME}/events'

    # query parameters
    params = {
        "per_page": 100
    }

    github_event = get_github_event()

    is_pull_request = True if github_event.get("pull_request") else False

    try:
        # set sha to the head sha of the pull request
        github_sha = github_event["pull_request"]["head"]["sha"]
    except KeyError:
        # not a pull request event
        github_sha = os.environ["GITHUB_SHA"]
    push_event_details['release_commit'] = github_sha

    if not is_pull_request:  # this is a push event
        attempt = 0
        push_event = None
        while push_event is None and attempt < int(os.getenv('INPUT_EVENT_API_MAX_ATTEMPTS', 30)):
            time.sleep(10)
            response = requests.get(github_api_url, headers=GITHUB_HEADERS, params=params)

            for event in response.json():
                if event["type"] == "PushEvent" and event["payload"]["head"] == github_sha:
                    push_event = event
                if event["type"] == "PushEvent" and \
                        event["payload"]["ref"] == f"refs/heads/{get_repo_default_branch()}":
                    break

            attempt += 1

        if push_event is None:
            msg = f":exclamation: ERROR: Push event not found in the GitHub API after {attempt} attempts."
            append_github_step_summary(message=msg)
            if os.getenv('INPUT_FAIL_ON_EVENTS_API_ERROR', 'false').lower() == 'true':
                raise SystemExit(msg)
            else:
                return push_event_details
    else:  # this is a pull request
        return push_event_details

    # not a pull request
    push_event_details['publish_release'] = True

    # use regex and convert created at to yyyy.m.d-hhmmss
    # created_at: "2023-1-25T10:43:35Z"
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{2}):(\d{2})Z', push_event["created_at"])

    release_version = ''
    if match:
        year = int(match.group(1))
        month = match.group(2).zfill(2)
        day = match.group(3).zfill(2)
        hour = match.group(4).zfill(2)
        minute = match.group(5).zfill(2)
        second = match.group(6).zfill(2)
        if os.getenv('INPUT_DOTNET', 'false').lower() == 'true':
            # dotnet versioning
            build = f"{hour}{minute}"
            revision = second
            release_version = f"{year}.{int(month)}{day}.{int(build)}.{int(revision)}"
        else:
            # default versioning
            build = f"{hour}{minute}{second}"
            release_version = f"{year}.{int(month)}{day}.{int(build)}"

    push_event_details['release_version'] = release_version
    return push_event_details


def main() -> dict:
    """
    Main function for the action.

    Returns
    -------
    dict
        Job outputs.
    """
    job_outputs = dict()

    # Get the push event details
    push_event_details = get_push_event_details()

    release_generate_release_notes = True
    release_version = push_event_details["release_version"]
    release_tag = f"{release_version}"

    version_prefix = ''
    if os.getenv('INPUT_INCLUDE_TAG_PREFIX_IN_OUTPUT', 'true').lower() == 'true':
        version_prefix = os.getenv('INPUT_TAG_PREFIX', 'v')

    job_outputs['publish_release'] = str(push_event_details['publish_release']).lower()
    job_outputs['release_commit'] = push_event_details['release_commit']
    job_outputs['release_generate_release_notes'] = str(release_generate_release_notes).lower()
    job_outputs['release_version'] = release_version
    job_outputs['release_tag'] = f'{version_prefix if release_tag else ""}{release_tag}'

    # Set the outputs
    for output_name, output_value in job_outputs.items():
        # debug print
        print(f'::debug::Setting output {output_name} to {output_value}')
        set_github_action_output(output_name=output_name, output_value=output_value)

    return job_outputs


if __name__ == "__main__":
    main()
