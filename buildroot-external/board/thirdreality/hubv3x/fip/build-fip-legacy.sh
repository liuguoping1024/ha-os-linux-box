#!/bin/bash
# Build legacy FIP bootloader for HubV3X
#
# This script compiles U-Boot v2015.01 (bl33) from the Amlogic SDK source,
# copies proprietary Amlogic blobs (bl2/bl30/bl31) locally, and packages
# the complete FIP bootloader using SDK tools.
#
# Amlogic proprietary binaries (bl2, bl30, bl31, aml_encrypt_axg, etc.)
# MUST NOT be committed to git per Amlogic SDK license terms.
#
# Prerequisites:
#   - aarch64-linux-gnu-gcc cross compiler
#   - arm-none-eabi-gcc cross compiler (for bl301/bl21 firmware)
#   - python3
#   - Amlogic SDK at SDK_PATH
#
# SDK patches needed before first build (already applied if you followed the guide):
#   1. bl33/v2015/Makefile: "-Werror" → "-Wno-error" (GCC 12+ compat)
#   2. fip/acs_tool.py: Python3 port of acs_tool.pyc
#   3. fip/axg/build.sh: "python acs_tool.pyc" → "python3 acs_tool.py"
#   4. bl33/v2015/.../axg/firmware/acs/Makefile: LDFLAGS add --no-warn-rwx-segments
#   5. bl33/v2015/.../axg/firmware/bl21/Makefile: LDFLAGS add --no-warn-rwx-segments
#
# Usage:
#   ./build-fip-legacy.sh [BOARD_CONFIG]
#   Default BOARD_CONFIG: axg_s420_v1
#
# Environment:
#   SDK_PATH  - Path to Amlogic SDK (default: /root/linuxbox/sdk_A113X_202210)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_PATH="${SDK_PATH:-/root/linuxbox/sdk_A113X_202210}"
BOARD_CONFIG="${1:-axg_s420_v1}"
SOC="axg"

UBOOT_REPO="${SDK_PATH}/bootloader/uboot-repo"
BL33_DIR="${UBOOT_REPO}/bl33/v2015"

# Local staging directories (all .gitignored)
BLOBS_DIR="${SCRIPT_DIR}/blobs"
TOOLS_DIR="${SCRIPT_DIR}/tools"
BUILD_DIR="${SCRIPT_DIR}/build"

export CROSS_COMPILE=aarch64-linux-gnu-
export CROSS_COMPILE_T32=arm-none-eabi-

# ============================================================
# Helper: fix_blx - pad and concatenate bl2/bl30 components
# Ported from SDK fip/axg/build.sh
# ============================================================
fix_blx() {
    local blx_bin=$1
    local zero_tmp=$2
    local blx_zero=$3
    local blx01_bin=$4
    local blx01_zero=$5
    local output=$6
    local name_flag=$7

    local blx_bin_limit=0
    local blx01_bin_limit=0

    if [ "$name_flag" = "bl30" ]; then
        blx_bin_limit=40960
        blx01_bin_limit=13312
    elif [ "$name_flag" = "bl2" ]; then
        blx_bin_limit=41984
        blx01_bin_limit=7168
    else
        echo "Error: fix_blx unknown name flag: $name_flag"
        exit 1
    fi

    local blx_size
    blx_size=$(stat -c '%s' "$blx_bin")
    if [ "$blx_size" -gt "$blx_bin_limit" ]; then
        echo "Error: $name_flag ($blx_bin) too big: $blx_size > $blx_bin_limit"
        exit 1
    fi

    local zero_size=$((blx_bin_limit - blx_size))
    dd if=/dev/zero of="$zero_tmp" bs=1 count=$zero_size 2>/dev/null
    cat "$blx_bin" "$zero_tmp" > "$blx_zero"
    rm -f "$zero_tmp"

    blx_size=$(stat -c '%s' "$blx01_bin")
    zero_size=$((blx01_bin_limit - blx_size))
    dd if=/dev/zero of="$zero_tmp" bs=1 count=$zero_size 2>/dev/null
    cat "$blx01_bin" "$zero_tmp" > "$blx01_zero"

    cat "$blx_zero" "$blx01_zero" > "$output"
    rm -f "$zero_tmp"
}

# ============================================================
# Cleanup: restore system headers if moved
# ============================================================
HEADERS_MOVED=0
cleanup() {
    if [ $HEADERS_MOVED -eq 1 ]; then
        mv /usr/include/libfdt.h.bak /usr/include/libfdt.h 2>/dev/null || true
        mv /usr/include/libfdt_env.h.bak /usr/include/libfdt_env.h 2>/dev/null || true
        mv /usr/include/fdt.h.bak /usr/include/fdt.h 2>/dev/null || true
        echo "System libfdt headers restored"
    fi
}
trap cleanup EXIT

