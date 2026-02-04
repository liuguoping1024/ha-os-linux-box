# Meson64 内核补丁说明

## 补丁来源
这些补丁来自 Armbian 项目,已适配到 Linux Kernel v6.6.120

## 补丁总数: 29个

## 补丁分类

### 电源管理 (3个)
- `0001-pyavitz-meson64-generalized-odroid-reboot-driver.patch` - Meson64重启驱动
- `0003-HACK-arm64-meson-add-Amlogic-Meson-GX-PM-Suspend.patch` - 系统休眠支持
- `0031-HACK-arm64-dts-meson-add-support-for-GX-PM-and-Virtu.patch` - PM和RTC设备树

### Device Tree Overlay (2个)
- `0004-add-overlay-compilation-support-to-meson64-dev.patch` - Overlay编译支持
- `0019-general-meson64-overlays.patch` - Overlay构建目标

### GPU/显示 (2个)
- `0005-drm-panfrost-fix-reference-leak-in-panfrost_job_hw_s.patch` - Mali GPU修复
- `0007-ODROID-COMMON-gpu-drm-add-new-display-resolution-256.patch` - 2K分辨率支持

### 核心修复 (1个)
- `0010-HACK-of-partial-revert-of-fdt.c-changes.patch` - secmon内存预留修复

### 音频 (1个)
- `0011-ASoC-meson-aiu-Fix-HDMI-codec-control-selection.patch` - HDMI音频修复

### 存储/MMC (3个)
- `0012-arm64-amlogic-mmc-meson-gx-Add-core-tx-rx-eMMC-SD-SD.patch` - MMC时钟相位配置
- `0013-arm64-amlogic-dts-meson-update-meson-axg-device-tree.patch` - AXG MMC设备树
- `0014-arm64-dts-docs-Update-mmc-meson-gx-documentation-for.patch` - MMC文档

### 视频解码 (5个)
- `0015-WIP-drivers-meson-vdec-add-HEVC-decode-codec.patch` - HEVC解码
- `0016-WIP-drivers-meson-vdec-add-handling-to-HEVC-decoder-.patch` - HEVC处理
- `0017-WIP-drivers-meson-vdec-check-if-parser-has-really-pa.patch` - HEVC解析检查
- `0032-WIP-drivers-meson-vdec-add-HEVC-support-to-GXBB.patch` - GXBB HEVC支持
- `0033-drivers-meson-vdec-add-VP9-support-to-GXM.patch` - GXM VP9支持

### 红外遥控 (2个)
- `0020-media-rc-drivers-should-produce-alternate-pulse-and-.patch` - 红外事件处理
- `0030-pinctrl-meson-g12a-add-missing-ir-options.patch` - 红外引脚配置

### SoC信息识别 (6个)
- `0021-soc-amlogic-meson-gx-socinfo-Add-S905L-ID.patch` - S905L识别
- `0022-soc-amlogic-meson-gx-socinfo-add-new-A113X-SoC-id.patch` - A113X识别
- `0023-soc-amlogic-meson-gx-socinfo-move-common-code-to-hea.patch` - 代码重构
- `0024-soc-amlogic-meson-gx-socinfo-sm-Add-Amlogic-secure-m.patch` - Secure monitor
- `0025-arm64-dts-meson-add-dts-links-to-secure-monitor-for-.patch` - DTS链接
- `0026-dt-bindings-arm-amlogic-amlogic-meson-gx-ao-secure-a.patch` - 设备树绑定

### 外设驱动 (3个)
- `0028-spi-nor-add-support-for-XT25F128B-XT25Q64.patch` - XTX SPI Flash
- `0029-usb-core-improve-handling-of-hubs-with-no-ports.patch` - USB hub处理
- `0035-Fix-meson64-add-gpio-irq-patch-from-https-lkml.org-l.patch` - **GPIO中断支持(重要!)**

### 性能优化 (1个)
- `0034-Add-higher-clocks-for-SM1-family.patch` - SM1更高频率(2.016GHz/2.1GHz)

## 关键补丁说明

### ⭐⭐⭐⭐⭐ 必需补丁
1. **0001** - Meson64重启功能
2. **0003+0031** - 系统休眠功能
3. **0010** - 修复secmon内存问题
4. **0012** - eMMC/SD稳定性
5. **0015-0017** - 视频硬件解码
6. **0021-0026** - SoC正确识别
7. **0035** - GPIO中断功能(所有GPIO中断依赖此补丁!)

### ⭐⭐⭐⭐ 重要补丁
- **0004+0019** - Device Tree Overlay支持
- **0005** - Mali GPU稳定性
- **0011** - HDMI音频
- **0020+0030** - 红外遥控
- **0029** - USB兼容性(S905W等)

### ⭐⭐⭐ 增强补丁
- **0007** - 2K显示支持
- **0028** - 特定Flash芯片
- **0032-0033** - 特定SoC视频解码
- **0034** - SM1超频

## 未包含的补丁

### 已在上游 (2个)
- `0002-Revert-USB-core-changes-causing-issues-with-Z-Wave.m.patch` - v6.6.120已包含
- `0008-WIP-ASoC-hdmi-codec-reorder-channel-allocation-list.patch` - v6.6.120已包含

### 有冲突 (1个)
- `0018-WIP-drivers-meson-vdec-improve-mmu-and-fbc-handling-.patch` - 需要手动解决

### 硬件特定 (5个)
- `0006-HACK-arm64-fix-Kodi-sysinfo-CPU-information.patch` - 仅Kodi需要
- `0009-HACK-media-cec-silence-CEC-timeout-message.patch` - 日志静默(可选)
- `0036-0038` - JetHub特定硬件
- `0039` - JetHub J200特定

### 通用功能 (1个)
- `0001-ipv6-add-option-to-explicitly-enable-reachability-te.patch` - IPv6功能(非Meson特定)

## 应用顺序
Buildroot会按照补丁文件名的数字顺序自动应用。
补丁编号已保持原始顺序,确保依赖关系正确。

## 验证
这些补丁已在 Linux v6.6.120 上成功应用和测试。

## 参考
详细分析见: `/root/linuxbox/linux-stable/COMPLETE_PATCH_ANALYSIS.md`
