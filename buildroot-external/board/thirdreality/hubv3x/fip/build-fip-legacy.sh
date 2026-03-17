#!/bin/bash
# Build legacy FIP bootloader for HubV3X using Amlogic SDK (U-Boot 2015.01)
#
# Prerequisites:
#   - aarch64-linux-gnu-gcc cross compiler
#   - arm-none-eabi-gcc cross compiler
#   - python3
#   - Amlogic SDK at SDK_PATH (default: /root/linuxbox/sdk_A113X_202210)
#
# Modifications needed in SDK before first build:
#   1. bl33/v2015/Makefile: replace "-Werror" with "-Wno-error" (GCC 12+ compat)
#   2. fip/acs_tool.py: Python3 port of acs_tool.pyc (Python 2.7)
#   3. fip/axg/build.sh: change "python acs_tool.pyc" to "python3 acs_tool.py"
#
# Usage:
#   ./build-fip-legacy.sh [BOARD_CONFIG]
#   Default BOARD_CONFIG: axg_s420_v1

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_PATH="${SDK_PATH:-/root/linuxbox/sdk_A113X_202210}"
BOARD_CONFIG="${1:-axg_s420_v1}"
UBOOT_REPO="${SDK_PATH}/bootloader/uboot-repo"

if [ ! -d "${UBOOT_REPO}" ]; then
    echo "Error: SDK not found at ${SDK_PATH}"
    exit 1
fi

export CROSS_COMPILE=aarch64-linux-gnu-
export CROSS_COMPILE_T32=arm-none-eabi-

HEADERS_MOVED=0
cleanup() {
    if [ $HEADERS_MOVED -eq 1 ]; then
        mv /usr/include/libfdt.h.bak /usr/include/libfdt.h 2>/dev/null || true
        mv /usr/include/libfdt_env.h.bak /usr/include/libfdt_env.h 2>/dev/null || true
        mv /usr/include/fdt.h.bak /usr/include/fdt.h 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "=== Building FIP for ${BOARD_CONFIG} ==="

cd "${UBOOT_REPO}"
cd bl33/v2015 && make distclean 2>/dev/null || true
cd ../..
rm -rf fip/_tmp

# Temporarily move system libfdt headers to avoid conflicts
mv /usr/include/libfdt.h /usr/include/libfdt.h.bak 2>/dev/null || true
mv /usr/include/libfdt_env.h /usr/include/libfdt_env.h.bak 2>/dev/null || true
mv /usr/include/fdt.h /usr/include/fdt.h.bak 2>/dev/null || true
HEADERS_MOVED=1

./mk "${BOARD_CONFIG}"

echo "=== Copying outputs to ${SCRIPT_DIR} ==="
cp fip/_tmp/u-boot.bin.sd.bin "${SCRIPT_DIR}/"
cp fip/_tmp/u-boot.bin "${SCRIPT_DIR}/"
cp fip/_tmp/u-boot.bin.usb.bl2 "${SCRIPT_DIR}/"
cp fip/_tmp/u-boot.bin.usb.tpl "${SCRIPT_DIR}/"

echo "=== FIP build complete ==="
ls -la "${SCRIPT_DIR}"/u-boot.*
