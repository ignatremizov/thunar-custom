#!/usr/bin/env bash
set -euo pipefail

readonly source_version="4.18.8-1build3"
readonly source_dir="thunar-4.18.8"
readonly source_dsc="https://archive.ubuntu.com/ubuntu/pool/universe/t/thunar/thunar_${source_version}.dsc"
readonly project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly build_root="${project_dir}/build"
readonly artifact_dir="${project_dir}/artifacts"
readonly patch_name="0002-persist-shortcuts-pane-order.patch"
readonly generated_patch="${build_root}/${patch_name}"

sudo apt-get update
sudo apt-get install --yes build-essential devscripts equivs quilt

rm -rf -- "${build_root}" "${artifact_dir}"
mkdir -p -- "${build_root}" "${artifact_dir}"

python3 "${project_dir}/scripts/generate-patch.py" \
  --source-dir "${build_root}/upstream-git" \
  --output "${generated_patch}"

cd -- "${build_root}"

dget --allow-unauthenticated --extract "${source_dsc}"
cd -- "${source_dir}"

sudo mk-build-deps \
  --install \
  --remove \
  --tool='apt-get --yes --no-install-recommends' \
  debian/control

install -m 0644 \
  "${generated_patch}" \
  "debian/patches/${patch_name}"
printf '%s\n' "${patch_name}" >> debian/patches/series
QUILT_PATCHES=debian/patches quilt --quiltrc /dev/null push -a

DEBEMAIL="ignatremizov@users.noreply.github.com" \
DEBFULLNAME="Ignat Remizov" \
  dch \
    --local "+ignat" \
    --distribution noble \
    --force-distribution \
    "Persist drag-and-drop ordering for Places and Devices shortcuts."

dpkg-buildpackage --build=binary --no-sign

cp -a ../*.deb ../*.buildinfo ../*.changes "${artifact_dir}/"
cp -a "${generated_patch}" "${artifact_dir}/"
sha256sum "${artifact_dir}"/* > "${artifact_dir}/SHA256SUMS"
