#
# spec file for package claude-desktop
#
# Copyright (c) 2026 Jeroen van Erp
# Copyright (c) 2026 kanonmaten
# Packaging under the MIT License (see LICENSE at the repo root).
#
# Tumbleweed fork of https://github.com/hierynomus/claude-desktop-rpm
#
# All license terms are preserved from the original .deb payload.
# claude-desktop is Anthropic's proprietary desktop app (-> LicenseRef-
# SUSE-NonFree); it also ships LICENSES.chromium.html (Chromium,
# BSD-3-Clause) and Apache-2.0 for the bundled virtiofsd.
#

# SHA256 of the upstream .deb, taken from Anthropic's apt Packages index
# (dists/stable/main/binary-amd64/Packages, field "SHA256:"). Bumped in
# lockstep with Version by scripts/bump-version.sh. Verified in %%prep so a
# changed-out-from-under-us payload fails the build instead of shipping.
%global deb_sha256 4fcf658e0fc895390ab82593287281dfbce261b0ec3ea90060e82d8bfbfd7a84

# Prebuilt Electron payload: nothing to debug, nothing to compile.
%global debug_package %{nil}

Name:           claude-desktop
Version:        4.4212.0
# OBS supplies the real release; 0 is the openSUSE convention.
Release:        0
Summary:        Desktop application for Claude (Chat, Cowork, Code)
License:        LicenseRef-SUSE-NonFree AND BSD-3-Clause AND Apache-2.0
URL:            https://claude.ai
# Fetched at build time by the _service download_url service (see _service).
# Kept as a bare filename so OBS does not treat Source0 as a stored blob.
Source0:        claude-desktop_%{version}_amd64.deb

ExclusiveArch:  x86_64
# Electron's chrome-sandbox is shipped NON-SUID (0755). Chromium prefers the
# unprivileged-user-namespace sandbox and only falls back to the SUID helper
# when userns is unavailable; openSUSE Tumbleweed enables unprivileged userns
# by default (podman-rootless, flatpak). The sandbox stays fully active - this
# is not --no-sandbox. See README "Sandbox".
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
BuildRequires:  file

# Mapping of the .deb's Depends onto openSUSE Tumbleweed packages
# (checked against the Tumbleweed OSS repo, Oct 2026):
#   libgtk-3-0            -> libgtk-3-0
#   libnotify4            -> libnotify4
#   libnss3               -> mozilla-nss
#   xdg-utils             -> xdg-utils
#   libatspi2.0-0         -> libatspi0
#   libdrm2               -> libdrm2
#   libgbm1               -> libgbm1
#   libxcb-dri3-0         -> libxcb-dri3-0
#   libsecret-1-0         -> libsecret-1-0
#   libc6 (>= 2.34)       -> glibc
#   libxtst6              -> libXtst6
#   libuuid1              -> libuuid1
#   libpipewire-0.3-0     -> libpipewire-0_3-0  (screen share on Wayland)
#   xdg-desktop-portal    -> xdg-desktop-portal
#   portal backend alt    -> xdg-desktop-portal-{kde6,gtk,gnome}
#   trash helper alt      -> kde-cli-tools6 | gvfs | trash-cli | glib2-tools
# Rich (boolean) deps keep KDE systems from being forced to pull GNOME bits.
Requires:       glibc >= 2.34
Requires:       libatspi0
Requires:       libdrm2
Requires:       libgbm1
Requires:       libgtk-3-0
Requires:       libnotify4
Requires:       libpipewire-0_3-0
Requires:       libsecret-1-0
Requires:       libuuid1
Requires:       libXtst6
Requires:       libxcb-dri3-0
Requires:       mozilla-nss
Requires:       xdg-desktop-portal
Requires:       xdg-utils
Requires:       (xdg-desktop-portal-kde6 or xdg-desktop-portal-gtk or xdg-desktop-portal-gnome)
Requires:       (kde-cli-tools6 or gvfs or trash-cli or glib2-tools)

# Deb Recommends: audio, tray icon, certs, keyring, Claude Code helpers
# (bubblewrap sandbox, socat, ssh) and the Cowork VM stack.
Recommends:     (libasound2 or libpulse0)
Recommends:     (libayatana-appindicator3-1 or libappindicator3-1)
Recommends:     (kwalletd6 or gnome-keyring)
Recommends:     ca-certificates
Recommends:     bubblewrap
Recommends:     openssh-clients
Recommends:     socat
Recommends:     qemu-ovmf-x86_64
Recommends:     qemu-x86
Recommends:     virtiofsd
Suggests:       lsb-release

%description
Claude desktop application for Linux (beta). Provides Chat, Cowork and
Claude Code in a native app. Upstream only ships .deb builds; this
package repackages the official amd64 .deb payload as an RPM.

Cowork runs in a QEMU virtual machine and needs hardware
virtualization; QEMU, OVMF and virtiofsd are pulled in as
recommended packages and the vhost_vsock module is loaded at boot.

