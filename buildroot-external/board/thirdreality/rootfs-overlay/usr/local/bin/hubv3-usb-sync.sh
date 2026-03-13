#!/bin/bash

# maintainer: guoping.liu@thirdreality.com

LC_ALL=en_US.UTF-8

export LC_ALL

USB_MOUNT="/mnt/media/usb"
WORK_DIR="$USB_MOUNT/R3Install"
DEBUG_DIR="$USB_MOUNT/R3Debug"
BACKUP_DIR="$USB_MOUNT/R3Backup"

DEBUG_ZHA_DIR="$DEBUG_DIR/zha_quirks"
DEBUG_Z2M_DIR="$DEBUG_DIR/z2m_converters"
DEBUG_OTA_DIR="$DEBUG_DIR/zigpy_local_ota"
DEBUG_FIRMWARE_DIR="$DEBUG_DIR/firmware"

CONFIG_DIR="/var/lib/homeassistant"

set -e

# Ensure lock file is removed when script exits,
# and perform additional error handling

on_exit() {
    local exit_code=$?

    echo "Running cleanup tasks..."
    if [ -e "/usr/local/bin/supervisor" ]; then
        /usr/local/bin/supervisor led sys_event_off || true
    fi

    if [ "$exit_code" -ne 0 ]; then
        echo "An error occurred during the execution of the script. Exit code $exit_code"
    fi
}

error_handler() {
    local lineno=$1
    echo "Error occurred at line $lineno"
}

# trap 'error_handler $LINENO' ERR
trap "on_exit" EXIT

while getopts "d:" opt; do
  case ${opt} in
    d )
      WORK_DIR=$OPTARG
      ;;
    \? )
      echo "Usage: cmd [-d directory]"
      exit 1
      ;;
  esac
done

echo "Using directory: ${WORK_DIR}"

update_z2m_quirks_for_debug()
{
    if [ ! -d "$DEBUG_Z2M_DIR" ]; then
        echo 0 >&2
        echo 0
        return 0
    fi

    # Check js file count
    local js_files_count=$(find "$DEBUG_Z2M_DIR" -maxdepth 1 -name "*.js" -type f | wc -l)

    # If js file count is 0, do nothing
    if [ "$js_files_count" -eq 0 ]; then
        echo 0 >&2
        echo 0
        return 0
    fi

    local target_dir="/opt/zigbee2mqtt/data/external_converters"
    
    # Check if Z2M data directory exists
    local z2m_data_dir="/opt/zigbee2mqtt/data"
    if [ ! -d "$z2m_data_dir" ]; then
        echo "[DEBUG-Z2M] Zigbee2MQTT data directory not found: $z2m_data_dir" >&2
        echo 0 >&2
        echo 0
        return 0
    fi
    
    echo "[DEBUG-Z2M] Found $js_files_count *.js files in $DEBUG_Z2M_DIR" >&2
    echo "[DEBUG-Z2M] Copying *.js files to: $target_dir" >&2
    
    # Create target directory if it doesn't exist
    mkdir -p "$target_dir"
    
    # Copy all js files to target directory
    find "$DEBUG_Z2M_DIR" -maxdepth 1 -name "*.js" -type f -exec cp {} "$target_dir"/ \;

    echo "[DEBUG-Z2M] z2m converters sync completed, total js files: $js_files_count" >&2
    
    # Return total js file count
    echo "$js_files_count"
    return 0
}

