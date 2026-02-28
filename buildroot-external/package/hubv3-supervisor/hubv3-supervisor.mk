################################################################################
#
# hubv3-supervisor
#
################################################################################

HUBV3_SUPERVISOR_VERSION = bc9a0823afd592996ceeb029bd2711fe7cf33471
HUBV3_SUPERVISOR_SITE = https://github.com/liuguoping1024/LinuxBox_Supervisor.git
HUBV3_SUPERVISOR_SITE_METHOD = git
HUBV3_SUPERVISOR_LICENSE = Proprietary
HUBV3_SUPERVISOR_DEPENDENCIES = \
	host-pkgconf libglib2 json-c avahi libgpiod openssl \
	libmicrohttpd libcurl libyaml sqlite cjson bluez5_utils

HUBV3_SUPERVISOR_CONF_OPTS = -DCMAKE_BUILD_TYPE=Release

define HUBV3_SUPERVISOR_INSTALL_EXTRAS
	# D-Bus policy
	$(INSTALL) -D -m 0644 $(@D)/config/dbus/com.thirdreality.linuxbox.Supervisor.conf \
		$(TARGET_DIR)/etc/dbus-1/system.d/com.thirdreality.linuxbox.Supervisor.conf
	# Config directory with defaults (rootfs-overlay will override configuration.yaml)
	$(INSTALL) -d $(TARGET_DIR)/var/lib/hubv3-supervisor
	$(INSTALL) -D -m 0644 $(@D)/config/configuration.yaml \
		$(TARGET_DIR)/var/lib/hubv3-supervisor/configuration.yaml
	# Static web UI files
	$(INSTALL) -d $(TARGET_DIR)/var/lib/hubv3-supervisor/static/css
	$(INSTALL) -d $(TARGET_DIR)/var/lib/hubv3-supervisor/static/js
	cp -dpfr $(@D)/config/static/* $(TARGET_DIR)/var/lib/hubv3-supervisor/static/
	# Zigbee2MQTT conf templates
	$(INSTALL) -d $(TARGET_DIR)/var/lib/hubv3-supervisor/conf
	cp -dpfr $(@D)/config/conf/* $(TARGET_DIR)/var/lib/hubv3-supervisor/conf/
endef
HUBV3_SUPERVISOR_POST_INSTALL_TARGET_HOOKS += HUBV3_SUPERVISOR_INSTALL_EXTRAS

define HUBV3_SUPERVISOR_INSTALL_INIT_SYSTEMD
	$(INSTALL) -D -m 0644 $(@D)/supervisor.service \
		$(TARGET_DIR)/etc/systemd/system/supervisor.service
endef

$(eval $(cmake-package))
