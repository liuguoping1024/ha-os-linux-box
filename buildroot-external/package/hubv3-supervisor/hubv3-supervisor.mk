################################################################################
#
# hubv3-supervisor
#
################################################################################

HUBV3_SUPERVISOR_VERSION = 6019daebc29ebe7e0f7114deaf43d0ea846bc047
HUBV3_SUPERVISOR_SITE = git@github.com:liuguoping1024/LinuxBox_Supervisor.git
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
	# Default config (read-only, copied to /mnt/overlay on first boot by os-overlay)
	$(INSTALL) -d $(TARGET_DIR)/etc/hubv3-supervisor
	$(INSTALL) -D -m 0644 $(@D)/config/configuration.yaml \
		$(TARGET_DIR)/etc/hubv3-supervisor/configuration.yaml
	# Zigbee2MQTT conf templates (read-only)
	$(INSTALL) -d $(TARGET_DIR)/etc/hubv3-supervisor/conf
	cp -dpfr $(@D)/config/conf/* $(TARGET_DIR)/etc/hubv3-supervisor/conf/
	# Static web UI files (read-only, served directly from /usr/share)
	$(INSTALL) -d $(TARGET_DIR)/usr/share/hubv3-supervisor/static/css
	$(INSTALL) -d $(TARGET_DIR)/usr/share/hubv3-supervisor/static/js
	cp -dpfr $(@D)/config/static/* $(TARGET_DIR)/usr/share/hubv3-supervisor/static/
endef
HUBV3_SUPERVISOR_POST_INSTALL_TARGET_HOOKS += HUBV3_SUPERVISOR_INSTALL_EXTRAS

define HUBV3_SUPERVISOR_INSTALL_INIT_SYSTEMD
	$(INSTALL) -D -m 0644 $(@D)/supervisor.service \
		$(TARGET_DIR)/etc/systemd/system/supervisor.service
endef

$(eval $(cmake-package))
