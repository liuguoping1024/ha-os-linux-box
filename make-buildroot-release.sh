#!/bin/bash
set -e

current_dir=$(pwd)

# --- Parse arguments ---
BOARD="hubv3"
DO_CLEAN=false

usage() {
    echo "Usage: $0 [-b hubv3|hubv3a|hubv3b] [clean]"
    echo ""
    echo "Options:"
    echo "  -b BOARD   Board variant (default: hubv3)"
    echo "             hubv3  - base model, no zigbee2mqtt"
    echo "             hubv3b - same hardware as hubv3, with zigbee2mqtt"
    echo "             hubv3a - cost-reduced variant, with zigbee2mqtt"
    echo "  clean      Remove output directory before building"
    echo ""
    echo "Examples:"
    echo "  $0                    # build hubv3"
    echo "  $0 -b hubv3b         # build hubv3b"
    echo "  $0 -b hubv3a clean   # clean + build hubv3a"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -b)
            BOARD="$2"
            shift 2
            ;;
        clean)
            DO_CLEAN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            ;;
    esac
done

case "${BOARD}" in
    hubv3)  DEFCONFIG="thirdreality_hubv3_defconfig"  ;;
    hubv3a) DEFCONFIG="thirdreality_hubv3a_defconfig" ;;
    hubv3b) DEFCONFIG="thirdreality_hubv3b_defconfig" ;;
    *)
        echo "Error: unknown board '${BOARD}', must be hubv3|hubv3a|hubv3b"
        exit 1
        ;;
esac

NEEDS_NODEJS=false
case "${BOARD}" in
    hubv3a|hubv3b) NEEDS_NODEJS=true ;;
esac

echo "========================================"
echo "  Board:    ${BOARD}"
echo "  Defconfig: ${DEFCONFIG}"
echo "  Node.js:  ${NEEDS_NODEJS}"
echo "  Clean:    ${DO_CLEAN}"
echo "  Work dir: ${current_dir}"
echo "========================================"

