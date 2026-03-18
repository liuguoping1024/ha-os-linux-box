
################################################################################
#
# amlogic-boot-fip-legacy
#
# Provides bootloader images built with the Amlogic legacy SDK
# (old BL2/BL30/BL31 + ACS DDR parameter support), packaged together with
# a freshly built U-Boot BL33 from Buildroot.
#
################################################################################

AMLOGIC_BOOT_FIP_LEGACY_VERSION = 1.0
AMLOGIC_BOOT_FIP_LEGACY_SITE_METHOD = local
AMLOGIC_BOOT_FIP_LEGACY_SITE = $(BR2_EXTERNAL_HASSOS_PATH)/board/thirdreality/$(call qstrip,$(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD))/fip
AMLOGIC_BOOT_FIP_LEGACY_INSTALL_IMAGES = YES
AMLOGIC_BOOT_FIP_LEGACY_DEPENDENCIES = uboot
AMLOGIC_BOOT_FIP_LEGACY_LICENSE = PROPRIETARY
AMLOGIC_BOOT_FIP_LEGACY_REDISTRIBUTE = NO

ifeq ($(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY),y)
ifeq ($(call qstrip,$(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD)),)
$(error No board name specified, check your BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD setting)
endif
endif

define AMLOGIC_BOOT_FIP_LEGACY_BUILD_CMDS
	# Build legacy FIP + bootloader images using the Amlogic SDK
	# The script will:
	#   - compile U-Boot BL33 with SDK patches (v2015.01)
	#   - use legacy BL2/BL30/BL31 blobs + ACS DDR tool
	#   - output u-boot.bin* files into the current directory
	cd $(@D) && ./build-fip-legacy.sh $(call qstrip,$(BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY_BOARD))
endef

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
