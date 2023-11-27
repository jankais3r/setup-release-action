# standard imports
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


def check_if_changelog_exists(changelog_path: str) -> bool:
    """
    Check if the changelog exists.

    This function will first check if the changelog exists at the given path.

    Parameters
    ----------
    changelog_path : str
        Full path to the changelog file.

    Returns
    -------
    bool
        True if the changelog exists, False otherwise.
    """
    # Check if the changelog exists
    if os.path.exists(changelog_path):
        return True
    else:
        return False


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

    response = requests.get(github_api_url, headers=GITHUB_HEADERS, params=params)
    push_event = None

    github_event = get_github_event()
    try:
        # set sha to the head sha of the pull request
        github_sha = github_event["pull_request"]["head"]["sha"]
    except KeyError:
        # not a pull request event
        github_sha = os.environ["GITHUB_SHA"]
        push_event_details['publish_release'] = True
    push_event_details['release_commit'] = github_sha

    for event in response.json():
        if event["type"] == "PushEvent" and event["payload"]["head"] == github_sha:
            push_event = event
        if event["type"] == "PushEvent" and event["payload"]["ref"] == f"refs/heads/{get_repo_default_branch()}":
            break

    if push_event is None:
        msg = ":exclamation: ERROR: Push event not found in the GitHub API."
        append_github_step_summary(message=msg)
        if os.getenv('INPUT_FAIL_ON_EVENTS_API_ERROR', 'false').lower() == 'true':
            raise SystemExit(msg)
        else:
            return push_event_details

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
        build = f"{hour}{minute}{second}"
        release_version = f"{year}.{int(month)}{day}.{int(build)}"

    push_event_details['release_version'] = release_version
    return push_event_details


def parse_changelog(changelog_path: str) -> dict:
    """
    Parse the changelog file.

    This function will parse the changelog and return a dictionary.

    Parameters
    ----------
    changelog_path : str
        Full path to the changelog file.

    Returns
    -------
    dict
        Dictionary containing the following keys:

        - version
        - date
        - changes
        - url
    """
    with open(changelog_path, 'r') as file:
        changelog_content = file.read()

    # Define regular expressions to match version headers and their content
    version_pattern = r'\[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})'
    url_pattern = r'\[(\d+\.\d+\.\d+)\]:\s+(https:\/\/\S+)'

    # Find all version headers and their content
    versions = re.findall(version_pattern, changelog_content)
    urls = re.findall(url_pattern, changelog_content)

    # Determine the newest version based on the version numbers
    newest_version = max(versions, key=lambda x: tuple(map(int, x[0].split('.'))))

    # Find the URL associated with the newest version
    newest_version_url = None
    for version, url in urls:
        if version == newest_version[0]:
            newest_version_url = url
            break

    # Extract the changes for the newest version
    newest_version_changes = ""
    in_newest_version_section = False
    for version, date in versions:
        if version == newest_version[0]:
            in_newest_version_section = True
        elif in_newest_version_section and version != newest_version[0]:
            break
        if in_newest_version_section:
            version_start = changelog_content.find(f'[{version}] - {date}')
            next_version = versions.index((version, date)) + 1
            if next_version < len(versions):
                version_end = changelog_content.find(
                    f'\n## [{versions[next_version][0]}] - {versions[next_version][1]}', version_start)
            else:
                version_end = len(changelog_content)

            # Extract changes while excluding the start of the next version
            if version_end != -1:
                newest_version_changes = changelog_content[version_start:version_end]
            else:
                newest_version_changes = changelog_content[version_start:]

    # Remove the version header line from the changes
    newest_version_changes = newest_version_changes.replace(f'[{newest_version[0]}] - {newest_version[1]}\n', '')

    # Remove the URL line from the changes
    if newest_version_url:
        newest_version_changes = newest_version_changes.replace(f'[{newest_version[0]}]: {newest_version_url}\n', '')

    # Create a dictionary with the extracted information
    changelog_data = {
        'version': newest_version[0],
        'date': newest_version[1],
        'url': newest_version_url,
        'changes': newest_version_changes.strip()
    }

    return changelog_data


def main() -> dict:
    """
    Main function for the action.

    Returns
    -------
    dict
        Job outputs.
    """
    job_outputs = dict()

    # Get the inputs from the Environment File
    changelog_path = os.path.join(os.environ['GITHUB_WORKSPACE'], os.environ["INPUT_CHANGELOG_PATH"])

    # Get the push event details
    push_event_details = get_push_event_details()

    # Check if the changelog exists
    changelog_exists = check_if_changelog_exists(changelog_path=changelog_path)
    job_outputs["changelog_exists"] = str(changelog_exists)

    changelog_data = None
    release_exists = False
    # Parse the changelog
    if changelog_exists:
        changelog_data = parse_changelog(changelog_path=changelog_path)
        job_outputs['changelog_changes'] = changelog_data["changes"]
        job_outputs['changelog_date'] = changelog_data["date"]
        job_outputs['changelog_url'] = changelog_data["url"]
        job_outputs['changelog_version'] = changelog_data["version"]

        # Check if the release exists
        release_exists = check_release(version=changelog_data["version"])
    else:
        job_outputs['changelog_changes'] = ''
        job_outputs['changelog_date'] = ''
        job_outputs['changelog_url'] = ''
        job_outputs['changelog_version'] = ''

    job_outputs['changelog_release_exists'] = str(release_exists)
    job_outputs['publish_pre_release'] = str(release_exists).lower()
    job_outputs['publish_stable_release'] = str(not release_exists).lower()

    if release_exists:
        # the changelog release exists in GitHub
        append_github_step_summary(
            message=":warning: WARNING: The release in the changelog already exists. Defaulting to a pre-release.")

    if release_exists or not changelog_exists:
        # the changelog release exists, so we want to publish a pre-release
        # or the changelog does not exist, so we want to publish a stable rolling release
        release_body = ''
        release_generate_release_notes = True
        release_version = push_event_details["release_version"]
        release_tag = f"{release_version}"
    else:
        # the changelog release does not exist, so we want to publish a stable release
        release_body = changelog_data["changes"]
        release_generate_release_notes = False
        release_version = changelog_data["version"] if changelog_data else ''
        release_tag = f"{release_version}"

    version_prefix = ''
    if os.getenv('INPUT_INCLUDE_TAG_PREFIX_IN_OUTPUT', 'true').lower() == 'true':
        version_prefix = os.getenv('INPUT_TAG_PREFIX', 'v')

    job_outputs['publish_release'] = str(push_event_details['publish_release']).lower()
    job_outputs['release_body'] = release_body
    job_outputs['release_commit'] = push_event_details['release_commit']
    job_outputs['release_generate_release_notes'] = str(release_generate_release_notes).lower()
    job_outputs['release_version'] = release_version
    job_outputs['release_tag'] = f'{version_prefix}{release_tag}'

    # Set the outputs
    for output_name, output_value in job_outputs.items():
        # debug print
        print(f'::debug::Setting output {output_name} to {output_value}')
        set_github_action_output(output_name=output_name, output_value=output_value)

    return job_outputs


if __name__ == "__main__":
    main()
