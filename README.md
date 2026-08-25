# Thunar custom builds for Ubuntu 24.04

This repository carries small, reviewable patches for Ubuntu Noble's Thunar
package. GitHub Actions downloads the official Ubuntu source package, applies
the patches through Debian's quilt series, and publishes installable `.deb`
artifacts.

No Thunar source tree or build dependencies are required on the target
workstation.

## Current customization

- Allow every non-header entry in **Places** and **Devices** to be reordered by
  drag and drop.
- Persist Places and Devices independently through Thunar's existing Xfconf
  preferences.
- Preserve native entry behavior, icons, visibility, context menus, and GTK
  bookmark synchronization.
- Restore known device positions by stable device identifier when devices are
  disconnected and later reattached.

## Build

The workflow is pinned to Ubuntu 24.04 and the official
`thunar_4.18.8-1build3` Noble source package.

```bash
./scripts/build-noble.sh
```

The script is intended for GitHub's disposable Ubuntu runner. It installs build
dependencies and writes resulting packages to `artifacts/`.

## Install

Download the successful workflow artifact and install the matching `thunar` and
`thunar-data` packages together:

```bash
sudo apt install ./thunar-data_*+ignat1_all.deb ./thunar_*+ignat1_amd64.deb
thunar -q
```

Reopen Thunar after quitting it. A reboot or desktop logout is not required.

Normal Ubuntu packages with a newer version supersede this local build. Rebase
and rebuild the patch when Noble publishes a newer Thunar package.
