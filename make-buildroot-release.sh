#!/bin/bash


current_dir=$(pwd)
echo "Working directory is '$current_dir'"

# Source code initialization script

# Check if buildroot directory exists and has sufficient subdirectories
subdir_count=0
if [ -d "${current_dir}/buildroot" ]; then
    subdir_count=$(find ${current_dir}/buildroot -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
fi

# Initialize only when buildroot doesn't exist or has less than 2 subdirectories
if [ ! -d "${current_dir}/buildroot" ] || [ "$subdir_count" -lt 2 ]; then
    echo "Buildroot directory missing or incomplete (subdirs: $subdir_count), initializing..."
    /usr/bin/git pull && /usr/bin/git submodule update --init --recursive
    /usr/bin/git submodule sync
    echo "Buildroot initialization completed!"
else
    echo "Buildroot directory exists and is complete (subdirs: $subdir_count), skipping sync"
fi

mkdir -p /cache
mkdir -p /build

# Keep host tools to avoid recompilation, remove target packages (kernel, u-boot, etc.) to force rebuild
# Exception: force rebuild host-uboot-tools to regenerate boot.scr
find ${current_dir}/output/build -maxdepth 1 -type d ! -name "host-*" ! -name "build" -exec rm -rf {} + 2>/dev/null || true
rm -rf ${current_dir}/output/build/host-uboot-tools-* > /dev/null 2>&1 || true
find ${current_dir}/output/build -maxdepth 1 -type f -exec rm -f {} + 2>/dev/null || true
rm -rf ${current_dir}/output/target > /dev/null 2>&1 || true
rm -rf ${current_dir}/output/images > /dev/null 2>&1 || true


echo "Clean buildroot output directory"
/usr/bin/make -C ${current_dir}/buildroot clean
 
echo "Configure buildroot for ThirdReality HubV3"
/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output BR2_EXTERNAL=${current_dir}/buildroot-external "thirdreality_hubv3_defconfig"

echo "Build ThirdReality HubV3"
/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output BR2_EXTERNAL=${current_dir}/buildroot-external

