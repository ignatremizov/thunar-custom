#!/usr/bin/env bash
set -euo pipefail

readonly thunar_version="4.20.10"
readonly thunar_package_version="${thunar_version}-1~noble1+ignat1"
readonly exo_package_version="4.20.0-1~noble1+ignat1"
readonly project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly build_root="${project_dir}/build"
readonly artifact_dir="${project_dir}/artifacts"
readonly patch_name="0002-persist-shortcuts-pane-order-hardened-4.20.patch"
readonly committed_patch="${project_dir}/patches/${patch_name}"

# This script installs dependencies and is intended for a disposable Noble
# runner. Refuse to erase output from an earlier build or a local installation.
if [[ -e "${build_root}" || -e "${artifact_dir}" ]]; then
  printf '%s\n' 'Use a clean checkout: build/ and artifacts/ must not exist.' >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install --yes \
  build-essential devscripts equivs quilt xvfb xauth curl dbus-x11 xfconf

mkdir -p -- "${build_root}" "${artifact_dir}"
cd -- "${build_root}"

# Pin both upstream releases and Debian packaging. Newer distro binaries must
# never be installed on the Noble target: every package here is rebuilt on 24.04.
fetch() {
  local url="$1" checksum="$2" filename="$3"
  curl --fail --location --retry 3 --output "${filename}" "${url}"
  printf '%s  %s\n' "${checksum}" "${filename}" | sha256sum --check --strict
}

install_build_dependencies() {
  sudo mk-build-deps \
    --install \
    --remove \
    --tool='apt-get --yes --no-install-recommends' \
    debian/control
}

set_package_version() {
  DEBEMAIL="ignatremizov@users.noreply.github.com" \
  DEBFULLNAME="Ignat Remizov" \
    dch -b --newversion "$1" --distribution noble --force-distribution "$2"
}

# XDT_VERSION_INIT is newer than Noble's build tools. This package is used only
# on the runner and is deliberately excluded from the published runtime bundle.
fetch \
  https://archive.ubuntu.com/ubuntu/pool/universe/x/xfce4-dev-tools/xfce4-dev-tools_4.20.0.orig.tar.bz2 \
  1fba39a08a0ecc771eaa3a3b6e4272a4f0b9e7c67d0f66e780cd6090cd4466aa \
  xfce4-dev-tools_4.20.0.orig.tar.bz2
fetch \
  https://archive.ubuntu.com/ubuntu/pool/universe/x/xfce4-dev-tools/xfce4-dev-tools_4.20.0-2.debian.tar.xz \
  744b39e0357a927041bbb45435f3e3ecc421f41bbafe362b7f6321d1e861d471 \
  xfce4-dev-tools_4.20.0-2.debian.tar.xz
tar -xf xfce4-dev-tools_4.20.0.orig.tar.bz2
tar -xf xfce4-dev-tools_4.20.0-2.debian.tar.xz -C xfce4-dev-tools-4.20.0
(
  cd xfce4-dev-tools-4.20.0
  install_build_dependencies
  set_package_version "4.20.0-2~noble1+ignat1" "Rebuild Xfce build tools for the Noble Thunar runner."
  dpkg-buildpackage --build=binary --no-sign
)
sudo apt-get install --yes ./xfce4-dev-tools_4.20.0-2~noble1+ignat1_amd64.deb

# Thunar 4.20 requires Exo >= 4.19. Rebuild stable Exo against Noble's existing
# GTK/Xfce libraries, retaining its helpers.rc terminal-selection fallback.
fetch \
  https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/exo_4.20.0.orig.tar.bz2 \
  4277f799245f1efde01cd917fd538ba6b12cf91c9f8a73fe2035fd5456ec078d \
  exo_4.20.0.orig.tar.bz2
fetch \
  https://archive.ubuntu.com/ubuntu/pool/universe/e/exo/exo_4.20.0-1.debian.tar.xz \
  285fb4e458364595bb3c976bd43cfb21880b44f0474e935d69dd2123c9d9066a \
  exo_4.20.0-1.debian.tar.xz
tar -xf exo_4.20.0.orig.tar.bz2
tar -xf exo_4.20.0-1.debian.tar.xz -C exo-4.20.0
(
  cd exo-4.20.0
  install_build_dependencies
  set_package_version "${exo_package_version}" "Rebuild stable Exo for hardened Thunar on Ubuntu 24.04."
  dpkg-buildpackage --build=binary --no-sign
)
sudo apt-get install --yes \
  "./libexo-common_${exo_package_version}_all.deb" \
  "./libexo-2-0_${exo_package_version}_amd64.deb" \
  "./libexo-2-dev_${exo_package_version}_amd64.deb" \
  "./exo-utils_${exo_package_version}_amd64.deb"

fetch \
  "https://archive.xfce.org/src/xfce/thunar/4.20/thunar-${thunar_version}.tar.bz2" \
  a5a32b51028dc821155e44cdec025fe70398bae193c619ae6ba8b1babf6f49f1 \
  "thunar_${thunar_version}.orig.tar.bz2"
fetch \
  https://archive.ubuntu.com/ubuntu/pool/universe/t/thunar/thunar_4.20.9-1.debian.tar.xz \
  0b3e1945f15c1e34be6d15c5be5b8e14080f0ad55ca26a44f540c7d275fbb38d \
  thunar_4.20.9-1.debian.tar.xz
tar -xf "thunar_${thunar_version}.orig.tar.bz2"
tar -xf thunar_4.20.9-1.debian.tar.xz -C "thunar-${thunar_version}"
(
  cd "thunar-${thunar_version}"
  install_build_dependencies
  install -m 0644 "${committed_patch}" "debian/patches/${patch_name}"
  printf '%s\n' "${patch_name}" >> debian/patches/series
  QUILT_PATCHES=debian/patches quilt --quiltrc /dev/null push -a
  set_package_version "${thunar_package_version}" \
    "Port hardened persistent Places and Devices ordering to stable Thunar 4.20.10."
  # dh_auto_test runs the four headless executables. Xvfb adds the full
  # display-dependent view, window, accelerator and monitor coverage.
  dpkg-buildpackage --build=binary --no-sign
  xvfb-run -a ./tests/test-shortcuts-view | tee "${artifact_dir}/shortcuts-view-xvfb.log"
  cp tests/test-suite.log "${artifact_dir}/"
)

for package in thunar thunar-data libthunarx-3-0 libthunarx-3-dev gir1.2-thunarx-3.0 \
               libexo-common libexo-2-0 libexo-2-dev exo-utils; do
  cp "${package}_"*.deb "${artifact_dir}/"
done
cp thunar_*.buildinfo thunar_*.changes exo_*.buildinfo exo_*.changes "${artifact_dir}/"
cp -a "${committed_patch}" "${artifact_dir}/"
(
  cd -- "${artifact_dir}"
  sha256sum * > SHA256SUMS
)