update_zha_quirks_for_debug()
{
    # If $DEBUG_ZHA_DIR exists, copy all *.py files under it to
    # /var/lib/homeassistant/homeassistant/zha_quirks.
    # Proceed only if the target directory exists.
    if [ ! -d "$DEBUG_ZHA_DIR" ]; then
        echo 0 >&2
        echo 0
        return 0
    fi

    # Check how many *.py files are in $DEBUG_ZHA_DIR directory
    local py_files_count=$(find "$DEBUG_ZHA_DIR" -maxdepth 1 -name "*.py" -type f | wc -l)
    
    if [ "$py_files_count" -eq 0 ]; then
        #echo "[DEBUG-ZHA] No *.py files found in $DEBUG_ZHA_DIR, skipping"
        echo 0 >&2
        echo 0
        return 0
    fi

    echo "[DEBUG-ZHA] Found $py_files_count *.py files in $DEBUG_ZHA_DIR" >&2

    # Set the target directory to the new path
    local zha_target_dir="/var/lib/homeassistant/homeassistant/zha_quirks"
    
    # Create target directory if it doesn't exist
    mkdir -p "$zha_target_dir"

    echo "[DEBUG-ZHA] Copying *.py files to: $zha_target_dir" >&2
    # Copy all *.py files to target directory
    find "$DEBUG_ZHA_DIR" -maxdepth 1 -name "*.py" -type f -exec cp {} "$zha_target_dir"/  \;

    # Update Home Assistant configuration
    local ha_cfg="/var/lib/homeassistant/homeassistant/configuration.yaml"
    if [ ! -f "$ha_cfg" ]; then
        echo "[DEBUG-ZHA] Home Assistant configuration file not found: $ha_cfg" >&2
        echo "$py_files_count"
        return 0
    fi

    # Check if custom_quirks_path configuration already exists with the correct path
    if grep -qE "custom_quirks_path:" "$ha_cfg"; then
        # Check if the path is correct
        if grep -qE "custom_quirks_path:.*zha_quirks" "$ha_cfg"; then
            echo "[DEBUG-ZHA] ZHA configuration already exists with correct custom_quirks_path in $ha_cfg" >&2
        else
            # Path exists but is different, update it
            echo "[DEBUG-ZHA] ZHA configuration exists but with different custom_quirks_path, updating..." >&2
            # Create a backup
            cp "$ha_cfg" "$ha_cfg.backup.$(date +%Y%m%d_%H%M%S)" || true
            # Update the path using sed
            sed -i 's|custom_quirks_path:.*|custom_quirks_path: /var/lib/homeassistant/homeassistant/zha_quirks|g' "$ha_cfg"
            echo "[DEBUG-ZHA] Updated custom_quirks_path to correct value" >&2
        fi
    else
        # Need to add custom_quirks_path configuration
        echo "[DEBUG-ZHA] Adding ZHA quirks configuration to $ha_cfg" >&2
        
        # Check if zha: section already exists
        if grep -qE "^[[:space:]]*zha:" "$ha_cfg"; then
            # zha: section exists, append quirks config under it
            # Create a backup
            cp "$ha_cfg" "$ha_cfg.backup.$(date +%Y%m%d_%H%M%S)" || true
            
            # Find the line number of zha: and insert quirks config after it
            # Use awk to add the configuration with proper indentation
            awk '/^[[:space:]]*zha:/ && !done { print; print "  enable_quirks: true"; print "  custom_quirks_path: /var/lib/homeassistant/homeassistant/zha_quirks"; done=1; next } 1' "$ha_cfg" > "$ha_cfg.tmp" && mv "$ha_cfg.tmp" "$ha_cfg"
            echo "[DEBUG-ZHA] Added quirks configuration to existing zha: section" >&2
        else
            # zha: section doesn't exist, create new one
            {
                echo ""
                echo "zha:"
                echo "  enable_quirks: true"
                echo "  custom_quirks_path: /var/lib/homeassistant/homeassistant/zha_quirks"
            } >> "$ha_cfg"
            echo "[DEBUG-ZHA] Created new zha: section with quirks configuration" >&2
        fi
    fi

    echo "[DEBUG-ZHA] zhaquirks sync completed" >&2
    
    # Output total *.py file count and return 0
    echo "$py_files_count"
    return 0
}

