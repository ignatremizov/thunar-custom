#!/usr/bin/env bash
set -euo pipefail

readonly source_version="4.18.8-1build3"
readonly source_dir="thunar-4.18.8"
readonly source_dsc="https://archive.ubuntu.com/ubuntu/pool/universe/t/thunar/thunar_${source_version}.dsc"
readonly project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly build_root="${project_dir}/build"
readonly artifact_dir="${project_dir}/artifacts"
readonly patch_name="0002-persist-shortcuts-pane-order-hardened.patch"
readonly committed_patch="${project_dir}/patches/${patch_name}"

sudo apt-get update
sudo apt-get install --yes build-essential devscripts equivs quilt xvfb xauth

rm -rf -- "${build_root}" "${artifact_dir}"
mkdir -p -- "${build_root}" "${artifact_dir}"

cd -- "${build_root}"

dget --allow-unauthenticated --extract "${source_dsc}"
cd -- "${source_dir}"

sudo mk-build-deps \
  --install \
  --remove \
  --tool='apt-get --yes --no-install-recommends' \
  debian/control

install -m 0644 \
  "${committed_patch}" \
  "debian/patches/${patch_name}"
printf '%s\n' "${patch_name}" >> debian/patches/series
QUILT_PATCHES=debian/patches quilt --quiltrc /dev/null push -a

DEBEMAIL="ignatremizov@users.noreply.github.com" \
DEBFULLNAME="Ignat Remizov" \
  dch \
    --newversion "${source_version}+ignat2" \
    --distribution noble \
    --force-distribution \
    "Backport hardened persistent ordering for Places and Devices shortcuts."

dpkg-buildpackage --build=binary --no-sign

# Debian's normal build runs the headless suite through dh_auto_test. Repeat
# it explicitly so the workflow contract remains visible if packaging rules
# change, then exercise the display-dependent window/monitor cases under Xvfb.
make -C tests check
xvfb-run -a ./tests/test-shortcuts-view

cp -a ../*.deb ../*.buildinfo ../*.changes "${artifact_dir}/"
cp -a "${committed_patch}" "${artifact_dir}/"
(
  cd -- "${artifact_dir}"
  sha256sum * > SHA256SUMS
)
