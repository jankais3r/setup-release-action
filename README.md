# setup-release-action
[![GitHub Workflow Status (CI)](https://img.shields.io/github/actions/workflow/status/lizardbyte/setup-release-action/ci.yml.svg?branch=master&label=CI%20build&logo=github&style=for-the-badge)](https://github.com/LizardByte/setup-release-action/actions/workflows/ci.yml?query=branch%3Amaster)
[![Codecov](https://img.shields.io/codecov/c/gh/LizardByte/setup-release-action.svg?token=joIISKAJtv&style=for-the-badge&logo=codecov&label=codecov)](https://app.codecov.io/gh/LizardByte/setup-release-action)

A reusable action to set up release inputs for GitHub Actions. This action is tailored to the
@LizardByte organization, but can be used by anyone if they follow the same conventions.

The action does the following:

- Get the latest push event to the default branch
- Provide some outputs to use for the release step

## Simple Usage
```yaml
- name: Setup Release
  id: setup_release
  uses: LizardByte/setup-release-action@master
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Advanced Usage
```yaml
- name: Setup Release
  id: setup_release
  uses: LizardByte/setup-release-action@master
  with:
    fail_on_events_api_error: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs
| Name                         | Description                                                                                | Default | Required |
|------------------------------|--------------------------------------------------------------------------------------------|---------|----------|
| dotnet                       | Whether to create a dotnet version (4 components, e.g. yyyy.mmdd.hhmm.ss).                 | `false` | `false`  |
| event_api_max_attempts       | Maximum number of attempts for the GitHub Events API.                                      | `10`    | `false`  |
| fail_on_events_api_error     | Whether to fail if the GitHub Events API returns an error. Will only fail for push events. | `true`  | `false`  |
| github_token                 | GitHub token to use for API requests.                                                      |         | `true`   |
| include_tag_prefix_in_output | Whether to include the tag prefix in the output.                                           | `true`  | `false`  |
| tag_prefix                   | The tag prefix. This will be used when searching for existing releases in GitHub API.      | `v`     | `false`  |

## Outputs
| Name                           | Description                                                                |
|--------------------------------|----------------------------------------------------------------------------|
| publish_release                | Whether or not to publish a release                                        |
| release_body                   | The body for the release                                                   |
| release_commit                 | The commit hash for the release                                            |
| release_generate_release_notes | Whether or not to generate release notes. True if `release_body` is blank. |
| release_tag                    | The tag for the release (i.e. `release_version` with prefix)               |
| release_version                | The version for the release (i.e. `yyyy.mmdd.hhmmss`)                      |
