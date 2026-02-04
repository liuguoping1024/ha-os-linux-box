#!/bin/bash
# shellcheck disable=SC1090,SC1091
set -e

SCRIPT_DIR=${BR2_EXTERNAL_HASSOS_PATH}/scripts
BOARD_DIR=${2}
HOOK_FILE=${3}

. "${BR2_EXTERNAL_HASSOS_PATH}/meta"
. "${BOARD_DIR}/meta"

. "${SCRIPT_DIR}/hdd-image.sh"
. "${SCRIPT_DIR}/rootfs-layer.sh"
. "${SCRIPT_DIR}/name.sh"
. "${SCRIPT_DIR}/rauc.sh"
. "${HOOK_FILE}"

# Cleanup
rm -rf "$(path_boot_dir)"
mkdir -p "$(path_boot_dir)"

# Hook pre image build stuff
hassos_pre_image

# Create empty data partition if it doesn't exist (when HASSIO is disabled)
if [ ! -f "$(path_data_img)" ]; then
    echo "Creating empty data.ext4 partition (HASSIO disabled)..."
    data_img="$(path_data_img)"
    rm -f "${data_img}"
    truncate --size="6000M" "${data_img}"
    mkfs.ext4 -L "hassos-data" -E lazy_itable_init=0,lazy_journal_init=0 "${data_img}"
    e2fsck -f -p "${data_img}"
    resize2fs "${data_img}"
fi

# Disk & OTA
create_disk_image

# Hook post image build stuff
hassos_post_image
