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
])
def test_check_release(version):
    assert main.check_release(version=version[0]) == version[1]


def test_get_repo_default_branch(github_token):
    assert main.get_repo_default_branch() == 'master'


def test_get_push_event_details(github_event_path, input_dotnet, latest_commit):
    assert main.get_push_event_details()


def test_get_push_event_details_no_event(dummy_github_event_path, dummy_commit):
    result = main.get_push_event_details()
    assert result['publish_release'] is False
    assert result['release_version'] == ''


def test_get_push_event_details_fail_on_error(dummy_github_event_path, dummy_commit, fail_on_events_api_error):
    with pytest.raises(SystemExit):
        main.get_push_event_details()


def test_main(github_output_file, github_step_summary_file, github_token, input_dotnet):
    job_outputs = main.main()

    with open(github_output_file, 'r') as f:
        output = f.read()

    for output_name, output_value in job_outputs.items():
        assert f'{output_name}<<EOF\n{output_value}\nEOF\n' in output