# Helper function: Update ZHA OTA configuration
update_zha_ota_config()
{
    local updated=0
    
    if [ ! -f "$DEBUG_OTA_DIR/local_index.json" ]; then
        echo "$updated"
        return 0
    fi

    echo "[DEBUG-OTA-ZHA] Found local_index.json in $DEBUG_OTA_DIR" >&2

    local ota_dir="/var/lib/homeassistant/homeassistant/zigpy_local_ota"
    mkdir -p "$ota_dir"
    
    # Copy local_index.json
    if install -m 0644 "$DEBUG_OTA_DIR/local_index.json" "$ota_dir/local_index.json"; then
        updated=1
        echo "[DEBUG-OTA-ZHA] Successfully copied local_index.json to $ota_dir" >&2
    else
        echo "[DEBUG-OTA-ZHA] Failed to copy local_index.json" >&2
    fi
    
    # Copy all *.ota files
    shopt -s nullglob
    local ota_files_count=0
    for f in "$DEBUG_OTA_DIR"/*.ota; do
        install -m 0644 "$f" "$ota_dir/"
        ota_files_count=$((ota_files_count + 1))
    done
    shopt -u nullglob

    if [ "$ota_files_count" -gt 0 ]; then
        echo "[DEBUG-OTA-ZHA] Copied $ota_files_count *.ota files to $ota_dir" >&2
    fi

    # Update Home Assistant configuration
    local ha_cfg="/var/lib/homeassistant/homeassistant/configuration.yaml"
    if [ ! -f "$ha_cfg" ]; then
        echo "[DEBUG-OTA-ZHA] Home Assistant configuration file not found: $ha_cfg" >&2
        echo "$updated"
        return 0
    fi

    # Check if OTA providers are already configured
    if grep -qE "extra_providers.*zigpy_local|index_file:.*zigpy_local_ota" "$ha_cfg"; then
        echo "[DEBUG-OTA-ZHA] ZHA OTA providers already configured in $ha_cfg" >&2
        echo "$updated"
        return 0
    fi

    echo "[DEBUG-OTA-ZHA] Adding local OTA providers for ZHA to $ha_cfg" >&2
    
    # Create a backup
    cp "$ha_cfg" "$ha_cfg.backup.$(date +%Y%m%d_%H%M%S)" || true
    
    # Check if zha: section already exists
    if grep -qE "^[[:space:]]*zha:" "$ha_cfg"; then
        # zha: section exists, append OTA config under it
        awk '
        /^[[:space:]]*zha:/ && !done {
            print
            print "  zigpy_config:"
            print "    ota:"
            print "      extra_providers:"
            print "        - type: zigpy_local"
            print "          index_file: '"$ota_dir"'/local_index.json"
            done=1
            next
        }
        { print }
        ' "$ha_cfg" > "$ha_cfg.tmp" && mv "$ha_cfg.tmp" "$ha_cfg"
        
        echo "[DEBUG-OTA-ZHA] Added OTA configuration to existing zha: section" >&2
    else
        # zha: section doesn't exist, create new one
        {
            echo ""
            echo "zha:"
            echo "  zigpy_config:"
            echo "    ota:"
            echo "      extra_providers:"
            echo "        - type: zigpy_local"
            echo "          index_file: $ota_dir/local_index.json"
        } >> "$ha_cfg"
        echo "[DEBUG-OTA-ZHA] Created new zha: section with OTA configuration" >&2
    fi

    echo "[DEBUG-OTA-ZHA] ZHA OTA configuration updated successfully" >&2
    echo "$updated"
    return 0
}

# Helper function: Update Z2M OTA configuration
update_z2m_ota_config()
{
    local updated=0
    
    if [ ! -f "$DEBUG_OTA_DIR/local_z2m_index.json" ]; then
        echo "$updated"
        return 0
    fi

    echo "[DEBUG-OTA-Z2M] Found local_z2m_index.json in $DEBUG_OTA_DIR" >&2

    local z2m_data_dir="/opt/zigbee2mqtt/data"
    local z2m_cfg="$z2m_data_dir/configuration.yaml"
    
    # Check if Z2M data directory exists
    if [ ! -d "$z2m_data_dir" ]; then
        echo "[DEBUG-OTA-Z2M] Zigbee2MQTT data directory not found: $z2m_data_dir" >&2
        echo "$updated"
        return 0
    fi
    
    # Copy local_z2m_index.json to Z2M data directory
    if [ -f "$DEBUG_OTA_DIR/local_z2m_index.json" ]; then
        cp "$DEBUG_OTA_DIR/local_z2m_index.json" "$z2m_data_dir/"
        echo "[DEBUG-OTA-Z2M] Copied local_z2m_index.json to $z2m_data_dir" >&2
        updated=1
    else
        echo "[DEBUG-OTA-Z2M] local_z2m_index.json not found in $DEBUG_OTA_DIR" >&2
        echo "$updated"
        return 0
    fi
    
    # Copy all *.ota files to Z2M data directory
    local ota_files_copied=0
    shopt -s nullglob
    for f in "$DEBUG_OTA_DIR"/*.ota; do
        if [ -f "$f" ]; then
            cp "$f" "$z2m_data_dir/"
            ota_files_copied=$((ota_files_copied + 1))
        fi
    done
    shopt -u nullglob
    
    if [ "$ota_files_copied" -gt 0 ]; then
        echo "[DEBUG-OTA-Z2M] Copied $ota_files_copied *.ota files to $z2m_data_dir" >&2
    fi
    
    # Update Z2M configuration.yaml if it exists
    if [ -f "$z2m_cfg" ]; then
        # Check if zigbee_ota_override_index_location is already configured
        if grep -qE "zigbee_ota_override_index_location:" "$z2m_cfg"; then
            echo "[DEBUG-OTA-Z2M] Z2M OTA override index already configured in $z2m_cfg" >&2
            echo "$updated"
            return 0
        fi
        
        echo "[DEBUG-OTA-Z2M] Adding OTA configuration to $z2m_cfg" >&2
        
        # Create a backup
        cp "$z2m_cfg" "$z2m_cfg.backup.$(date +%Y%m%d_%H%M%S)" || true
        
        # Check if ota: section exists
        if grep -qE "^[[:space:]]*ota:" "$z2m_cfg"; then
            # ota: section exists, add zigbee_ota_override_index_location under it
            awk '
            /^[[:space:]]*ota:/ && !done {
                print
                getline
                if ($0 !~ /zigbee_ota_override_index_location:/) {
                    print "  zigbee_ota_override_index_location: local_z2m_index.json"
                }
                print
                done=1
                next
            }
            { print }
            ' "$z2m_cfg" > "$z2m_cfg.tmp" && mv "$z2m_cfg.tmp" "$z2m_cfg"
            
            echo "[DEBUG-OTA-Z2M] Added OTA override index to existing ota: section" >&2
        else
            # ota: section doesn't exist, create new one
            {
                echo "ota:"
                echo "  zigbee_ota_override_index_location: local_z2m_index.json"
            } >> "$z2m_cfg"
            echo "[DEBUG-OTA-Z2M] Created new ota: section with override index configuration" >&2
        fi
    else
        echo "[DEBUG-OTA-Z2M] Z2M configuration.yaml not found: $z2m_cfg, skipping configuration update" >&2
    fi
    
    echo "[DEBUG-OTA-Z2M] Z2M OTA configuration updated successfully" >&2
    echo "$updated"
    return 0
}

# Main OTA update function
update_ota_for_debug()
{
    local total_updated=0
    
    if [ ! -d "$DEBUG_OTA_DIR" ]; then
        echo 0 >&2
        echo 0
        return 0
    fi
    # If there is no .ota file in DEBUG_OTA_DIR, nothing to do
    if ! ls "$DEBUG_OTA_DIR"/*.ota 1> /dev/null 2>&1; then
        echo 0 >&2
        echo 0
        return 0
    fi

    # Ensure local OTA index files exist; if both missing, try to generate them
    local zigpy_index="$DEBUG_OTA_DIR/local_index.json"
    local z2m_index="$DEBUG_OTA_DIR/local_z2m_index.json"
    local gen_script="/usr/local/bin/hubv3-generate-ota-indexes.sh"

    if [ ! -f "$zigpy_index" ] && [ ! -f "$z2m_index" ]; then
        if [ -x "$gen_script" ]; then
            echo "[DEBUG-OTA] Generating OTA indexes using $gen_script $DEBUG_OTA_DIR" >&2
            "$gen_script" "$DEBUG_OTA_DIR" || echo "[DEBUG-OTA] WARNING: OTA index generation script failed" >&2
        elif [ -f "$gen_script" ]; then
            echo "[DEBUG-OTA] Found $gen_script but not executable, trying with sh" >&2
            sh "$gen_script" "$DEBUG_OTA_DIR" || echo "[DEBUG-OTA] WARNING: OTA index generation via sh failed" >&2
        else
            echo "[DEBUG-OTA] OTA index generator not found: $gen_script" >&2
        fi
    fi

    # # Update ZHA OTA configuration
    # local zha_updated
    # zha_updated=$(update_zha_ota_config)
    # total_updated=$((total_updated + zha_updated))
    
    # # Update Z2M OTA configuration
    # local z2m_updated
    # z2m_updated=$(update_z2m_ota_config)
    # total_updated=$((total_updated + z2m_updated))
    
    # echo "$total_updated" >&2
    # echo "$total_updated"
    return 0
}

update_firmware_for_debug()
{
    if [ ! -d "$DEBUG_FIRMWARE_DIR" ]; then
        return 0
    fi

    echo "[DEBUG-FW] PATH at entry: $PATH" >&2

    local fw_dir="/usr/lib/firmware/bl706/partition_1m_images"
    local flasher_bin="/usr/lib/firmware/bl706/bl706_func.sh"
    local bl706_env_path="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"  # ensure python3 resolves to system interpreter

    # Handle Zigbee firmware
    if [ -f "$DEBUG_FIRMWARE_DIR/blz_whole_img.bin" ]; then
        echo "[DEBUG-FW] Update Zigbee firmware image"

        if [ -e "/usr/local/bin/supervisor" ]; then
            /usr/local/bin/supervisor led sys_firmware_updating  || true
        fi

        install -m 0644 "$DEBUG_FIRMWARE_DIR/blz_whole_img.bin" "$fw_dir/blz_whole_img.bin"

        local ha_running="no"
        local z2m_running="no"
        systemctl is-active --quiet home-assistant.service && ha_running="yes" || true
        systemctl is-active --quiet zigbee2mqtt.service && z2m_running="yes" || true

        if [ "$ha_running" = "yes" ]; then
            echo "[DEBUG-FW] Stopping Home Assistant service for Zigbee firmware update..." >&2
            systemctl stop home-assistant.service || true
        fi
        if [ "$z2m_running" = "yes" ]; then
            echo "[DEBUG-FW] Stopping Zigbee2MQTT service for Zigbee firmware update..." >&2
            systemctl stop zigbee2mqtt.service || true
        fi

        if [ -x "$flasher_bin" ]; then
            PATH="$bl706_env_path" "$flasher_bin" flash blz || true
        else
            echo "[DEBUG-FW][WARN] Flasher binary not found or not executable: $flasher_bin" >&2
        fi

        if [ -x "/usr/local/bin/supervisor" ]; then
            /usr/local/bin/supervisor zigbee info || true
        fi

        if [ "$ha_running" = "yes" ]; then
            echo "[DEBUG-FW] Starting Home Assistant service after Zigbee firmware update..." >&2
            systemctl start home-assistant.service || true
        fi
        if [ "$z2m_running" = "yes" ]; then
            echo "[DEBUG-FW] Starting Zigbee2MQTT service after Zigbee firmware update..." >&2
            systemctl start zigbee2mqtt.service || true
        fi
    fi

    # Handle Thread firmware
    if [ -f "$DEBUG_FIRMWARE_DIR/thread_whole_img.bin" ]; then
        echo "[DEBUG-FW] Update Thread firmware image"
        
        if [ -e "/usr/local/bin/supervisor" ]; then
            /usr/local/bin/supervisor led sys_firmware_updating  || true
        fi

        install -m 0644 "$DEBUG_FIRMWARE_DIR/thread_whole_img.bin" "$fw_dir/thread_whole_img.bin"

        local otbr_running="no"
        systemctl is-active --quiet otbr-agent.service && otbr_running="yes" || true

        if [ "$otbr_running" = "yes" ]; then
            echo "[DEBUG-FW] Stopping OTBR agent service for Thread firmware update..." >&2
            systemctl stop otbr-agent.service || true
        fi

        if [ -x "$flasher_bin" ]; then
            PATH="$bl706_env_path" "$flasher_bin" flash thread || true
        else
            echo "[DEBUG-FW][WARN] Flasher binary not found or not executable: $flasher_bin" >&2
        fi

        if [ -x "/usr/local/bin/supervisor" ]; then
            /usr/local/bin/supervisor thread info || true
        fi

        if [ "$otbr_running" = "yes" ]; then
            echo "[DEBUG-FW] Starting OTBR agent service after Thread firmware update..." >&2
            systemctl start otbr-agent.service || true
        fi
    fi
}


update_blueprints_for_debug()
{
    local bp_root="${DEBUG_DIR}/blueprints"
    local ha_bp_root="/var/lib/homeassistant/homeassistant/blueprints"

    if [ ! -d "$bp_root" ]; then
        return 0
    fi

    mkdir -p "$ha_bp_root"

    # Helper: copy a category (automation/script)
    copy_bp_category() {
        local category="$1"
        local src_dir="$bp_root/$category"
        local dst_dir="$ha_bp_root/$category"

        if [ ! -d "$src_dir" ]; then
            return 0
        fi

        # Count total files under src_dir; skip if empty
        local total_files
        total_files=$(find "$src_dir" -type f | wc -l)
        if [ "$total_files" -eq 0 ]; then
            return 0
        fi

        mkdir -p "$dst_dir"

        echo "[DEBUG-BP] Syncing blueprints category '$category' from $src_dir -> $dst_dir (files=$total_files)" >&2

        # 1) Copy files directly under category
        find "$src_dir" -mindepth 1 -maxdepth 1 -type f -name "*.y*ml" -print0 2>/dev/null | xargs -0r -I{} cp "{}" "$dst_dir/" || true

        # 2) Copy non-empty immediate subdirectories under category
        local subdir
        while IFS= read -r subdir; do
            [ -z "$subdir" ] && continue
            local sc
            sc=$(find "$subdir" -type f | wc -l)
            if [ "$sc" -gt 0 ]; then
                echo "[DEBUG-BP] Copying blueprint dir: $subdir -> $dst_dir" >&2
                cp -r "$subdir" "$dst_dir/" || true
            fi
        done < <(find "$src_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null || true)
    }

    # Prefer structured categories if present
    copy_bp_category automation
    copy_bp_category script

    # If there are legacy subdirectories directly under blueprints/, copy them to root
    # to maintain backward compatibility
    local legacy_dirs
    legacy_dirs=$(find "$bp_root" -mindepth 1 -maxdepth 1 -type d \( -name automation -o -name script \) -prune -o -type d -print 2>/dev/null | tr '\n' '\n')
    if [ -n "$legacy_dirs" ]; then
        local d
        while IFS= read -r d; do
            [ -z "$d" ] && continue
            local lc
            lc=$(find "$d" -type f | wc -l)
            if [ "$lc" -gt 0 ]; then
                echo "[DEBUG-BP] Copying legacy blueprint dir: $d -> $ha_bp_root" >&2
                cp -r "$d" "$ha_bp_root/" || true
            fi
        done <<EOF
$legacy_dirs
EOF
    fi

    return 0
}


is_backup_capable() {
    if dpkg -l | grep -q "^ii\s*thirdreality-hacore"; then
        return 0
    fi
    if dpkg -l | grep -q "^ii\s*thirdreality-zigbee-mqtt"; then
        return 0
    fi
    return 1
}

wait_for_backup_completion() {
    local max_wait=300  # Maximum wait time in seconds (5 minutes)
    local wait_interval=2  # Check interval in seconds
    local elapsed=0
    local api_url="http://127.0.0.1:8086/api/task/info?task=setting"
    
    echo "Waiting for backup to complete..."
    
    while [ $elapsed -lt $max_wait ]; do
        sleep $wait_interval
        elapsed=$((elapsed + wait_interval))
        
        # Query backup status
        local response
        response=$(curl -s "$api_url" 2>/dev/null || echo "")
        
        if [ -z "$response" ]; then
            # API might not be ready yet, continue waiting
            continue
        fi
        
        # Parse JSON response to extract status and progress
        # Try using jq if available, otherwise use grep/awk
        local status
        local progress
        
        if command -v jq >/dev/null 2>&1; then
            status=$(echo "$response" | jq -r '.data.status // "unknown"' 2>/dev/null || echo "unknown")
            progress=$(echo "$response" | jq -r '.data.progress // 0' 2>/dev/null || echo "0")
        else
            # Fallback: simple text parsing
            status=$(echo "$response" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tr -d '"' || echo "unknown")
            progress=$(echo "$response" | grep -o '"progress"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*' || echo "0")
        fi
        
        # Check if backup is completed (failed or success with progress 100)
        if [ "$status" = "failed" ]; then
            echo "Backup failed: $(echo "$response" | grep -o '"message"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tr -d '"' || echo "Unknown error")"
            return 0
        elif [ "$status" = "success" ] && [ "$progress" -eq 100 ]; then
            echo "Backup completed successfully (progress: ${progress}%)"
            return 0
        elif [ "$status" = "running" ]; then
            # Still running, show progress if available
            if [ -n "$progress" ] && [ "$progress" -gt 0 ]; then
                echo "Backup in progress: ${progress}%"
            fi
            continue
        fi
    done
    
    echo "Warning: Backup did not complete within ${max_wait} seconds"
    return 1
}

wait_for_restore_completion() {
    local max_wait=300  # Maximum wait time in seconds (5 minutes)
    local wait_interval=2  # Check interval in seconds
    local elapsed=0
    local api_url="http://127.0.0.1:8086/api/task/info?task=setting"
    
    echo "Waiting for restore to complete..."
    
    while [ $elapsed -lt $max_wait ]; do
        sleep $wait_interval
        elapsed=$((elapsed + wait_interval))
        
        # Query restore status
        local response
        response=$(curl -s "$api_url" 2>/dev/null || echo "")
        
        if [ -z "$response" ]; then
            # API might not be ready yet, continue waiting
            continue
        fi
        
        # Parse JSON response to extract status and progress
        # Try using jq if available, otherwise use grep/awk
        local status
        local progress
        
        if command -v jq >/dev/null 2>&1; then
            status=$(echo "$response" | jq -r '.data.status // "unknown"' 2>/dev/null || echo "unknown")
            progress=$(echo "$response" | jq -r '.data.progress // 0' 2>/dev/null || echo "0")
        else
            # Fallback: simple text parsing
            status=$(echo "$response" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tr -d '"' || echo "unknown")
            progress=$(echo "$response" | grep -o '"progress"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*' || echo "0")
        fi
        
        # Check if restore is completed (failed with progress 100, or success with progress 100)
        if [ "$status" = "failed" ] && [ "$progress" -eq 100 ]; then
            echo "Restore failed: $(echo "$response" | grep -o '"message"[[:space:]]*:[[:space:]]*"[^"]*"' | grep -o '"[^"]*"' | tr -d '"' || echo "Unknown error")"
            return 0
        elif [ "$status" = "success" ] && [ "$progress" -eq 100 ]; then
            echo "Restore completed successfully (progress: ${progress}%)"
            return 0
        elif [ "$status" = "running" ]; then
            # Still running, show progress if available
            if [ -n "$progress" ] && [ "$progress" -gt 0 ]; then
                echo "Restore in progress: ${progress}%"
            fi
            continue
        fi
    done
    
    echo "Warning: Restore did not complete within ${max_wait} seconds"
    return 1
}

perform_backup_if_ready() {
    local backup_dir="$BACKUP_DIR"
    local flag_primary="$backup_dir/.enable-backup"
    local flag_alt="$backup_dir/.enable_backup"

    if [ ! -d "$backup_dir" ] || [ ! -x "/usr/local/bin/supervisor" ]; then
        return 0
    fi

    if [ ! -f "$flag_primary" ] && [ ! -f "$flag_alt" ]; then
        return 0
    fi

    if is_backup_capable; then
        /usr/local/bin/supervisor led sys_event_off || true
        echo "Found .enable-backup flag, forcing backup..."
        echo "System found .enable-backup flag, forcing backup..." | wall
        /usr/local/bin/supervisor setting backup || true
        
        # Wait 1 second before checking status
        sleep 1
        
        # Wait for backup to complete
        wait_for_backup_completion
        
        rm -f "$flag_primary" "$flag_alt"
        echo "Backup completed, .enable-backup flag removed"
        /usr/local/bin/supervisor led sys_event_off || true
    else
        echo "Backup flag detected but required packages not installed; deferring backup."
    fi
}

validate_config() {
    local backup_dir="$BACKUP_DIR"
    local flag_primary="$backup_dir/.enable-backup"
    local flag_alt="$backup_dir/.enable_backup"

    if [ ! -d "$backup_dir" ]; then
        return 0
    fi

    if [ ! -f "$flag_primary" ] && [ ! -f "$flag_alt" ]; then
        return 0
    fi

    if is_backup_capable; then
        return 0
    fi

    echo "Warning: Backup flag present but required packages are missing. Removing flag..."
    rm -f "$flag_primary" "$flag_alt"
}

main_procedure()
{
    if [ -e "/usr/local/bin/supervisor" ]; then
        /usr/local/bin/supervisor led sys_firmware_updating  || true
    fi

    # Validate configuration first
    validate_config

    # Perform backup if requested
    perform_backup_if_ready

    # Flash board firmware from debug directory
    update_firmware_for_debug

    if [ -e "/usr/local/bin/supervisor" ]; then
        /usr/bin/sync
        /usr/local/bin/supervisor led sys_event_off || true
    fi

    # Auto restore functionality
    if [ -d "$BACKUP_DIR" ] && [ -e "/usr/local/bin/supervisor" ]; then
        perform_backup_if_ready

        # Check if .enable-restore exists - force restore if flag is present
        if [ -f "$BACKUP_DIR/.enable-restore" ] || [ -f "$BACKUP_DIR/.enable_restore" ]; then
            setting_files=$(find "$BACKUP_DIR" -maxdepth 1 -name "setting_*.tar.gz" -type f 2>/dev/null || true)
            if [ -n "$setting_files" ]; then
                /usr/local/bin/supervisor led sys_firmware_updating  || true
                echo "Found .enable-restore flag, attempting to restore..."
                echo "System found .enable-restore flag, attempting to restore..." | wall
                /usr/local/bin/supervisor setting restore || true

                sleep 1

                wait_for_restore_completion

                /usr/local/bin/supervisor led sys_event_off || true
                echo "Restore completed, .enable-restore flag removed"
                rm -f "$BACKUP_DIR/.enable-restore" "$BACKUP_DIR/.enable_restore"
            else
                echo "Warning: .enable-restore flag found but no setting files available"
                rm -f "$BACKUP_DIR/.enable-restore" "$BACKUP_DIR/.enable_restore"
            fi
        fi
    fi

    # Update OTA configurations
    update_ota_for_debug

    local zha_ota_updated=0
    local z2m_ota_updated=0
    if [ -d "$DEBUG_OTA_DIR" ]; then
        zha_ota_updated=$(update_zha_ota_config)
        z2m_ota_updated=$(update_z2m_ota_config)
    fi

    # Update Home Assistant blueprints from debug directory (DEBUG feature)
    update_blueprints_for_debug

    # Force filesystem sync
    /usr/bin/sync

    # Update ZHA quirks
    local zha_py_files_count
    zha_py_files_count=$(update_zha_quirks_for_debug)

    /usr/bin/sync

    # Update Z2M converters
    local z2m_js_files_count
    z2m_js_files_count=$(update_z2m_quirks_for_debug)

    /usr/bin/sync

    # Restart Home Assistant if ZHA quirks or OTA were updated
    if { [ "$zha_py_files_count" -gt 0 ] || [ "$zha_ota_updated" -gt 0 ]; } && systemctl is-active --quiet home-assistant.service; then
        echo "[MAIN] Processed ZHA quirks=$zha_py_files_count, OTA updates=$zha_ota_updated" >&2
        echo "[MAIN] Restarting Home Assistant service to apply changes..." >&2
        systemctl restart home-assistant.service || true
        echo "[MAIN] Home Assistant service restarted successfully" >&2
    fi

    # Restart Zigbee2MQTT if Z2M converters or OTA were updated
    if { [ "$z2m_js_files_count" -gt 0 ] || [ "$z2m_ota_updated" -gt 0 ]; } && systemctl is-active --quiet zigbee2mqtt.service; then
        echo "[MAIN] Processed Z2M converters=$z2m_js_files_count, OTA updates=$z2m_ota_updated" >&2
        echo "[MAIN] Restarting Zigbee2MQTT service to apply changes..." >&2
        systemctl restart zigbee2mqtt.service || true
        echo "[MAIN] Zigbee2MQTT service restarted successfully" >&2
    fi

    # Rename R3Debug directory after processing
    if [ -d "$DEBUG_DIR" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local new_debug_dir="${DEBUG_DIR}_${timestamp}"
        echo "[MAIN] Renaming $DEBUG_DIR to $new_debug_dir" >&2
        mv "$DEBUG_DIR" "$new_debug_dir" || true
        echo "[MAIN] Debug directory renamed successfully" >&2
        /usr/bin/sync
    fi
}


main_procedure

exit 0
