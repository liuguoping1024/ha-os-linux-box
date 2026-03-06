#!/bin/bash
#
# Zigbee2MQTT BLZ Reset Script (HubV3B)
# GPIO pins: DB_RSTN1 = GPIOZ_1 (1), DB_BOOT1 = GPIOZ_3 (3)
#

set -e

LOG_FILE="/var/log/zigbee2mqtt_blz_reset.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_gpio_tools() {
    if ! command -v gpioset &> /dev/null; then
        log "ERROR: gpioset command not found. Please install gpiod tools:"
        log "  sudo apt-get install gpiod"
        exit 1
    fi
}

gpio_reset_sequence() {
    log "Starting Zigbee GPIO reset sequence..."

    # GPIOZ_1 (pin 1) = reset, GPIOZ_3 (pin 3) = boot/ISP
    gpioset 0 1=1
    sleep 0.2

    gpioset 0 1=0
    sleep 0.2

    gpioset 0 3=1
    sleep 0.2

    gpioset 0 3=0
    sleep 0.2

    gpioset 0 3=1
    sleep 0.5

    log "Zigbee GPIO reset sequence completed"
}

log "Starting Zigbee2MQTT BLZ reset process..."

check_gpio_tools

gpio_reset_sequence

log "Zigbee2MQTT BLZ reset process completed"