# --- Buildroot submodule initialization ---
subdir_count=0
if [ -d "${current_dir}/buildroot" ]; then
    subdir_count=$(find ${current_dir}/buildroot -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
fi

if [ ! -d "${current_dir}/buildroot" ] || [ "$subdir_count" -lt 2 ]; then
    mkdir -p ${current_dir}/buildroot
    echo "Buildroot directory missing or incomplete (subdirs: $subdir_count), initializing..."
    /usr/bin/git pull && /usr/bin/git submodule update --init --recursive
    /usr/bin/git submodule sync
    echo "Buildroot initialization completed!"
else
    echo "Buildroot directory exists and is complete (subdirs: $subdir_count), skipping sync"
fi

# --- Apply Node.js patches (only when building boards that need it) ---
NODEJS_MK="${current_dir}/buildroot/package/nodejs/nodejs.mk"
NODEJS_HASH="${current_dir}/buildroot/package/nodejs/nodejs-src/nodejs-src.hash"
NODEJS_SRC_MK="${current_dir}/buildroot/package/nodejs/nodejs-src/nodejs-src.mk"

if [ "${NEEDS_NODEJS}" = true ]; then
    echo ""
    echo "--- Applying Node.js patches for ${BOARD} ---"

    # Patch 1: Upgrade Node.js to 22.13.1 (required by zigbee-on-host: ^20.19.0 || >=22.12.0)
    if ! grep -q "NODEJS_COMMON_VERSION = 22.13.1" "${NODEJS_MK}" 2>/dev/null; then
        echo "Patch 1: Upgrading Node.js -> 22.13.1"
        sed -i 's/NODEJS_COMMON_VERSION = .*/NODEJS_COMMON_VERSION = 22.13.1/' "${NODEJS_MK}"
        cat > "${NODEJS_HASH}" << 'HASHEOF'
# From https://nodejs.org/dist/v22.13.1/SHASUMS256.txt.asc
sha256  2722236564df6d33b1d953f23e21bf5247b62b38ea9000b47c655ee3a9a440e7  node-v22.13.1-headers.tar.xz
sha256  0a237c413ccbab920640438bf6e1a32edb19845bdc21f0e1cd5b91545ce1c126  node-v22.13.1-linux-arm64.tar.xz
sha256  f2be8dca2a7a518f6d187aa4b18abbeeafd71096a6d95f73f4d8bc0f8d2394ea  node-v22.13.1-linux-armv7l.tar.xz
sha256  377a7a1ea66f39251e1657f419e9404d526fcca9910620d0ecf0a870c6308f6b  node-v22.13.1-linux-ppc64le.tar.xz
sha256  0d2a5af33c7deab5555c8309cd3f373446fe1526c1b95833935ab3f019733b3b  node-v22.13.1-linux-x64.tar.xz
sha256  cfce282119390f7e0c2220410924428e90dadcb2df1744c0c4a0e7baae387cc2  node-v22.13.1.tar.xz

# Locally calculated
sha256  9d72cce9b104ecb67feb8af38618511685190ae5a119cc0488ecae66b221000d  LICENSE
HASHEOF
        echo "Patch 1 applied"
    else
        echo "Patch 1: Node.js 22.13.1 already applied, skipping"
    fi

    # Patch 2: Use bundled c-ares (buildroot c-ares 1.27.0 lacks ares_query_dnsrec)
    if grep -q "\-\-shared-cares" "${NODEJS_SRC_MK}" 2>/dev/null; then
        echo "Patch 2: Removing --shared-cares (use bundled c-ares)"
        sed -i '/--shared-cares \\/d' "${NODEJS_SRC_MK}"
        sed -i '/\bc-ares\b/d' "${NODEJS_SRC_MK}"
        echo "Patch 2 applied"
    else
        echo "Patch 2: --shared-cares already removed, skipping"
    fi

    # Patch 3: Use bundled libuv (buildroot libuv 1.48.0 lacks UV_TCP_REUSEPORT)
    if grep -q "\-\-shared-libuv" "${NODEJS_SRC_MK}" 2>/dev/null; then
        echo "Patch 3: Removing --shared-libuv (use bundled libuv 1.49.x)"
        sed -i '/--shared-libuv \\/d' "${NODEJS_SRC_MK}"
        sed -i '/\blibuv\b/d' "${NODEJS_SRC_MK}"
        echo "Patch 3 applied"
    else
        echo "Patch 3: --shared-libuv already removed, skipping"
    fi
else
    echo ""
    echo "--- Board ${BOARD} does not need Node.js, skipping patches ---"
fi

# --- Prepare directories ---
mkdir -p /cache
mkdir -p /build

# --- Clean ---
if [ "${DO_CLEAN}" = true ]; then
    echo ""
    echo "--- Cleaning output directory ---"
    rm -rf "${current_dir}/output"
    echo "Output directory removed"
else
    echo ""
    echo "--- Incremental build: cleaning target packages only ---"
    find ${current_dir}/output/build -maxdepth 1 -type d ! -name "host-*" ! -name "build" -exec rm -rf {} + 2>/dev/null || true
    rm -rf ${current_dir}/output/build/host-uboot-tools-* > /dev/null 2>&1 || true
    find ${current_dir}/output/build -maxdepth 1 -type f -exec rm -f {} + 2>/dev/null || true
    rm -rf ${current_dir}/output/target > /dev/null 2>&1 || true
    rm -rf ${current_dir}/output/images > /dev/null 2>&1 || true
fi

# --- Configure ---
echo ""
echo "Configure buildroot for ${BOARD} (${DEFCONFIG})"
/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output \
    BR2_EXTERNAL=${current_dir}/buildroot-external "${DEFCONFIG}"

# --- Build ---
echo ""
echo "Build ${BOARD}"
/usr/bin/make -C ${current_dir}/buildroot O=${current_dir}/output \
    BR2_EXTERNAL=${current_dir}/buildroot-external
