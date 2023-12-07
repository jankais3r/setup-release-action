# lib imports
import pytest

# local imports
from action import main


@pytest.mark.parametrize('message', [
    'foo',
    'bar',
])
def test_append_github_step_summary(github_step_summary_file, message):
    main.append_github_step_summary(message=message)

    with open(github_step_summary_file, 'r') as f:
        output = f.read()

    assert output.endswith(f"{message}\n")


@pytest.mark.parametrize('outputs', [
    ('test_1', 'foo'),
    ('test_2', 'bar'),
])
def test_set_github_action_output(github_output_file, outputs):
    main.set_github_action_output(output_name=outputs[0], output_value=outputs[1])

    with open(github_output_file, 'r') as f:
        output = f.read()

    assert output.endswith(f"{outputs[0]}<<EOF\n{outputs[1]}\nEOF\n")


def test_check_if_changelog_exists(changelog_set):
    if changelog_set['changelog_expected']:
        assert main.check_if_changelog_exists(changelog_path=changelog_set['changelog_path'])


@pytest.mark.parametrize('version', [
    ('1970.1.1', False),
])
def test_check_release(version):
    assert main.check_release(version=version[0]) == version[1]


def test_get_repo_default_branch(github_token):
    assert main.get_repo_default_branch() == 'master'


def test_get_push_event_details(github_event_path, input_dotnet, latest_commit):
    assert main.get_push_event_details()


def test_parse_changelog(changelog_set):
    if changelog_set['changelog_expected']:
        changelog_data = main.parse_changelog(changelog_path=changelog_set['changelog_path'])

        assert changelog_data['version'] == changelog_set['version']
        assert changelog_data['date'] == changelog_set['date']
        assert changelog_data['url'] == changelog_set['url']
        assert changelog_data['changes'] == changelog_set['changes']


def test_main(changelog_set, github_output_file, github_step_summary_file, github_token, input_dotnet):
    job_outputs = main.main()

    with open(github_output_file, 'r') as f:
        output = f.read()

    for output_name, output_value in job_outputs.items():
        assert f'{output_name}<<EOF\n{output_value}\nEOF\n' in output
