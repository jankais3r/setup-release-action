# standard imports
from datetime import datetime
import io
import json
import os
import re

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
    github_event_path = os.environ['GITHUB_EVENT_PATH']
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


def get_repo_squash_and_merge_required() -> bool:
    """
    Check if squash and merge is required for the repository.

    Returns
    -------
    bool
        True if squash and merge is required, False otherwise.

    Raises
    ------
    KeyError
        If the required keys are not found in the GitHub API response.
        Ensure the token has the `"Metadata" repository permissions (read)` scope.
    """
    github_api_url = f'https://api.github.com/repos/{REPOSITORY_NAME}'
    response = requests.get(url=github_api_url, headers=GITHUB_HEADERS)
    repo_info = response.json()

    try:
        allow_squash_merge = repo_info['allow_squash_merge']
        allow_merge_commit = repo_info['allow_merge_commit']
        allow_rebase_merge = repo_info['allow_rebase_merge']
    except KeyError:
        msg = ('::error:: Could not find the required keys in the GitHub API response. '
               'Ensure the token has the `"Metadata" repository permissions (read)` scope.')
        print(msg)
        raise KeyError(msg)

    if allow_squash_merge and not allow_merge_commit and not allow_rebase_merge:
        return True
    else:
        print('::error:: The repository must have ONLY squash and merge enabled.')
        print('::warning:: DO NOT re-run this job after changing the repository settings.'
              'Wait until a new commit is made.')
        return False


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

    github_event = get_github_event()

    is_pull_request = True if github_event.get("pull_request") else False

    try:
        # set sha to the head sha of the pull request
        github_sha = github_event["pull_request"]["head"]["sha"]
    except KeyError:
        # not a pull request event
        github_sha = os.environ["GITHUB_SHA"]
    push_event_details['release_commit'] = github_sha

    if is_pull_request:
        return push_event_details

    # this is a push event
    # check if squash and merge is required
    if not get_repo_squash_and_merge_required():
        msg = (":exclamation: ERROR: Squash and merge is not enabled for this repository. "
               "Please ensure ONLY squash and merge is enabled. "
               "**DO NOT** re-run this job after changing the repository settings. Wait until a new commit is made.")
        append_github_step_summary(message=msg)
        print(f'::error:: {msg}')
        raise SystemExit(2)

    # ensure there is only 1 commit in the github context
    if len(github_event["commits"]) != 1:
        msg = (":exclamation: ERROR: This action only supports a single commit push event. "
               "Please ensure ONLY squash and merge is enabled. "
               "**DO NOT** re-run this job after changing the repository settings. Wait until a new commit is made.")
        append_github_step_summary(message=msg)
        print(f'::error:: {msg}')
        raise SystemExit(3)

    # not a pull request, so publish
    push_event_details['publish_release'] = True

    # get the commit
    commit_timestamp = github_event["commits"][0]['timestamp']

    # use regex and convert created at to yyyy.m.d-hhmmss
    # GitHub can provide timestamps in different formats, ensure we handle them all using `fromisoformat`
    # timestamp: "2023-01-25T10:43:35Z"
    # timestamp "2024-07-14T13:17:25-04:00"
    timestamp = datetime.fromisoformat(commit_timestamp)
    year = timestamp.year
    month = str(timestamp.month).zfill(2)
    day = str(timestamp.day).zfill(2)
    hour = str(timestamp.hour).zfill(2)
    minute = str(timestamp.minute).zfill(2)
    second = str(timestamp.second).zfill(2)

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


def process_release_body(release_body: str) -> str:
    """
    Process the provided release body.

    Replace contributor mentions and PR numbers with GitHub URLs.

    Parameters
    ----------
    release_body : str
       The release body.

    Returns
    -------
    str
       Processed release body.
    """
    # replace contributor mentions with GitHub profile
    processed_body = ''
    re_username = re.compile(r'@([a-zA-Z\d\-]{0,38})')
    re_pr_url = re.compile(r'(https://github\.com/([a-zA-Z\d\-]{0,38})/([a-zA-Z\d-]+)/pull/(\d+))')
    for line in io.StringIO(release_body).readlines():
        # find the username
        username_search = re_username.search(line)
        if not username_search:
            processed_body += line
            continue

        username = username_search.group(1)

        update_pr_url = False
        username_url = f'[@{username}](https://github.com/{username})'
        if ' by @' in line:
            # replace the mention with a GitHub profile URL
            line = line.replace(f' by @{username}', f' by {username_url}')
            update_pr_url = True
        if '* @' in line:
            # replace the mention with a GitHub profile URL
            line = line.replace(f'* @{username}', f'* {username_url}')
            update_pr_url = True
        if update_pr_url:
            pr_search = re_pr_url.search(line)
            if not pr_search:
                processed_body += line
                continue

            pr_url = pr_search.group(1)
            pr_number = pr_search.group(4)

            # replace the pr url with a Markdown link
            line = line.replace(pr_url, f'[#{pr_number}]({pr_url})')

        processed_body += line

    return processed_body


def generate_release_body(tag_name: str, target_commitish: str) -> str:
    """
    Generate the release body, by comparing this SHA to the previous latest release.

    Parameters
    ----------
    tag_name : str
        Tag name of the release.
    target_commitish : str
        The commitish value that determines where the Git tag is created from.

    Returns
    -------
    str
        Release body.
    """
    # Get the latest release from the GitHub API
    github_api_url = f'https://api.github.com/repos/{REPOSITORY_NAME}/releases/latest'
    response = requests.get(github_api_url, headers=GITHUB_HEADERS)

    # Check if the release exists
    if not response.status_code == 200:
        return ''

    latest_release = response.json()

    # generate release notes
    github_api_url = f'https://api.github.com/repos/{REPOSITORY_NAME}/releases/generate-notes'
    data = {
        'tag_name': tag_name,
        'target_commitish': target_commitish,
        'previous_tag_name': latest_release['tag_name'],
    }
    response = requests.post(github_api_url, headers=GITHUB_HEADERS, json=data)

    release_notes = response.json()
    return process_release_body(release_body=release_notes['body'])


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

    release_version = push_event_details["release_version"]
    release_tag = f"{release_version}"

    # generate release notes
    if push_event_details['publish_release']:
        release_body = generate_release_body(
            tag_name=release_tag,
            target_commitish=push_event_details["release_commit"],
        )
    else:
        release_body = ''
    release_generate_release_notes = True if not release_body else False

    version_prefix = ''
    if os.getenv('INPUT_INCLUDE_TAG_PREFIX_IN_OUTPUT', 'true').lower() == 'true':
        version_prefix = os.getenv('INPUT_TAG_PREFIX', 'v')

    job_outputs['publish_release'] = str(push_event_details['publish_release']).lower()
    job_outputs['release_body'] = release_body
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
    main()  # pragma: no cover
