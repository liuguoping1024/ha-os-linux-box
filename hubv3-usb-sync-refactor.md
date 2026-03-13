# hubv3-usb-sync.sh 重构说明

## 背景

原脚本位于 `usr/lib/thirdreality/hubv3-usb-sync.sh`，已重新定位至
`usr/local/bin/hubv3-usb-sync.sh`（标准可执行路径）。

本次重构在迁移路径的同时完成以下清理工作。

---

## 功能分类（原版）

| 类别 | 函数 | 本次处理 |
|------|------|----------|
| ① deb 安装 | `install_extra_debs` / `install_deb_if_needed` / `dpkg_install` / `execute_fix_dependency_if_needed` / `install_board_flash_debs` / `install_core_matter_debs` / `install_zigbee2mqtt_debs` / `install_thirdreality_bridge_debs` / `install_openhab_debs` / `install_music_assistant_debs` / `install_enocean_debs` / `install_zwave_debs` / `install_linux_image_deb` / `install_supervisor_deb` | **全部删除** |
| ② Backup / Restore | `is_backup_capable` / `wait_for_backup_completion` / `wait_for_restore_completion` / `perform_backup_if_ready` / `validate_config` | 保留，路径变量化 |
| ③ 自动复制文件/修改配置 | `update_z2m_quirks_for_debug` / `update_zha_quirks_for_debug` / `update_zha_ota_config` / `update_z2m_ota_config` / `update_ota_for_debug` / `update_etc_for_install` / `update_blueprints_for_debug` | 保留 |
| ④ 烧写子板 | `update_firmware_for_debug` | 保留，直接在 main 中调用 |
| ⑤ 其他 | 全局变量 / `on_exit` / `main_procedure` | 更新 |

---

## 变更详情

### 1. 删除 deb 安装支持

Buildroot 系统不使用 apt/dpkg，移除全部 14 个 deb 安装函数及相关逻辑。

**删除的变量：**
```bash
# 已删除
DEBIAN_FRONTEND=noninteractive
APT_LISTCHANGES_FRONTEND=none
MACHINE=odroid-n2
TIMEOUT=1200
```

**删除的数组：**
```bash
# 已删除
exclude_patterns=(
    "board_firmware_"
    "linuxbox-supervisor_"
    "python3_"
    ...
)
```

**删除的函数（共 14 个）：**
- `install_extra_debs`
- `execute_fix_dependency_if_needed`
- `install_deb_if_needed`
- `dpkg_install`
- `install_board_flash_debs`
- `install_core_matter_debs`
- `install_zigbee2mqtt_debs`
- `install_thirdreality_bridge_debs`
- `install_openhab_debs`
- `install_music_assistant_debs`
- `install_enocean_debs`
- `install_zwave_debs`
- `install_linux_image_deb`
- `install_supervisor_deb`

---

### 2. USB 存储挂载路径变更

#### 问题

原代码将 USB 挂载路径硬编码为 `/mnt`，在 Buildroot 环境下不适用：
- `/mnt` 通常作为临时手动挂载点
- `/mnt/data` 已用于持久数据分区
- Buildroot 的 mdev/udev 不会自动挂载到 `/mnt` 根目录

#### 方案选择

| 候选路径 | 分析 |
|----------|------|
| `/mnt/media` | ✅ **选用**：专用于可移除设备，与 `/mnt/data` 明确分离，语义清晰 |
| `/mnt/data/media` | ❌ 将外部媒体混入持久数据分区，逻辑混乱 |
| `/media/usb` | ❌ 与 systemd-automount 默认路径冲突风险 |

#### 变更

新增 `USB_MOUNT` 变量，所有路径统一基于该变量：

```bash
# 旧
WORK_DIR="/mnt/R3Install"
DEBUG_DIR="/mnt/R3Debug"
# backup_dir="/mnt/R3Backup"  (各函数内硬编码)

# 新
USB_MOUNT="/mnt/media"
WORK_DIR="$USB_MOUNT/R3Install"
DEBUG_DIR="$USB_MOUNT/R3Debug"
BACKUP_DIR="$USB_MOUNT/R3Backup"
```

`perform_backup_if_ready` 和 `validate_config` 中原来硬编码的 `/mnt/R3Backup` 均替换为 `$BACKUP_DIR`。

---

### 3. on_exit() 精简

移除已无意义的 deb 安装完成提示语：

```bash
# 已删除
echo "System finished to install deb packages. " | wall
```

---

### 4. main_procedure() 重写

移除全部 deb 安装调用，保留核心流程：

```
main_procedure 新流程:
  1. LED 状态提示（firmware_updating）
  2. validate_config        — 校验 backup 标志完整性
  3. perform_backup_if_ready — 执行备份（若有标志）
  4. update_firmware_for_debug — 烧写 Zigbee/Thread 固件
  5. LED 状态恢复（sys_event_off）
  6. Auto restore           — 从 USB 恢复配置（若有标志）
  7. update_ota_for_debug   — OTA 固件索引更新
  8. update_zha/z2m_ota_config — OTA 配置写入
  9. update_etc_for_install — /etc 文件覆盖（DEBUG）
 10. update_blueprints_for_debug — HA blueprints 同步
 11. update_zha_quirks_for_debug — ZHA quirks 同步
 12. update_z2m_quirks_for_debug — Z2M converters 同步
 13. 按需重启 home-assistant / zigbee2mqtt
 14. 重命名 R3Debug 目录（防重复执行）
```

---

## 文件对应关系

| 项目 | 路径 |
|------|------|
| 修改后脚本 | `usr/local/bin/hubv3-usb-sync.sh` |
| 变更说明（本文件） | `usr/local/bin/hubv3-usb-sync-refactor.md` |
| Diff patch | `usr/local/bin/hubv3-usb-sync-refactor.patch` |
| Service 文件（未改动） | `usr/lib/systemd/system/hubv3-usb-sync.service` |

> **注意**：service 文件的 `ExecStart` 目前仍指向
> `/usr/lib/thirdreality/hubv3-usb-sync.sh`（运行时热更新路径）。
> 若需将 service 直接指向 `/usr/local/bin/hubv3-usb-sync.sh`，
> 需同步修改 service 文件并更新 udev 挂载规则以确保 `/mnt/media` 在
> service 启动前已完成挂载（`After=mnt-media.mount`）。

---

## 行数对比

| 版本 | 行数 |
|------|------|
| 原版（`usr/lib/thirdreality/hubv3-usb-sync.sh`） | 1452 |
| 新版（`usr/local/bin/hubv3-usb-sync.sh`） | 913 |
| 净减少 | **539 行（-37%）** |
