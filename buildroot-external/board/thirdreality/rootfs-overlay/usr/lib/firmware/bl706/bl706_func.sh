#!/bin/sh
# refer to pinctrl-meson-axg.c

reset_module()
{
    if [ "$1" = "zigbee" ]; then
        # Zigbee reset: DB_RSTN1/GPIOZ_1
        gpioset 0 1=0
        sleep 0.1
        gpioset 0 1=1
    elif [ "$1" = "thread" ]; then
        # Thread reset: DB_RSTN2/GPIOA_1
        gpioset 0 27=0
        sleep 0.1
        gpioset 0 27=1
    else
        echo "Invalid mode: $1. Use 'zigbee' or 'thread'."
        exit 1
    fi
    sleep 0.1
}

enter_isp_mode()
{
    if [ "$1" = "zigbee" ]; then
        # Zigbee boot: DB_BOOT1/GPIOZ_3
        gpioset 0 3=1
        sleep 0.1

        reset_module "zigbee"

        gpioset 0 3=0
    elif [ "$1" = "thread" ]; then
        # Thread boot: DB_BOOT2/GPIOA_3
        gpioset 0 29=1
        sleep 0.1

        reset_module "thread"

        gpioset 0 29=0
    else
        echo "Invalid mode: $1. Use 'zigbee' or 'thread'."
        exit 1
    fi

    sleep 0.1
}

disable_isp()
{
    if [ "$1" = "zigbee" ]; then
        # Zigbee boot: DB_BOOT1/GPIOZ_3
        gpioset 0 3=0
    elif [ "$1" = "thread" ]; then
        # Thread boot: DB_BOOT2/GPIOA_3
        gpioset 0 29=0
    fi
    sleep 0.1
}

BFLB_IOT_DIR="/usr/lib/firmware/bl706/bflb_iot"

flash_firmware()
{
    mode=$1
    image_size_dir="partition_images"

    if [ "$mode" = "zigbee" ]; then
        port="/dev/ttyAML3"
        firmware="/usr/lib/firmware/bl706/${image_size_dir}/blz_whole_img.bin"
    elif [ "$mode" = "zigate" ]; then
        port="/dev/ttyAML3"
        firmware="/usr/lib/firmware/bl706/${image_size_dir}/zigate_whole_img.bin"
        mode="zigbee"
    elif [ "$mode" = "blz" ]; then
        port="/dev/ttyAML3"
        firmware="/usr/lib/firmware/bl706/${image_size_dir}/blz_whole_img.bin"
        mode="zigbee"
    elif [ "$mode" = "thread" ]; then
        port="/dev/ttyAML6"
        firmware="/usr/lib/firmware/bl706/${image_size_dir}/thread_whole_img.bin"
    else
        echo "Invalid mode: $mode. Use 'zigbee', 'zigate', 'blz' or 'thread'."
        exit 1
    fi

    if [ ! -d "${BFLB_IOT_DIR}" ]; then
        echo "Error: ${BFLB_IOT_DIR} not found. Firmware tool not installed."
        exit 1
    fi

    enter_isp_mode $mode

    echo "Burning Image, mode: $mode. port: $port . firmware: $firmware"
    python3 "${BFLB_IOT_DIR}/core/bflb_iot_tool.py" --chipname=bl702 --port=$port --baudrate=921600 --addr=0x0 --firmware="$firmware" --single

    if [ $? -eq 0 ]; then
        echo "Burn successfully"
    else
        echo "Burning failed, retrying..."
        python3 "${BFLB_IOT_DIR}/core/bflb_iot_tool.py" --chipname=bl702 --port=$port --baudrate=921600 --addr=0x0 --firmware="$firmware" --single
    fi

    disable_isp $mode
}

case "$1" in
    start)
    mode=${2:-zigbee}  # default to zigbee if no second argument
    echo "BL706: start $mode ..."
    disable_isp $mode # Default to zigbee if mode not specified
    reset_module $mode
    ;;

    restart)
    mode=${2:-zigbee}  # default to zigbee if no second argument
    echo "BL706: restart $mode ..."
    disable_isp $mode # Default to zigbee if mode not specified
    reset_module $mode
    ;;

    flash)
    mode=${2:-zigbee}  # [zigbee|thread]: default to zigbee if no second argument
    echo "BL706: flash $mode ..."
    flash_firmware $mode
    disable_isp $mode
    reset_module $mode
    ;;

    *)
    echo "Usage: $0 {start [zigbee|thread]|restart [zigbee|thread]|flash [zigbee|thread]}"
    exit 1
    ;;
esac