%prep
# Integrity check: the .deb is fetched over TLS by the download_url service;
# pin it to the checksum Anthropic publishes in their apt index as well.
echo '%{deb_sha256}  %{SOURCE0}' | sha256sum -c -
# The .deb is an ar archive: debian-binary, control.tar.xz, data.tar.xz
ar x %{SOURCE0}
mkdir -p payload
tar -xf data.tar.* -C payload

%build
# Nothing to compile: self-contained Electron payload.
# Strip whatever upstream shipped unstripped (the set
# changes between releases, so detect instead of hard-coding paths).
find payload/usr/lib/claude-desktop -type f -print0 \
  | xargs -0 file -N -F '|' \
  | awk -F'|' '/ELF/ && /not stripped/ {print $1}' \
  | while read -r f; do strip --strip-unneeded "$f"; done

%install
APP=%{buildroot}%{_prefix}/lib/claude-desktop
install -dm 0755 %{buildroot}%{_prefix}/lib
cp -a payload/usr/lib/claude-desktop %{buildroot}%{_prefix}/lib/
install -dm 0755 %{buildroot}%{_bindir}
ln -sf ../lib/claude-desktop/claude-desktop %{buildroot}%{_bindir}/claude-desktop

install -Dm 0644 payload/usr/share/applications/com.anthropic.Claude.desktop \
    %{buildroot}%{_datadir}/applications/com.anthropic.Claude.desktop
# Upstream ships Categories=Utility;Development; - two "main" categories,
# which desktop-file-validate/rpmlint reject (the entry would show up twice
# in the menu). Collapse to a single main category.
sed -i 's/^Categories=.*/Categories=Utility;/' \
    %{buildroot}%{_datadir}/applications/com.anthropic.Claude.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/com.anthropic.Claude.desktop
install -dm 0755 %{buildroot}%{_datadir}/icons
cp -a payload/usr/share/icons/hicolor %{buildroot}%{_datadir}/icons/

# What the .deb's postinst writes at install time, done statically here so
# rpm owns the files (and removes them on uninstall):
#  - MIME types for .mcpb / .dxt / .skill
install -Dm 0644 "$APP/resources/linux-mime/com.anthropic.Claude.xml" \
    %{buildroot}%{_datadir}/mime/packages/com.anthropic.Claude.xml
#  - GNOME Shell search provider (inert outside GNOME)
install -Dm 0644 "$APP/resources/gnome-search-provider/com.anthropic.Claude.search-provider.ini" \
    %{buildroot}%{_datadir}/gnome-shell/search-providers/com.anthropic.Claude.search-provider.ini
install -Dm 0644 "$APP/resources/gnome-search-provider/com.anthropic.Claude.SearchProvider.service" \
    %{buildroot}%{_datadir}/dbus-1/services/com.anthropic.Claude.SearchProvider.service
#  - `ccd` terminal launcher, only when this build ships one. The list
#    always holds the main launcher too: rpm rejects an empty -f file.
echo '%{_bindir}/claude-desktop' > extra.files
if [ -x "$APP/resources/bin/ccd" ]; then
  ln -s ../lib/claude-desktop/resources/bin/ccd %{buildroot}%{_bindir}/ccd
  echo '%{_bindir}/ccd' >> extra.files
fi
#  - Cowork's VM needs vhost_vsock. Tumbleweed's udev already makes
#    /dev/kvm and /dev/vhost-vsock world-accessible (0666), so no kvm group
#    is needed; just make sure the module is loaded at boot.
install -dm 0755 %{buildroot}%{_prefix}/lib/modules-load.d
echo vhost_vsock > %{buildroot}%{_prefix}/lib/modules-load.d/claude-desktop.conf
# Skipped on purpose: the AppArmor profile (Ubuntu userns restriction, not
# needed here) and the apt repo/keyring registration (OBS repo replaces it).

# The Electron payload ships many byte-identical files (icon light/dark
# pairs, content-hashed JS chunks); hardlink them. Must be the %%fdupes
# macro, not bare `fdupes`: the macro recurses, plain fdupes does not.
# Scoped to the app dir: the copies in /usr/share must not become hardlinks
# into /usr/lib (rpmlint hardlink-across-partition, badness 10000 each).
%fdupes %{buildroot}%{_prefix}/lib/claude-desktop

# Ship chrome-sandbox NON-SUID (upstream .deb has it 4755). See above.
chmod 0755 "$APP/chrome-sandbox"

# No desktop/icon cache scriptlets: Tumbleweed runs update-desktop-database,
# gtk-update-icon-cache and update-mime-database from file triggers.

%post
# Load vhost_vsock now too, so Cowork works without a reboot.
/usr/sbin/modprobe -q vhost_vsock 2>/dev/null || :

