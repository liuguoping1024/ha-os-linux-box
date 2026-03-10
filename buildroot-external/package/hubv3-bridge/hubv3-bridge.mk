################################################################################
#
# hubv3-bridge
#
################################################################################

HUBV3_BRIDGE_VERSION = fb7dd076e1fcb7b7a3ae88acf1b881669adf64a9
HUBV3_BRIDGE_SITE = git@github.com:liuguoping1024/hubv3_service.git
HUBV3_BRIDGE_SITE_METHOD = git
HUBV3_BRIDGE_LICENSE = Proprietary
HUBV3_BRIDGE_DEPENDENCIES = \
	host-pkgconf libwebsockets openssl libcurl libyaml cjson mosquitto dbus jq

HUBV3_BRIDGE_CONF_OPTS = \
	-DCMAKE_BUILD_TYPE=Release \
	-DUSE_SYSTEM_LIBWEBSOCKETS=ON \
	-DBUILD_TESTING=OFF

define HUBV3_BRIDGE_INSTALL_EXTRAS
	$(INSTALL) -d $(TARGET_DIR)/etc/hubv3-bridge
	$(INSTALL) -D -m 0644 $(@D)/config/configuration.yaml \
		$(TARGET_DIR)/etc/hubv3-bridge/configuration.yaml
	$(INSTALL) -D -m 0755 $(@D)/config/command.sh \
		$(TARGET_DIR)/etc/hubv3-bridge/command.sh
endef
HUBV3_BRIDGE_POST_INSTALL_TARGET_HOOKS += HUBV3_BRIDGE_INSTALL_EXTRAS

define HUBV3_BRIDGE_INSTALL_INIT_SYSTEMD
	$(INSTALL) -D -m 0644 $(HUBV3_BRIDGE_PKGDIR)/linuxbox-hubv3-bridge.service \
		$(TARGET_DIR)/etc/systemd/system/linuxbox-hubv3-bridge.service
endef

$(eval $(cmake-package))
