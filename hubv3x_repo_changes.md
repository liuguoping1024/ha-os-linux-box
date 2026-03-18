# HubV3X（本仓库改动说明 / 换机编译指南）

本文档用于在更换 PC 后，快速复现本仓库对 **Thirdreality HubV3X** 的改动与编译流程，并强调 **Amlogic SDK 许可限制**（专有 bootloader blobs 不能上传到 GitHub）。

> 分支：`amlogic-v11.2`  
> 主要提交：
> - `9e73cfb62`：Add HubV3X board variant with legacy Amlogic SDK bootloader  
> - `bcdb4c7bd`：Remove Amlogic proprietary FIP binaries from git tracking

---

## 目标与约束

- **目标**：新增板级 `hubv3x`（基于 `hubv3a`），适配 Amlogic A113X/AXG（S420），并支持 **2×512MB DDR（总 1GB）**。
- **核心约束**：老 SDK 的 BL2 需要 ACS DDR 参数机制（DDR 配置/时序从 BL33 侧导出并被 BL2 侧使用），现代 FIP/现代 U-Boot 流程不兼容此机制。
- **许可约束**：Amlogic SDK 中的 **BL2/BL30/BL31/加密工具等专有二进制**不得上传 GitHub。允许在本地构建时复制到工作目录使用。

---

## 本仓库新增/修改的内容（文件清单）

### 1) 新增 HubV3X 板级目录

目录：`buildroot-external/board/thirdreality/hubv3x/`

包含：
- `meta`：板级元信息（`BOARD_ID=hubv3x` 等）
- `boot-env.txt`：U-Boot 环境变量（`fdtfile=amlogic/meson-axg-thirdreality-hub-v3x.dtb`）
- `hassos-hook.sh`：post-image 阶段拷贝 DTB / overlays / boot.scr 等
- `cmdline.txt` / `partition-spl-spl.cfg` / `image-spl-spl.cfg`：镜像分区相关
- `rootfs-overlay/`：用户态 overlay（armbian-release、t3r-release、zigbee2mqtt、systemd 单元等）

### 2) 新增 HubV3X Linux DTS 补丁

文件：`buildroot-external/board/thirdreality/patches/linux/0044-add-arm64-dts-thirdreality-hub-v3x.patch`

作用：
- 新增 `meson-axg-thirdreality-hub-v3x.dts`
- 兼容字符串/型号描述为 HubV3X
- memory 配置保持 1GB（后续 DDR timing 细化在 bootloader 侧处理）

### 3) HubV3X Buildroot defconfig

文件：`buildroot-external/configs/thirdreality_hubv3x_defconfig`

现状说明：
- 内核：`Linux 6.6.120`（与 hubv3a 一致）
- bootloader：启用 `BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY=y`
- **注意**：该 defconfig 后续会根据“Buildroot 内 fresh 编译 U-Boot + legacy FIP 打包”的新方案继续调整（见“后续计划”）。

### 4) HubV3X 内核配置

文件：`buildroot-external/board/thirdreality/kernel-linuxbox-hubv3x.config`  
来源：从 `hubv3a` 拷贝（保持一致）。

### 5) legacy FIP Buildroot 包（用于接入老 SDK FIP 产物）

目录：`buildroot-external/package/amlogic-boot-fip-legacy/`

文件：
- `Config.in`：Kconfig 入口（`BR2_PACKAGE_AMLOGIC_BOOT_FIP_LEGACY`）
- `amlogic-boot-fip-legacy.mk`：将 legacy bootloader 产物安装到 `$(BINARIES_DIR)`

并在 `buildroot-external/Config.in` 增加：
- `source "$BR2_EXTERNAL_HASSOS_PATH/package/amlogic-boot-fip-legacy/Config.in"`

### 6) HubV3X legacy FIP 构建脚本（本地使用）

文件：`buildroot-external/board/thirdreality/hubv3x/fip/build-fip-legacy.sh`

用途：
- 使用 Amlogic SDK 的工具/流程（`mk` / `fip_create` / `aml_encrypt_axg` / `acs_tool` 等）将 BL2/BL30/BL31 与 BL33 组合打包生成 `u-boot.bin*`。
- **强调**：脚本会在工作目录下生成包含专有 blob 的文件，必须保持 `.gitignore` 排除，不可上传。

配套忽略文件：
- `buildroot-external/board/thirdreality/hubv3x/fip/.gitignore`
  - 忽略 `blobs/ tools/ build/ u-boot.bin*` 等

### 7) 构建脚本支持 hubv3x

文件：`make-buildroot-release.sh`

改动：
- 增加 `-b hubv3x` 选项与 defconfig 映射

---

## 新 PC 上准备工作

### 1) 拉取代码与子模块

在仓库根目录：

```bash
git submodule update --init --recursive
```

### 2) Amlogic SDK 放置位置（仅本地）

默认参考路径：
- `/root/linuxbox/sdk_A113X_202210`

注意：
- SDK 仅用于本地编译和复制产物，不要提交/上传 SDK 或其中的二进制 blobs。

### 3) 必要工具（宿主机）

至少需要：
- `aarch64-linux-gnu-gcc`（交叉编译）
- `arm-none-eabi-gcc`（用于部分固件/工具链）
- `python3`

---

## 编译流程（当前版本）

### 方案 A：先本地构建 legacy FIP（生成 u-boot.bin*），再跑 Buildroot

1) 在 SDK 环境内完成 legacy bootloader 打包（输出会落在 hubv3x/fip 的工作目录或 SDK 的 build 目录，取决于脚本/调用方式）：

```bash
cd buildroot-external/board/thirdreality/hubv3x/fip
./build-fip-legacy.sh
```

2) 编译系统镜像：

```bash
./make-buildroot-release.sh -b hubv3x clean
```

输出目录：
- `output/images/`

---

## 许可与合规（必须遵守）

- **禁止上传到 GitHub 的内容**（示例）：
  - `bl2.bin` / `bl30.bin` / `bl31.img`（或 `bl31_1.3` 相关）
  - `aml_encrypt_*` / `fip_create` 等打包工具（若为 SDK 专有分发）
  - 打包后的 `u-boot.bin*`（内部包含上述专有 blob）
- 本仓库通过 `hubv3x/fip/.gitignore` 显式忽略这些输出，以降低误提交风险。

---

## 后续计划（换机后建议优先做）

你们当前希望的最终形态是：

- **Buildroot 内部 fresh 编译 U-Boot（并使用 hubv3x 自己的 patch/config fragments）**
- legacy FIP 包仅做“打包”，从 `$(BINARIES_DIR)/u-boot.bin` 取最新 BL33，再与 SDK 的 BL2/BL30/BL31 组合生成最终 `u-boot.bin.sd.bin` 等
- 全程不在仓库中保存任何 `u-boot.bin*` 或 BL2/30/31 blob

这部分需要进一步整理 hubv3x 的 U-Boot patch/defconfig 方式（与 hubv3/hubv3a/hubv3b 不同之处），并将 `thirdreality_hubv3x_defconfig` 调整为启用 `BR2_TARGET_UBOOT` 的方式。

