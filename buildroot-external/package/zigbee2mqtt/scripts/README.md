# Zigbee2MQTT 脚本

这个目录包含 Zigbee2MQTT 运行所需的辅助脚本。

## 脚本说明

### zigbee2mqtt_blz_reset.sh
- **用途**: BLZ 适配器重置脚本
- **运行时机**: 在 zigbee2mqtt 服务启动之前执行（ExecStartPre）
- **位置**: `/opt/zigbee2mqtt/scripts/zigbee2mqtt_blz_reset.sh`

### z2m-permit-on-passlist.sh
- **用途**: 启动后自动允许白名单设备加入
- **运行时机**: 在 zigbee2mqtt 服务启动后延迟 8 秒执行（ExecStartPost）
- **位置**: `/opt/zigbee2mqtt/scripts/z2m-permit-on-passlist.sh`

## 使用说明

这些脚本会在构建时自动复制到目标系统的 `/opt/zigbee2mqtt/scripts/` 目录，并在 systemd 服务文件中被引用。

不需要手动操作，systemd 会自动调用它们。
