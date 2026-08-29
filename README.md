# Thunar custom builds for Ubuntu 24.04

This branch carries the hardened Thunar shortcuts-ordering backport for Ubuntu
24.04. GitHub Actions downloads the official Noble source package, applies the
committed patch through Debian's quilt series, runs the isolated regression
suite, and publishes installable `.deb` artifacts.

No Thunar source tree or build dependencies are required on the target
workstation.

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

The patch is generated from the reviewable source branch
`backport/noble-4.18.8-hardening` in the local upstream checkout. Its three
commits separate the original drag-order feature, production hardening, and
the regression suite. The patch is based on the official `thunar-4.18.8` tag
and currently ends at source commit `235eaee`.

## Build

The workflow is pinned to Ubuntu 24.04 and the official
`thunar_4.18.8-1build3` Noble source package.

```bash
./scripts/build-noble.sh
```

The script is intended for GitHub's disposable Ubuntu runner. It installs build
dependencies, builds `4.18.8-1build3+ignat2`, runs all four headless regression
executables plus the display-dependent shortcuts-view pass under Xvfb, and
writes packages and checksums to `artifacts/`.

## Install

Download the successful workflow artifact and install the matching `thunar` and
`thunar-data` packages together:

```bash
sudo apt install ./thunar-data_*+ignat2_all.deb ./thunar_*+ignat2_amd64.deb
thunar -q
```

Reopen Thunar after quitting it. A reboot or desktop logout is not required.

Normal Ubuntu packages with a newer version supersede this local build. Rebase
and rebuild the patch when Noble publishes a newer Thunar package.

The currently installed `+ignat1` package can remain in place while this branch
builds and is reviewed. Installing `+ignat2` upgrades it in place and preserves
the existing `/shortcuts-places-order` and `/shortcuts-devices-order` values.

To restore Noble's unmodified package explicitly:

```bash
sudo apt install --allow-downgrades \
  thunar=4.18.8-1build3 \
  thunar-data=4.18.8-1build3
```

The saved custom order can be removed independently:

```bash
xfconf-query -c thunar -p /shortcuts-places-order -r
xfconf-query -c thunar -p /shortcuts-devices-order -r
```
