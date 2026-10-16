#!/usr/bin/env bash
# One-time OBS side of the SCM/CI setup. Idempotent; safe to re-run.
#
# Does the parts that can be scripted:
#   - checks home:kanonmaten has an openSUSE_Tumbleweed / x86_64 repo
#   - ensures home:kanonmaten:ci exists (PR branch target) with the same
#     Tumbleweed / x86_64 repo
#   - points home:kanonmaten/claude-desktop at this git repo via <scmsync>
#   - creates the runservice token (push -> rebuild)
#
# The workflow token and the two GitHub webhooks are manual - they need a
# GitHub PAT and the GitHub UI. See docs/obs-setup.md.
#
# Prereqs: osc installed and configured for build.opensuse.org.
# Usage:   scripts/obs-bootstrap.sh [git-url]
set -euo pipefail

OBS_USER="kanonmaten"
PROJ="home:$OBS_USER"
CI_PROJ="home:$OBS_USER:ci"
REPO="openSUSE_Tumbleweed"
PKG="claude-desktop"
GIT_URL="${1:-https://github.com/kanonmaten/claude-desktop-rpm?subdir=packaging#main}"

command -v osc >/dev/null || { echo "osc not installed / not in PATH"; exit 1; }

# Run osc once un-piped so a first-run login prompt is visible (later calls
# pipe osc output into grep, which would swallow the prompt).
osc whoami || { echo "osc login failed"; exit 1; }

echo "==> Checking $PROJ has a $REPO repository"
if osc meta prj "$PROJ" | grep -q "<repository name=\"$REPO\""; then
  echo "    ok"
else
  echo "    missing. Add it in the web UI: $PROJ -> Repositories -> Add from a"
  echo "    Distribution -> openSUSE Tumbleweed (x86_64), then re-run this script."
  exit 1
fi

echo "==> Ensuring $CI_PROJ exists (PR build target)"
if osc meta prj "$CI_PROJ" >/dev/null 2>&1; then
  echo "    already exists"
else
  osc meta prj "$CI_PROJ" -F - <<XML
<project name="$CI_PROJ">
  <title>claude-desktop PR builds</title>
  <description>Throwaway branch target for pull-request builds of $PROJ/$PKG (OBS SCM/CI workflow integration).</description>
  <person userid="$OBS_USER" role="maintainer"/>
  <repository name="$REPO">
    <path project="openSUSE:Factory" repository="snapshot"/>
    <arch>x86_64</arch>
  </repository>
</project>
XML
  echo "    created"
fi

echo "==> Pointing $PROJ/$PKG at git via <scmsync>"
echo "    $GIT_URL"
current=$(osc meta pkg "$PROJ" "$PKG" 2>/dev/null || true)
if grep -qF "$GIT_URL" <<<"$current"; then
  echo "    scmsync already set"
else
  osc meta pkg "$PROJ" "$PKG" -F - <<XML
<package name="$PKG" project="$PROJ">
  <title>Desktop application for Claude.ai (Chat, Cowork, Code)</title>
  <description>Repackage of Anthropic's official Linux .deb as a native RPM for openSUSE. Source: $GIT_URL</description>
  <scmsync>$GIT_URL</scmsync>
</package>
XML
  echo "    set"
fi

echo
echo "==> Creating the runservice token (push -> scmsync re-sync + rebuild)"
osc token --create --operation runservice "$PROJ" "$PKG" 2>&1 || true

cat <<'NEXT'

==> Scripted part done. Remaining manual steps (docs/obs-setup.md):

  1. GitHub: create a fine-grained PAT for kanonmaten/claude-desktop-rpm
     with  Contents: read-only,  Commit statuses: read/write.

  2. OBS workflow token for PR builds (feed it that PAT):
       osc token --create --operation workflow --scm-token <GITHUB_PAT>

  3. GitHub -> repo Settings -> Webhooks -> Add TWO webhooks
     (SSL on; the token string is the Secret):

       a) Payload URL: https://build.opensuse.org/trigger/webhook?id=<RUNSERVICE_TOKEN_ID>
          Events:      Pushes
       b) Payload URL: https://build.opensuse.org/trigger/workflow?id=<WORKFLOW_TOKEN_ID>
          Events:      Pull requests

     Content type: application/json for BOTH - GitHub's form default
     ("Add webhook" pre-selects application/x-www-form-urlencoded) makes
     /trigger/workflow fail with a 403 "invalid_token" that looks exactly
     like a wrong secret. See docs/obs-setup.md#troubleshooting.

     Why two endpoints: /trigger/workflow only runs .obs/workflows.yml
     (PR builds). /trigger/webhook (runservice) re-pulls the scmsync
     source on push.

  4. GitHub Settings -> Actions -> General -> Workflow permissions:
     enable "Allow GitHub Actions to create and approve pull requests".

  5. Verify (after a commit that touches packaging/):
       osc results home:kanonmaten claude-desktop
       osc api /source/home:kanonmaten/claude-desktop/_scmsync.obsinfo
     Force a sync by hand any time with:
       osc service remoterun home:kanonmaten claude-desktop
NEXT