%files -f extra.files
%license payload/usr/share/doc/claude-desktop/copyright
%{_prefix}/lib/claude-desktop
%{_datadir}/applications/com.anthropic.Claude.desktop
%{_datadir}/icons/hicolor
# Shared directories: co-owned so nothing is left unowned when the packages
# that normally own them (shared-mime-info, gnome-shell, dbus) are absent.
%dir %{_datadir}/mime
%dir %{_datadir}/mime/packages
%{_datadir}/mime/packages/com.anthropic.Claude.xml
%dir %{_datadir}/gnome-shell
%dir %{_datadir}/gnome-shell/search-providers
%{_datadir}/gnome-shell/search-providers/com.anthropic.Claude.search-provider.ini
%dir %{_prefix}/lib/modules-load.d
%{_prefix}/lib/modules-load.d/claude-desktop.conf
%dir %{_datadir}/dbus-1
%dir %{_datadir}/dbus-1/services
%{_datadir}/dbus-1/services/com.anthropic.Claude.SearchProvider.service

%changelog
* Fri Oct 30 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 4.4212.0-0
- Update to upstream 4.4212.0

* Wed Oct 28 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 4.29.0-0
- Update to upstream 4.29.0

* Fri Oct 23 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.6556.2-0
- Update to upstream 3.6556.2

* Thu Oct 22 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.6556.1-0
- Update to upstream 3.6556.1

* Thu Oct 22 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.1623.4-0
- Update to upstream 3.1623.4

* Thu Oct 22 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.1623.3-0
- Update to upstream 3.1623.3

* Wed Oct 21 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.1623.1-0
- Update to upstream 3.1623.1

* Tue Oct 20 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 3.1623.0-0
- Update to upstream 3.1623.0

* Mon Oct 19 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 2.42304.2-0
- Update to upstream 2.42304.2

* Fri Oct 16 2026 kanonmaten <86723077+kanonmaten@users.noreply.github.com> - 2.42304.0-0
- Update to upstream 2.42304.0
- Retarget to openSUSE Tumbleweed
- Add deps new in the upstream .deb: libpipewire-0_3-0, portal backend;
  libatspi0 instead of at-spi2-core
- Rich deps for trash helper / portal / keyring so KDE doesn't pull GNOME
- Recommend bubblewrap, socat, openssh-clients and the Cowork VM stack
  (qemu-x86, qemu-ovmf-x86_64, virtiofsd) like the upstream .deb does
- Install MIME types, GNOME search provider and optional ccd launcher
  statically instead of via postinst
- Detect unstripped objects instead of hard-coding paths

* Wed Oct 14 2026 jeroen <jeroen@hierynomus.com> - 2.37337.1-0
- Update to upstream 2.37337.1

* Sat Oct 10 2026 jeroen <jeroen@hierynomus.com> - 2.31226.1-0
- Update to upstream 2.31226.1

* Fri Oct 09 2026 jeroen <jeroen@hierynomus.com> - 2.31226.0-0
- Update to upstream 2.31226.0

* Thu Oct 08 2026 jeroen <jeroen@hierynomus.com> - 2.26454.2-0
- Update to upstream 2.26454.2

* Wed Oct 07 2026 jeroen <jeroen@hierynomus.com> - 2.26454.0-0
- Update to upstream 2.26454.0

* Tue Oct 06 2026 jeroen <jeroen@hierynomus.com> - 2.19675.1-0
- Update to upstream 2.19675.1

* Tue Sep 29 2026 jeroen <jeroen@hierynomus.com> - 2.9939.4-0
- Update to upstream 2.9939.4

* Fri Sep 25 2026 jeroen <jeroen@hierynomus.com> - 2.7032.0-0
- Update to upstream 2.7032.0

* Wed Sep 23 2026 jeroen <jeroen@hierynomus.com> - 2.2553.13-0
- Update to upstream 2.2553.13

* Fri Sep 18 2026 jeroen <jeroen@hierynomus.com> - 2.2553.1-0
- Update to upstream 2.2553.1

* Thu Sep 17 2026 jeroen <jeroen@hierynomus.com> - 2.110.1-0
- Update to upstream 2.110.1

* Wed Sep 16 2026 jeroen <jeroen@hierynomus.com> - 2.110.0-0
- Update to upstream 2.110.0

* Mon Sep 14 2026 jeroen <jeroen@hierynomus.com> - 1.52386.6-0
- Update to upstream 1.52386.6

* Sat Sep 12 2026 jeroen <jeroen@hierynomus.com> - 1.52386.3-0
- Update to upstream 1.52386.3

* Wed Sep 09 2026 jeroen <jeroen@hierynomus.com> - 1.49585.0-0
- Update to upstream 1.49585.0

* Sat Sep 05 2026 jeroen <jeroen@hierynomus.com> - 1.46388.2-0
- Update to upstream 1.46388.2

* Thu Sep 03 2026 jeroen <jeroen@hierynomus.com> - 1.40609.1-0
- Initial packaging: repackage Anthropic's Claude Desktop .deb as an
  openSUSE RPM, built from git via OBS scmsync. Non-SUID chrome-sandbox
  (user-namespace sandbox), SHA256-verified payload, rpmlint clean.
