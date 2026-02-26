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
    mkdir -p ${current_dir}/buildroot
    echo "Buildroot directory missing or incomplete (subdirs: $subdir_count), initializing..."
    /usr/bin/git pull && /usr/bin/git submodule update --init --recursive
    /usr/bin/git submodule sync
    echo "Buildroot initialization completed!"
else
    echo "Buildroot directory exists and is complete (subdirs: $subdir_count), skipping sync"
fi

# Apply patches to buildroot source files
NODEJS_MK="${current_dir}/buildroot/package/nodejs/nodejs.mk"
NODEJS_HASH="${current_dir}/buildroot/package/nodejs/nodejs-src/nodejs-src.hash"
NODEJS_SRC_MK="${current_dir}/buildroot/package/nodejs/nodejs-src/nodejs-src.mk"

# Patch 1: Upgrade Node.js to 22.13.1 (required by zigbee-on-host: ^20.19.0 || >=22.12.0)
if ! grep -q "NODEJS_COMMON_VERSION = 22.13.1" "${NODEJS_MK}" 2>/dev/null; then
    echo "Patching Node.js version -> 22.13.1"
    sed -i 's/NODEJS_COMMON_VERSION = .*/NODEJS_COMMON_VERSION = 22.13.1/' "${NODEJS_MK}"
    cat > "${NODEJS_HASH}" << 'EOF'
# From https://nodejs.org/dist/v22.13.1/SHASUMS256.txt.asc
sha256  2722236564df6d33b1d953f23e21bf5247b62b38ea9000b47c655ee3a9a440e7  node-v22.13.1-headers.tar.xz
sha256  0a237c413ccbab920640438bf6e1a32edb19845bdc21f0e1cd5b91545ce1c126  node-v22.13.1-linux-arm64.tar.xz
sha256  f2be8dca2a7a518f6d187aa4b18abbeeafd71096a6d95f73f4d8bc0f8d2394ea  node-v22.13.1-linux-armv7l.tar.xz
sha256  377a7a1ea66f39251e1657f419e9404d526fcca9910620d0ecf0a870c6308f6b  node-v22.13.1-linux-ppc64le.tar.xz
sha256  0d2a5af33c7deab5555c8309cd3f373446fe1526c1b95833935ab3f019733b3b  node-v22.13.1-linux-x64.tar.xz
sha256  cfce282119390f7e0c2220410924428e90dadcb2df1744c0c4a0e7baae387cc2  node-v22.13.1.tar.xz

# Locally calculated
sha256  9d72cce9b104ecb67feb8af38618511685190ae5a119cc0488ecae66b221000d  LICENSE
EOF
    echo "Patch 1 applied: Node.js -> 22.13.1"
else
    echo "Patch 1: Node.js 22.13.1 already applied, skipping"
fi

# Patch 2: Use bundled c-ares instead of shared system c-ares
# Node.js 22.x requires ares_query_dnsrec which is not in buildroot's c-ares 1.27.0
if grep -q "\-\-shared-cares" "${NODEJS_SRC_MK}" 2>/dev/null; then
    echo "Patch 2: Removing --shared-cares (use bundled c-ares)"
    sed -i '/--shared-cares \\/d' "${NODEJS_SRC_MK}"
    sed -i '/\bc-ares\b/d' "${NODEJS_SRC_MK}"
    echo "Patch 2 applied: bundled c-ares enabled"
else
    echo "Patch 2: --shared-cares already removed, skipping"
fi

# Patch 3: Use bundled libuv instead of shared system libuv
# Node.js 22.x requires libuv 1.49+ (UV_TCP_REUSEPORT / UV_UDP_REUSEPORT),
# but buildroot only ships libuv 1.48.0 which lacks these constants
if grep -q "\-\-shared-libuv" "${NODEJS_SRC_MK}" 2>/dev/null; then
    echo "Patch 3: Removing --shared-libuv (use bundled libuv 1.49.x)"
    sed -i '/--shared-libuv \\/d' "${NODEJS_SRC_MK}"
    sed -i '/\blibuv\b/d' "${NODEJS_SRC_MK}"
    echo "Patch 3 applied: bundled libuv enabled"
else
    echo "Patch 3: --shared-libuv already removed, skipping"
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

