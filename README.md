# Thunar custom builds for Ubuntu 24.04

This branch builds stable **Thunar 4.20.10** with the existing hardened sidebar
ordering feature for **Ubuntu 24.04**. GitHub Actions downloads checksum-pinned
upstream sources and Debian packaging, applies the committed quilt patch,
runs the isolated regression suite, and publishes installable `.deb` artifacts.

No Thunar source tree or build dependencies are required on the target
workstation. The older 4.18.8 `+ignat2` delivery remains on
`backport/noble-4.18.8-hardening`.

## Hardened customization

- Allow every non-header entry in **Places** and **Devices** to be reordered by
  drag and drop.
- Coordinate integrated Places order with canonical or legacy GTK bookmark
  persistence through a recoverable Xfconf journal.
- Rebase concurrent writers, use bounded and generation-checked bookmark I/O,
  and publish absent bookmark files atomically without replacing another
  writer.
- Keep lock contention off the GTK main loop and coalesce device lifecycle
  retries after a competing process releases the lock.
- Preserve disconnected device slots and conservative restart-stable identity
  claims while failing closed for ambiguous or label-only identities.
- Monitor bookmark pathnames, nearest existing ancestors, and symlink targets;
  keep window menus and accelerators synchronized through source replacement
  and teardown.
- Preserve native entry behavior, icons, visibility, context menus, and GTK
  bookmark synchronization.

The new patch is generated from source branch
`backport/noble-4.20.10-hardening` in the local upstream checkout. It is based
on the official `thunar-4.20.10` tag, commit
`7760dfaa32db5ab6049606ca048ba2219688f369`, and ports the six production
commits from the previously hardened `feature/persistent-shortcut-order`
branch, plus the same four executable regression suite used on 4.18.8.
Compatibility changes preserve native 4.20 APIs and behavior around the
ordering implementation.

The `/shortcuts-places-order`, `/shortcuts-devices-order` and pending-v1
Xfconf format remain compatible with the installed 4.18.8 `+ignat2` build.
The existing limitations still apply: uncooperative GTK clients do not share
Thunar's lock or close-time compare-and-swap; different XDG roots do not
coordinate locks; the journal does not guarantee durability through power loss.

## Build

The workflow is pinned to Ubuntu 24.04 and builds:

- Thunar `4.20.10-1~noble1+ignat1`, using the official 4.20.10 release tarball
  with Debian's 4.20.9 packaging and its normal multiarch module patch.
- Exo `4.20.0-1~noble1+ignat1`, required by Thunar 4.20, against Noble's
  existing GTK and Xfce libraries. Its terminal selection still supports
  `~/.config/xfce4/helpers.rc`.
- Xfce build tools 4.20.0, used only inside CI and excluded from the runtime
  artifact.

```bash
./scripts/build-noble.sh
```

The script is intended for GitHub's disposable Ubuntu runner. It installs
build dependencies, runs all four headless regression executables during the
Debian build, adds the full 18-case shortcuts-view pass under Xvfb, and writes
packages, test logs, build metadata and checksums to `artifacts/`. It refuses
to overwrite an existing `build/` or `artifacts/` directory.

A separate workflow step installs only the runtime bundle into a fresh
Ubuntu 24.04 container and checks the installed binary under Xvfb/private
D-Bus and dynamically loads the optional trash-panel plugin. No additional
package repository or desktop upgrade is needed.
The tarball's bundled D-Bus bindings are regenerated with Noble's
`gdbus-codegen`, including the optional trash-panel plugin, so the result
uses the target release's GLib APIs. Two XML
inputs omitted from the tarball are fetched from the exact upstream release
commit and checksum-verified before generation.

## Install

Download the successful workflow artifact, verify `SHA256SUMS`, and install
the six matching runtime packages together:

```bash
sha256sum --check SHA256SUMS
pkexec apt-get install --yes \
  ./libexo-common_4.20.0-1~noble1+ignat1_all.deb \
  ./libexo-2-0_4.20.0-1~noble1+ignat1_amd64.deb \
  ./exo-utils_4.20.0-1~noble1+ignat1_amd64.deb \
  ./thunar-data_4.20.10-1~noble1+ignat1_all.deb \
  ./libthunarx-3-0_4.20.10-1~noble1+ignat1_amd64.deb \
  ./thunar_4.20.10-1~noble1+ignat1_amd64.deb
thunar -q
```

Reopen Thunar after quitting it. A reboot or desktop logout is not required.

First finish any active file operations before quitting Thunar. Existing
settings, bookmarks, MIME associations and user GTK CSS are retained. If
additional Thunar/Exo development or introspection packages are installed,
upgrade those matching packages from the artifact in the same transaction.

Only packages with a higher Debian version supersede this build. Noble's
4.18 updates do not supersede 4.20, so track upstream stable fixes and rebuild
this branch as needed. No APT hold is installed.

To restore the prior hardened 4.18.8 build, use the retained `+ignat2` Thunar
packages and downgrade its library and the three Exo packages to Noble:

```bash
pkexec apt-get install --yes --allow-downgrades \
  /absolute/path/to/thunar_4.18.8-1build3+ignat2_amd64.deb \
  /absolute/path/to/thunar-data_4.18.8-1build3+ignat2_all.deb \
  libthunarx-3-0=4.18.8-1build3 \
  libexo-2-0=4.18.0-1build4 \
  libexo-common=4.18.0-1build4 \
  exo-utils=4.18.0-1build4
```

To return fully to Noble's unmodified Thunar instead, replace the two file
arguments with `thunar=4.18.8-1build3` and `thunar-data=4.18.8-1build3`.

The saved custom order can be removed independently:

```bash
xfconf-query -c thunar -p /shortcuts-places-order -r
xfconf-query -c thunar -p /shortcuts-devices-order -r
```