# ============================================================
# Validation
# ============================================================
if [ ! -d "${UBOOT_REPO}" ]; then
    echo "Error: Amlogic SDK not found at ${SDK_PATH}"
    echo "Set SDK_PATH environment variable to point to your SDK"
    exit 1
fi

echo "========================================"
echo "  HubV3X Legacy FIP Builder"
echo "  SDK:    ${SDK_PATH}"
echo "  Board:  ${BOARD_CONFIG}"
echo "  SOC:    ${SOC}"
echo "  Output: ${SCRIPT_DIR}"
echo "========================================"

mkdir -p "${BLOBS_DIR}" "${TOOLS_DIR}" "${BUILD_DIR}"

# ============================================================
# Stage 1: Copy Amlogic proprietary blobs from SDK
# ============================================================
echo ""
echo "=== Stage 1: Copy Amlogic proprietary blobs ==="

copy_blob() {
    local src=$1
    local dst=$2
    if [ ! -f "$src" ]; then
        echo "Error: blob not found: $src"
        exit 1
    fi
    cp -f "$src" "$dst"
    echo "  $(basename "$dst") ($(stat -c '%s' "$dst") bytes)"
}

copy_blob "${UBOOT_REPO}/bl2/bin/${SOC}/bl2.bin"      "${BLOBS_DIR}/bl2.bin"
copy_blob "${UBOOT_REPO}/bl30/bin/${SOC}/bl30.bin"     "${BLOBS_DIR}/bl30.bin"
copy_blob "${UBOOT_REPO}/bl31_1.3/bin/${SOC}/bl31.img" "${BLOBS_DIR}/bl31.img"

# ============================================================
# Stage 2: Copy FIP tools from SDK
# ============================================================
echo ""
echo "=== Stage 2: Copy FIP packaging tools ==="

copy_blob "${UBOOT_REPO}/fip/${SOC}/aml_encrypt_${SOC}" "${TOOLS_DIR}/aml_encrypt_${SOC}"
chmod +x "${TOOLS_DIR}/aml_encrypt_${SOC}"
copy_blob "${UBOOT_REPO}/fip/fip_create"                "${TOOLS_DIR}/fip_create"
chmod +x "${TOOLS_DIR}/fip_create"
copy_blob "${UBOOT_REPO}/fip/acs_tool.py"               "${TOOLS_DIR}/acs_tool.py"

# ============================================================
# Stage 3: Compile bl33 (U-Boot v2015.01)
# ============================================================
echo ""
echo "=== Stage 3: Compile bl33 (U-Boot v2015.01) ==="

# Temporarily move system libfdt headers to avoid conflicts with U-Boot's bundled copy
if [ -f /usr/include/libfdt.h ]; then
    mv /usr/include/libfdt.h /usr/include/libfdt.h.bak 2>/dev/null || true
    mv /usr/include/libfdt_env.h /usr/include/libfdt_env.h.bak 2>/dev/null || true
    mv /usr/include/fdt.h /usr/include/fdt.h.bak 2>/dev/null || true
    HEADERS_MOVED=1
fi

cd "${BL33_DIR}"
make distclean 2>/dev/null || true
echo "Configuring ${BOARD_CONFIG}..."
make "${BOARD_CONFIG}_config"
echo "Building U-Boot..."
make -j"$(nproc)"

# Collect build artifacts
echo "Collecting build artifacts..."
cp -f "${BL33_DIR}/build/u-boot.bin"                                      "${BUILD_DIR}/bl33.bin"
cp -f "${BL33_DIR}/build/scp_task/bl301.bin"                              "${BUILD_DIR}/bl301.bin"
cp -f "${BL33_DIR}/build/board/amlogic/${BOARD_CONFIG}/firmware/bl21.bin"  "${BUILD_DIR}/bl21.bin"

echo "  bl33.bin  ($(stat -c '%s' "${BUILD_DIR}/bl33.bin") bytes)"
echo "  bl301.bin ($(stat -c '%s' "${BUILD_DIR}/bl301.bin") bytes)"
echo "  bl21.bin  ($(stat -c '%s' "${BUILD_DIR}/bl21.bin") bytes)"

cd "${SCRIPT_DIR}"

# ============================================================
# Stage 4: Package FIP
# ============================================================
echo ""
echo "=== Stage 4: Package FIP ==="

