
################################################################################
#
# amlogic-boot-fip-legacy
#
# Provides prebuilt bootloader images from the Amlogic legacy SDK
# (U-Boot 2015.01 + old FIP toolchain with ACS DDR parameter support).
#
################################################################################

AMLOGIC_BOOT_FIP_LEGACY_VERSION = 1.0
AMLOGIC_BOOT_FIP_LEGACY_SITE_METHOD = local
AMLOGIC_BOOT_FIP_LEGACY_SITE = $(BR2_EXTERNAL_HASSOS_PATH)/board/thirdreality/$(call qstrip,$(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD))/fip
AMLOGIC_BOOT_FIP_LEGACY_INSTALL_IMAGES = YES
AMLOGIC_BOOT_FIP_LEGACY_LICENSE = PROPRIETARY
AMLOGIC_BOOT_FIP_LEGACY_REDISTRIBUTE = NO

ifeq ($(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY),y)
ifeq ($(call qstrip,$(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD)),)
$(error No board name specified, check your BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD setting)
endif
endif

define AMLOGIC_BOOT_FIP_LEGACY_INSTALL_IMAGES_CMDS
	cp -dpf "$(@D)/u-boot.bin.sd.bin" "$(BINARIES_DIR)/u-boot.bin.sd.bin"
	if [ -f "$(@D)/u-boot.bin" ]; then \
		cp -dpf "$(@D)/u-boot.bin" "$(BINARIES_DIR)/u-boot.bin"; \
	fi
	if [ -f "$(@D)/u-boot.bin.usb.bl2" ]; then \
		cp -dpf "$(@D)/u-boot.bin.usb.bl2" "$(BINARIES_DIR)/u-boot.bin.usb.bl2"; \
	fi
	if [ -f "$(@D)/u-boot.bin.usb.tpl" ]; then \
		cp -dpf "$(@D)/u-boot.bin.usb.tpl" "$(BINARIES_DIR)/u-boot.bin.usb.tpl"; \
	fi
endef

$(eval $(generic-package))
