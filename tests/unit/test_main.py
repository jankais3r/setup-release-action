# standard imports
import os

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


@pytest.mark.parametrize('version', [
    ('1970.1.1', False),
    ('2023.1127.235828', True),
])
def test_check_release(version):
    assert main.check_release(version=version[0]) == version[1]


def test_get_repo_default_branch(github_token, github_event_path):
    assert main.get_repo_default_branch() == 'master'


def test_get_repo_squash_and_merge_required(mock_get_repo_squash_and_merge_required):
    assert main.get_repo_squash_and_merge_required() is mock_get_repo_squash_and_merge_required


def test_get_repo_squash_and_merge_required_key_error(mock_get_repo_squash_and_merge_required_key_error):
    with pytest.raises(KeyError):
        main.get_repo_squash_and_merge_required()


def test_get_push_event_details(github_event_path, input_dotnet, latest_commit):
    assert main.get_push_event_details()


def test_get_push_event_details_no_squash(github_event_path, mock_get_squash_and_merge_return_value):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main.get_push_event_details()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2


def test_get_push_event_details_invalid_commits(dummy_github_push_event_path_invalid_commits):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main.get_push_event_details()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 3


def test_process_release_body(release_notes_sample):
    result = main.process_release_body(release_body=release_notes_sample[0])
    assert result == release_notes_sample[1]


def test_generate_release_body(github_token):
    assert main.generate_release_body(tag_name='test', target_commitish=os.environ['GITHUB_SHA'])


def test_generate_release_body_non_200_status_code(github_token, requests_get_error):
    assert main.generate_release_body(tag_name='test', target_commitish='abc') == ''


def test_main_function(
        github_event_path,
        github_output_file,
        github_step_summary_file,
        github_token,
        input_dotnet,
        mock_get_push_event_details,
):
    job_outputs = main.main()

    with open(github_output_file, 'r') as f:
        output = f.read()

    for output_name, output_value in job_outputs.items():
        assert f'{output_name}<<EOF\n{output_value}\nEOF\n' in output