# Step 4a: Fix bl30 + bl301 → bl30_new.bin
echo "  Fixing bl30 + bl301..."
fix_blx \
    "${BLOBS_DIR}/bl30.bin" \
    "${BUILD_DIR}/zero_tmp" \
    "${BUILD_DIR}/bl30_zero.bin" \
    "${BUILD_DIR}/bl301.bin" \
    "${BUILD_DIR}/bl301_zero.bin" \
    "${BUILD_DIR}/bl30_new.bin" \
    bl30

# Step 4b: Extract ACS DDR parameters from bl2
echo "  Extracting ACS DDR parameters..."
cp -f "${BLOBS_DIR}/bl2.bin" "${BUILD_DIR}/bl2.bin"
python3 "${TOOLS_DIR}/acs_tool.py" \
    "${BUILD_DIR}/bl2.bin" \
    "${BUILD_DIR}/bl2_acs.bin" \
    "${BUILD_DIR}/acs.bin" 0

# Step 4c: Fix bl2_acs + bl21 → bl2_new.bin
echo "  Fixing bl2 + bl21..."
fix_blx \
    "${BUILD_DIR}/bl2_acs.bin" \
    "${BUILD_DIR}/zero_tmp" \
    "${BUILD_DIR}/bl2_zero.bin" \
    "${BUILD_DIR}/bl21.bin" \
    "${BUILD_DIR}/bl21_zero.bin" \
    "${BUILD_DIR}/bl2_new.bin" \
    bl2

# Step 4d: Create FIP image
echo "  Creating FIP image..."
cp -f "${BLOBS_DIR}/bl31.img" "${BUILD_DIR}/bl31.img"
"${TOOLS_DIR}/fip_create" \
    --bl30 "${BUILD_DIR}/bl30_new.bin" \
    --bl31 "${BUILD_DIR}/bl31.img" \
    --bl33 "${BUILD_DIR}/bl33.bin" \
    "${BUILD_DIR}/fip.bin"

# Step 4e: Combine bl2 + fip → boot_new.bin
cat "${BUILD_DIR}/bl2_new.bin" "${BUILD_DIR}/fip.bin" > "${BUILD_DIR}/boot_new.bin"

# Step 4f: Encrypt and sign
echo "  Encrypting bl30/bl31/bl33..."
"${TOOLS_DIR}/aml_encrypt_${SOC}" --bl3enc \
    --input "${BUILD_DIR}/bl30_new.bin" \
    --output "${BUILD_DIR}/bl30_new.bin.enc"

"${TOOLS_DIR}/aml_encrypt_${SOC}" --bl3enc \
    --input "${BUILD_DIR}/bl31.img" \
    --output "${BUILD_DIR}/bl31.img.enc"

"${TOOLS_DIR}/aml_encrypt_${SOC}" --bl3enc \
    --input "${BUILD_DIR}/bl33.bin" \
    --output "${BUILD_DIR}/bl33.bin.enc"

echo "  Signing bl2..."
"${TOOLS_DIR}/aml_encrypt_${SOC}" --bl2sig \
    --input "${BUILD_DIR}/bl2_new.bin" \
    --output "${BUILD_DIR}/bl2.n.bin.sig"

echo "  Creating final u-boot.bin..."
"${TOOLS_DIR}/aml_encrypt_${SOC}" --bootmk \
    --output "${BUILD_DIR}/u-boot.bin" \
    --bl2 "${BUILD_DIR}/bl2.n.bin.sig" \
    --bl30 "${BUILD_DIR}/bl30_new.bin.enc" \
    --bl31 "${BUILD_DIR}/bl31.img.enc" \
    --bl33 "${BUILD_DIR}/bl33.bin.enc"

# ============================================================
# Stage 5: Copy final outputs
# ============================================================
echo ""
echo "=== Stage 5: Copy outputs ==="

for f in u-boot.bin u-boot.bin.sd.bin u-boot.bin.usb.bl2 u-boot.bin.usb.tpl; do
    if [ -f "${BUILD_DIR}/${f}" ]; then
        cp -f "${BUILD_DIR}/${f}" "${SCRIPT_DIR}/${f}"
        echo "  ${f} ($(stat -c '%s' "${SCRIPT_DIR}/${f}") bytes)"
    else
        echo "  WARNING: ${f} not found in build output"
    fi
done

echo ""
echo "=== FIP build complete ==="
echo "Output directory: ${SCRIPT_DIR}"
ls -la "${SCRIPT_DIR}"/u-boot.* 2>/dev/null || echo "  (no u-boot binaries found)"
