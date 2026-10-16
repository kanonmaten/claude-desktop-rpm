# claude-desktop for openSUSE Tumbleweed

[![build result](https://build.opensuse.org/projects/home:kanonmaten/packages/claude-desktop/badge.svg?type=default)](https://build.opensuse.org/package/show/home:kanonmaten/claude-desktop)

This repo turns Anthropic's official [Claude Desktop](https://claude.ai)
Linux beta, which only ships as a `.deb`, into a native RPM for openSUSE
Tumbleweed. The [Open Build Service](https://build.opensuse.org) builds and
signs it in the project
[`home:kanonmaten`](https://build.opensuse.org/package/show/home:kanonmaten/claude-desktop).

It's a fork of [hierynomus/claude-desktop-rpm](https://github.com/hierynomus/claude-desktop-rpm),
which targets Leap 16. What's different here:

- It builds for Tumbleweed.
- Dependencies are mapped to Tumbleweed package names and to what the
  current upstream `.deb` needs, including PipeWire and a portal backend.
  Where several packages would do, the spec accepts any of them, so a KDE
  system doesn't pull in GNOME.
- The Cowork and Claude Code helpers are Recommends.
- rpm installs the MIME types and the GNOME search provider itself.
- It checks for a new version every hour instead of once a day.

## Install

```sh
sudo zypper ar -f https://download.opensuse.org/repositories/home:kanonmaten/openSUSE_Tumbleweed/home:kanonmaten.repo
sudo zypper refresh
sudo zypper install claude-desktop
```

The package is x86_64 only. Updates come with `sudo zypper dup`.

Chat, Cowork and Claude Code all work right after install. The Cowork VM
stack (QEMU, OVMF, virtiofsd) and Claude Code's helpers come in as
Recommends, and the package loads `vhost_vsock`. Tumbleweed already gives
every user access to `/dev/kvm` and `/dev/vhost-vsock`, so you don't need to
join the `kvm` group. The one thing you need is hardware virtualization
turned on in your firmware.

## How it works

This repo is the package source. OBS mirrors `packaging/` through
`<scmsync>` and rebuilds whenever a push changes it. The 166 MB `.deb` stays
out of git: `packaging/_service` downloads it at build time, and
`packaging/claude-desktop.spec` checks its SHA256 in `%prep` against the
value in Anthropic's apt index.

| Path | What it does |
|---|---|
| `packaging/claude-desktop.spec` | The recipe: dependency mapping, the `%prep` checksum, the non-SUID sandbox |
| `packaging/claude-desktop-rpmlintrc` | rpmlint filters for findings that come from upstream or are deliberate |
| `packaging/_service` | `download_url` for the upstream `.deb` |
| `.obs/workflows.yml` | OBS SCM/CI: builds each PR in a scratch project and reports the result back |
| `.github/workflows/upstream-bump.yml` | Runs hourly and opens a PR when Anthropic publishes a newer build |
| `.github/workflows/upstream-sync.yml` | Runs daily and opens an issue when hierynomus changes the packaging |
| `scripts/bump-version.sh` | Rewrites `packaging/` from the apt index without downloading the `.deb` |
| `scripts/local-build.sh` | Downloads the `.deb` and runs `rpmbuild -bb`, to test locally before OBS |
| `scripts/obs-bootstrap.sh` | One-time OBS setup: the `:ci` project, `<scmsync>`, the runservice token |
| `docs/obs-setup.md` | The one-time token and webhook steps |

## Update flow

1. `upstream-bump.yml`, or `scripts/bump-version.sh` run by hand, opens a PR
   that bumps `Version`, `%global deb_sha256` and the `_service` URL.
2. OBS test-builds the PR and posts the result as a status check.
3. When the check passes, the PR merges itself, and OBS re-syncs and
   rebuilds `home:kanonmaten/claude-desktop`.

## Local build

```sh
scripts/local-build.sh        # -> ./dist/claude-desktop-*.x86_64.rpm
```

You need `rpm-build` and `fdupes`. The `%prep` checksum check is the same as
on OBS.

## One-time OBS wiring

[`docs/obs-setup.md`](docs/obs-setup.md) has the details. In short: run
`scripts/obs-bootstrap.sh`, create a GitHub PAT and the `workflow` token,
then add two GitHub webhooks (push to `/trigger/webhook`, PR to
`/trigger/workflow`).

## Sandbox

The package ships `chrome-sandbox` without the SUID bit; upstream's `.deb`
sets it to `4755`. Chromium prefers the unprivileged user-namespace sandbox
and only falls back to the SUID helper. Tumbleweed enables unprivileged user
namespaces by default (rootless podman and flatpak depend on them), so the
sandbox stays fully on. This doesn't turn the sandbox off the way
`--no-sandbox` would, and it has been tested on openSUSE.

If a machine has unprivileged user namespaces disabled, the app won't start
and prints `The SUID sandbox helper binary was found, but is not configured
correctly`. Turn user namespaces back on (`user.max_user_namespaces`)
instead of changing the helper's permissions.

## Notes

- To install an unsigned local build, run
  `sudo zypper --no-gpg-checks install ./dist/*.rpm`, or add the signed OBS
  repo as shown above.
- The `License:` field is `LicenseRef-SUSE-NonFree AND BSD-3-Clause AND Apache-2.0`.
  Anthropic's app is proprietary, and it bundles Chromium (BSD-3) and
  virtiofsd (Apache-2.0).
- If a future `.deb` moves files or adds SUID helpers, update `%files` and
  check the sandbox section again.

## License

The packaging in this repo (spec, `_service`, scripts, CI config) is
[MIT](LICENSE). The repo doesn't contain or redistribute Claude Desktop
itself. The app belongs to Anthropic and is downloaded from their apt repo at
build time.
