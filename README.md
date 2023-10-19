# action-setup-release
A reusable action to setup release inputs for GitHub Actions. This action is tailored to the
@LizardByte organization, but can be used by anyone if they follow the same conventions.

The action does the following:

- Get the latest push event to the default branch
- Check if `CHANGELOG.md` file exists
- If it does, parse the file and extract the following properties
  - Latest version
  - Latest version date
  - Latest version changes
  - Latest version release url
- If the changelog exists, check if the latest release is already GitHub release
- Setup the correct type of release based on the conditions above

## Simple Usage
```yaml
- name: Setup Release
  id: setup_release
  uses: LizardByte/action-setup-release@master
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Advanced Usage
```yaml
- name: Setup Release
  id: setup_release
  uses: LizardByte/action-setup-release@master
  with:
    changelog_path: ./docs/CHANGELOG.md
    fail_on_events_api_error: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs
| Name                     | Description                                                  | Default        | Required |
|--------------------------|--------------------------------------------------------------|----------------|----------|
| changelog_path           | The path to the changelog file                               | `CHANGELOG.md` | `false`  |
| fail_on_events_api_error | Fail if the action cannot find this commit in the events API | `false`        | `false`  |
| github_token             | The GitHub token to use for API calls                        |                | `true`   |

## Outputs
| Name                     | Description                                                                      |
|--------------------------|----------------------------------------------------------------------------------|
| changelog_changes        | The changes for the latest version in the changelog                              |
| changelog_date           | The date for the latest version in the changelog                                 |
| changelog_exists         | Whether or not the changelog file exists                                         |
| changelog_release_exists | Whether or not the latest version is a GitHub release                            |
| changelog_url            | The url for the latest version in the changelog                                  |
| changelog_version        | The version for the latest version in the changelog                              |
| publish_stable_release   | Whether or not to publish a stable release                                       |
| release_build            | The build number to identify this build (i.e. first 7 characters of commit hash) |
| release_tag              | The tag for the release (i.e. `release_version`-`release_build`)                 |
| release_version          | The version for the release (i.e. `yyyy.m.d` or `changelog_version`)             |

## Basic Flow
```mermaid
graph TD

subgraph "Setup Release"
  A[Get Push Event Details from API]

  B[Changelog Exists?]
  C[Parse Changelog]
  D[Release Exists in GitHub?]

  E[Prepare Release]
  F[Prepare Pre-Release]
  G[Set GitHub Outputs]
end

A --> B
B --> |True| C
C --> D
B --> |False| E
D --> |False| E
D --> |True| F
E --> G
F --> G

```

## Expected Outputs
```mermaid
graph TD

subgraph "Set GitHub Outputs"
  A{Changelog Exists?}
  B(changelog_exists = 'True')
  C(changelog_changes = \list of changes\)
  D(changelog_date = \date from changelog\)
  E(changelog_url = \url from changelog\)
  F(changelog_version = \version from changelog\)

  I(changelog_exists = 'False')
  J(changelog_changes = '')
  K(changelog_date = '')
  L(changelog_url = '')
  M(changelog_version = '')

  N(release_build = \commit 0-7\)

  O{GitHub Release Exists?}
  P(changelog_release_exists = 'True')
  Q(publish_stable_release = 'False')
  R(release_version = 'yyyy.m.d')
  S(release_tag = `release_version`-`release_build`)

  U(changelog_release_exists = 'False')
  V(publish_stable_release = 'True')
  W(release_version = \changelog version\)
  X(release_tag = `release_version`)
end

A --> |True| B
B --> C
C --> D
D --> E
E --> F
F --> N

A --> |False| I
I --> J
J --> K
K --> L
L --> M
M --> N

N --> O

O --> |True| P
P --> Q
Q --> R
R --> S

O --> |False| U
U --> V
V --> W
W --> X

```
