# OBS setup (one-time)

These steps connect `home:kanonmaten/claude-desktop` on build.opensuse.org to
this repo. You only do them once. After that, a push to `main` triggers a
rebuild and every PR gets a test build.

## How the pieces fit

- This git repo is the package source. The package meta has a `<scmsync>`
  entry (`obs-scm-bridge`), so you never run `osc ci`. The `<scmsync>` URL
  ends in `?subdir=packaging#main`, which means only `packaging/` is
  packaged. A push that doesn't touch `packaging/` produces the same tree, so
  OBS correctly skips the rebuild.
- The 166 MB `.deb` is not stored in git. `packaging/_service` runs
  `download_url` at build time, and `%prep` checks its SHA256 against the
  value in Anthropic's apt `Packages` index.
- `.obs/workflows.yml` in the repo root handles PR builds. OBS branches each
  PR into `home:kanonmaten:ci:kanonmaten:claude-desktop-rpm:PR-<n>`, builds it
  with publishing turned off, and posts the result back to the PR as status
  checks. The branch project is deleted automatically when the PR closes.
- `.github/workflows/upstream-bump.yml` opens a bump PR when Anthropic ships a
  newer build. It needs no OBS credentials.

```
Anthropic apt index ─(hourly)→ bump PR ─→ OBS PR build (status checks)
                                      │
                                    merge ─→ push webhook ─→ rebuild ─→
                                      download.opensuse.org/repositories/home:kanonmaten/
```

## Steps

### 1. OBS side (scripted)

```
scripts/obs-bootstrap.sh
```

You can run it as many times as you like. It creates `home:kanonmaten:ci`
(where PR builds are branched) and sets

```xml
<scmsync>https://github.com/kanonmaten/claude-desktop-rpm?subdir=packaging#main</scmsync>
```

on `home:kanonmaten/claude-desktop`. It also creates the `runservice` token
used in step 3a. To edit the package meta by hand instead:
`osc meta pkg home:kanonmaten claude-desktop -e`.

### 2. GitHub PAT for OBS

Create a fine-grained token for `kanonmaten/claude-desktop-rpm` with:

- Contents: read-only
- Commit statuses: read and write, so OBS can report PR build results

### 3. Two OBS tokens

```
# a) push to main -> re-pull git + rebuild
osc token --create --operation runservice home:kanonmaten claude-desktop

# b) PR events -> run .obs/workflows.yml  (feed it the PAT from step 2)
osc token --create --operation workflow --scm-token <GITHUB_PAT>
```

Each command prints an id and a secret string. You need two tokens because
the two `/trigger/*` endpoints do different jobs. `/trigger/webhook`
(runservice) re-pulls the scmsync source and rebuilds. `/trigger/workflow`
only runs the steps in `.obs/workflows.yml`, and those only cover PRs.

### 4. Two GitHub webhooks

Go to the repo's Settings → Webhooks → Add webhook, and do it twice. Keep SSL
verification on, put the token string in Secret, and set Content type to
`application/json`.

The content type is the step people get wrong. GitHub's "Add webhook" form
defaults to `application/x-www-form-urlencoded`, and the rest of the form
looks fine, so it's easy to leave as is. `/trigger/workflow` rejects a
form-encoded body with a `403` and `X-Opensuse-Errorcode: invalid_token`,
which looks exactly like a wrong secret. `/trigger/webhook` happens to accept
form encoding. So if only the PR builds are broken, check the content type
before you touch the secret.

| Payload URL | Events |
|---|---|
| `https://build.opensuse.org/trigger/webhook?id=<RUNSERVICE_TOKEN_ID>` | Pushes |
| `https://build.opensuse.org/trigger/workflow?id=<WORKFLOW_TOKEN_ID>` | Pull requests |

### 5. GitHub repo setting

In Settings → Actions → General → Workflow permissions, turn on "Allow
GitHub Actions to create and approve pull requests". `upstream-bump` needs
it.

## Check that it works

- Push a commit that changes `packaging/`. `_scmsync.obsinfo` should move
  forward and a build should start:
  `osc api /source/home:kanonmaten/claude-desktop/_scmsync.obsinfo`
- Open a throwaway PR. An "OBS" status check should appear and turn green.
- To force a sync by hand at any time:
  `osc service remoterun home:kanonmaten claude-desktop`

## Troubleshooting

- The PR webhook ping returns `403` with the body
  `<status code="invalid_token"><summary>No valid token found</summary>`.

  This reads like a bad secret, but usually isn't one. First check that the
  token itself is fine by sending a self-signed request straight to OBS,
  without going through GitHub:
  ```sh
  secret=<WORKFLOW_TOKEN_STRING>
  payload='{"zen":"test","repository":{"full_name":"kanonmaten/claude-desktop-rpm"}}'
  sig=$(printf '%s' "$payload" | openssl dgst -sha256 -hmac "$secret" | sed 's/^.* //')
  curl -i -X POST "https://build.opensuse.org/trigger/workflow?id=<WORKFLOW_TOKEN_ID>" \
    -H "Content-Type: application/json" -H "X-GitHub-Event: ping" \
    -H "X-Hub-Signature-256: sha256=$sig" --data "$payload"
  ```
  If this returns `200`, the token and project are wired up correctly, and
  the problem is how GitHub signs its own deliveries. That is almost always
  the webhook's Content type still set to `form` instead of
  `application/json` (see step 4). Only look at the secret itself if this
  request fails too.

## Install on a desktop

```
sudo zypper ar https://download.opensuse.org/repositories/home:kanonmaten/openSUSE_Tumbleweed/home:kanonmaten.repo
sudo zypper refresh
sudo zypper install claude-desktop
```
