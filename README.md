# claude-desktop for openSUSE Tumbleweed

[![build result](https://build.opensuse.org/projects/home:kanonmaten/packages/claude-desktop/badge.svg?type=default)](https://build.opensuse.org/package/show/home:kanonmaten/claude-desktop)

Repackages Anthropic's official [Claude Desktop](https://claude.ai) Linux
beta (shipped only as `.deb`) into a native **RPM for openSUSE Tumbleweed**,
built and GPG-signed by the [Open Build Service](https://build.opensuse.org)
project [`home:kanonmaten`](https://build.opensuse.org/package/show/home:kanonmaten/claude-desktop).

Fork of [hierynomus/claude-desktop-rpm](https://github.com/hierynomus/claude-desktop-rpm)
(which targets Leap 16). Differences: Tumbleweed target, deps re-mapped for
Tumbleweed and the current upstream `.deb` (PipeWire, portal backend, rich
deps so KDE doesn't pull GNOME), Cowork / Claude Code helpers as
Recommends, MIME types + search provider installed by rpm, and a version
check every 2 hours instead of daily.

## Install

```sh
sudo zypper ar -f https://download.opensuse.org/repositories/home:kanonmaten/openSUSE_Tumbleweed/home:kanonmaten.repo
sudo zypper refresh
sudo zypper install claude-desktop
```

x86_64 only. Updates arrive with `sudo zypper dup`.

Everything (Chat, Cowork, Claude Code) works out of the box: the Cowork VM
stack (QEMU, OVMF, virtiofsd) and Claude Code's helpers come in as
Recommends, the package loads `vhost_vsock`, and Tumbleweed already grants
every user access to `/dev/kvm` and `/dev/vhost-vsock`, so no `kvm` group
is needed. Only requirement: hardware virtualization enabled in firmware.

## How it works

The package source **is this repo**. OBS mirrors `packaging/` via
`<scmsync>` and rebuilds when a push changes it. The 166 MB `.deb` is never
committed: `packaging/_service` fetches it at build time and
`packaging/claude-desktop.spec` verifies its SHA256 in `%prep` against the
value in Anthropic's apt index.

| path | what |
|---|---|
| `packaging/claude-desktop.spec` | the recipe — dependency mapping, `%prep` checksum, non-SUID sandbox |
| `packaging/claude-desktop-rpmlintrc` | rpmlint filters for upstream-inherent / deliberate findings |
| `packaging/_service` | `download_url` for the upstream `.deb` |
| `.obs/workflows.yml` | OBS SCM/CI — build each PR in a scratch project, report status back |
| `.github/workflows/upstream-bump.yml` | every 2 h — open a PR when Anthropic publishes a newer build |
| `.github/workflows/upstream-sync.yml` | daily — open an issue when hierynomus changes the packaging |
| `scripts/bump-version.sh` | rewrite `packaging/` from the apt index (no `.deb` download) |
| `scripts/local-build.sh` | fetch the `.deb` + `rpmbuild -bb` locally, to test before OBS |
| `scripts/obs-bootstrap.sh` | one-time OBS setup (`:ci` project, `<scmsync>`, runservice token) |
| `docs/obs-setup.md` | the one-time token + webhook steps |

## Update flow

1. `upstream-bump.yml` (or `scripts/bump-version.sh` by hand) opens a PR
   bumping `Version` + `%global deb_sha256` + the `_service` URL.
2. OBS test-builds the PR; the status check lands on it.
3. Auto-merge on green → OBS re-syncs and rebuilds `home:kanonmaten/claude-desktop`.

## Local build

```sh
scripts/local-build.sh        # -> ./dist/claude-desktop-*.x86_64.rpm
```

Needs `rpm-build` and `fdupes`. Same `%prep` checksum gate as OBS.

## One-time OBS wiring

See [`docs/obs-setup.md`](docs/obs-setup.md): run `scripts/obs-bootstrap.sh`,
create a GitHub PAT and the `workflow` token, then add two GitHub webhooks
(push → `/trigger/webhook`, PR → `/trigger/workflow`).

## Sandbox

`chrome-sandbox` is shipped **non-SUID** (upstream's `.deb` sets it `4755`).
Chromium prefers the unprivileged **user-namespace sandbox** and only uses
the SUID helper as a fallback; Tumbleweed enables unprivileged user namespaces
by default (podman-rootless, flatpak rely on it), so the sandbox is fully
active. This is *not* `--no-sandbox`, and it's verified working on openSUSE.

If a host has unprivileged userns disabled, the app fails to start with
`The SUID sandbox helper binary was found, but is not configured correctly`.
Re-enable userns (`user.max_user_namespaces`), don't chmod the helper.

## Notes

- Unsigned local builds: `sudo zypper --no-gpg-checks install ./dist/*.rpm`,
  or add the OBS repo (signed) as above.
- `License:` is `LicenseRef-SUSE-NonFree AND BSD-3-Clause AND Apache-2.0` —
  Anthropic's app is proprietary; the payload bundles Chromium (BSD-3) and
  virtiofsd (Apache-2.0).
- If a future `.deb` moves files or adds SUID helpers, update `%files` and
  revisit the sandbox note above.

## License

The packaging in this repo (spec, `_service`, scripts, CI config) is
[MIT](LICENSE). It does not contain or redistribute Claude Desktop itself —
the app is Anthropic's, fetched from their apt repo at build time.
