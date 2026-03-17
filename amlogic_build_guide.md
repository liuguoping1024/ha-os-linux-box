# Amlogic A113X SDK (AXG S420) 编译指南

> 项目：SENSI V3 Kernel 5.4  
> SDK 基线日期：2022年10月  
> 文档生成日期：2025-03-17

---

## 1. 版本信息总览

| 组件 | 版本 | 路径 |
|------|------|------|
| **Buildroot** | 2020.02.1 | `buildroot/` |
| **Linux Kernel** | 5.4.180 (amlogic-5.4-dev) | `kernel/aml-5.4/` |
| **U-Boot (BL33)** | 2015.01 (Amlogic 定制) | `bootloader/uboot-repo/bl33/v2015/` |
| **U-Boot Host Tools** | 2020.01 | `buildroot/package/uboot-tools/` |
| **SWUpdate** | 2019.11 | `buildroot/package/swupdate/` |
| **SoC 平台** | AXG (A113X) | — |
| **目标板** | axg_s420_v1 | — |
| **用户空间工具链** | GCC ARM 10.3-2021.07 (arm-none-linux-gnueabihf) | `toolchain/gcc/linux-x86/arm/` |
| **内核工具链** | GCC ARM 10.2-2020.11 (aarch64-none-linux-gnu) | `toolchain/gcc/linux-x86/aarch64/` |
| **U-Boot 工具链** | gcc-linaro-7.5.0-2019.12 (aarch64-elf) | `/opt/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-elf/` |

---

## 2. 编译环境准备

### 2.1 系统要求

- **操作系统**: Ubuntu 20.04 LTS
- **依赖包**:

```bash
sudo apt-get install build-essential bash bc binutils bzip2 cpio \
    diffutils file findutils gawk gcc g++ gzip make ncurses-dev \
    patch perl python3 rsync sed tar unzip wget python-is-python3 \
    device-tree-compiler libssl-dev u-boot-tools zip
```

### 2.2 工具链设置

U-Boot 编译需要额外的交叉编译器，不包含在 SDK 中：

```bash
# U-Boot BL2/BL31 编译工具链
export PATH=/opt/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-elf/bin/:$PATH
export PATH=/opt/CodeSourcery/Sourcery_G++_Lite/bin/:$PATH
export PATH=/opt/gcc-linaro-aarch64-none-elf-4.8-2013.11_linux/bin/:$PATH

# 如果机器上有 CUDA，避免链接冲突
export LD_LIBRARY_PATH=/usr/local/cuda-12.3/lib64
```

### 2.3 获取代码

```bash
git clone https://3reality.tech/gogs/SENSI_V3/sdk_A113X_202210.git
cd sdk_A113X_202210
git checkout sensi_v3_bolom  # 或目标分支
```

---

## 3. 编译流程

### 3.1 一键编译（推荐）

```bash
cd sdk_A113X_202210

# 设置环境并选择目标配置
source setenv.sh axg_s420_a6432_k54_release

# 全量编译（kernel + uboot + rootfs + 打包）
make
```

`setenv.sh` 接受配置名作为参数（不含 `_defconfig` 后缀），也可以不带参数进入交互选择菜单。

### 3.2 独立编译各模块

```bash
# 仅重新编译 U-Boot
make uboot-rebuild

# 仅重新编译 Linux Kernel
make linux-rebuild

# 查看所有可用编译目标
make show-targets

# 使用 runCompile.sh（封装脚本）
source buildroot/build/runCompile.sh           # 全量编译
source buildroot/build/runCompile.sh uboot     # 仅 uboot
source buildroot/build/runCompile.sh kernel    # 仅 kernel
```

### 3.3 输出目录结构

编译产物位于 `output/axg_s420_a6432_k54_release/`：

```
output/axg_s420_a6432_k54_release/
├── build/          # 各个包的编译目录
├── host/           # host 工具（mkimage, fip_create 等）
├── staging/        # sysroot（头文件、库）
├── target/         # 目标文件系统
└── images/         # 最终镜像输出
    ├── u-boot.bin                    # 完整 bootloader 镜像
    ├── u-boot.bin.encrypt            # 加密版 bootloader
    ├── u-boot.bin.usb.bl2            # USB 烧录用 BL2
    ├── u-boot.bin.usb.tpl            # USB 烧录用 TPL（BL30+BL31+BL33）
    ├── u-boot.bin.sd.bin             # SD 卡烧录用
    ├── boot.img                      # kernel + ramdisk (Android 格式)
    ├── dtb.img                       # 设备树合集
    ├── rootfs.ubi                    # UBI 根文件系统
    ├── rootfs.ubifs                  # UBIFS 根文件系统
    ├── rootfs.cpio.uboot            # initramfs (uImage 格式)
    ├── software.swu                  # SWUpdate 升级包
    ├── aml_upgrade_package.img       # USB 烧录完整镜像
    ├── Image.gz                      # 压缩内核
    ├── axg_s420.dtb                  # 设备树
    ├── recovery.img                  # recovery 镜像
    └── logo.img                      # 开机 logo
```

---

## 4. Defconfig 配置层次

SDK 使用分层的 `#include` 机制组合配置：

```
axg_s420_a6432_k54_release_defconfig         ← 顶层 defconfig
  ├── arch_a6432_10.2_10.3.config            ← 架构 + 工具链（ARM 32位用户空间，64位内核）
  ├── a113_s420_k54.config                   ← S420 板级配置
  │   └── a113_speaker_k54.config            ← Speaker 通用配置
  │       └── a113_base_k54.config           ← A113 基础配置（kernel/uboot 路径定义）
  │           └── base_aml.config            ← Amlogic Buildroot 基础配置
  │       ├── network_driver_k5.4.config
  │       ├── alsa.config
  │       ├── adb.config
  │       ├── network_app.config
  │       ├── tools.config
  │       ├── gst_audio.config
  │       ├── swupdate.config                ← SWUpdate 相关
  │       ├── speaker_app.config
  │       └── ...
  └── flash_nand_4k.config                   ← NAND Flash 配置
```

### 关键配置值

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `BR2_TARGET_UBOOT_BOARDNAME` | `axg_s420_v1` | U-Boot 板级名称 |
| `BR2_TARGET_UBOOT_PLATFORM` | `axg` | SoC 平台名称 |
| `BR2_LINUX_KERNEL_DEFCONFIG` | `meson64_a64_smarthome` | Kernel defconfig |
| `BR2_LINUX_KERNEL_INTREE_DTS_NAME` | `axg_s420 axg_s420_v03 axg_s420_1g` | 设备树列表 |
| `BR2_TARGET_BOARD_PLATFORM` | `mesonaxg` | 平台标识 |
| `BR2_ARM_KERNEL_64` | `y` | 64位内核 + 32位用户空间 |

---

## 5. Bootloader (FIP) 打包流程详解

### 5.1 Amlogic Boot 架构

Amlogic AXG 平台的启动链：

```
ROM → BL2 (SPL/DDR init) → BL30 (SCP) → BL31 (ATF/EL3) → BL32 (OP-TEE, 可选) → BL33 (U-Boot)
```

| 组件 | 说明 | 来源 | 大小限制 |
|------|------|------|----------|
| **BL2** | 第二阶段引导程序（DDR 初始化） | `bl2/bin/` 或 `bl2/src/` (bootloader/spl) | 41984 bytes |
| **BL21** | BL2 扩展 | 编译自 `bl33/v2015/arch/arm/cpu/armv8/axg/firmware/bl21/` | 7168 bytes |
| **BL30** | SCP (System Control Processor) 固件 | `bl30/bin/` 或 `bl30/src/` (firmware/scp) | 40960 bytes |
| **BL301** | BL30 扩展（电源管理等） | 编译自 `bl33/v2015/build/scp_task/` | 13312 bytes |
| **BL31** | ARM Trusted Firmware (ATF) | `bl31/bin/` 或 `bl31/src/` (ARM-software/arm-trusted-firmware) | — |
| **BL32** | OP-TEE（可选） | `bl32/bin/` 或 `bl32/src/` (OP-TEE/optee_os) | — |
| **BL33** | U-Boot 主程序 | `bootloader/uboot-repo/bl33/v2015/` | — |

### 5.2 FIP 打包脚本入口

```
bootloader/uboot-repo/mk                         ← 入口脚本
  └── source fip/mk_script.sh                    ← 主构建逻辑
       ├── source fip/variables.sh               ← 全局变量
       ├── source fip/lib.sh                     ← 工具函数
       ├── source fip/build_bl2.sh               ← BL2 编译
       ├── source fip/build_bl30.sh              ← BL30 编译
       ├── source fip/build_bl31.sh              ← BL31 编译
       ├── source fip/build_bl32.sh              ← BL32 编译
       ├── source fip/build_bl33.sh              ← BL33 (U-Boot) 编译
       └── source fip/axg/build.sh               ← AXG SoC 特定打包
            └── package() → build_fip() → encrypt()
```

### 5.3 完整打包过程（AXG 平台）

**Step 1: 预编译 U-Boot 获取配置**

```bash
# pre_build_uboot: 编译 U-Boot 的 .config，获取 CONFIG_SYS_SOC 等变量
# 决定 CUR_SOC=axg
```

**Step 2: 编译 BL33 (U-Boot)**

```bash
# build_uboot(): 使用 axg_s420_v1_defconfig 编译 U-Boot
# 工具链: gcc-linaro-7.5.0 aarch64-elf
# 输出: bl33/v2015/build/u-boot.bin
```

**Step 3: 获取/编译其他 BLx 固件**

```bash
# 默认从 bl2/bin/, bl30/bin/, bl31/bin/, bl32/bin/ 目录获取预编译二进制
# 也可以通过 --update-bl2 等参数从源码编译
# BL21: bl33/v2015/build/<board>/firmware/bl21.bin
# BL301: bl33/v2015/build/scp_task/bl301.bin
# ACS: bl33/v2015/build/<board>/firmware/acs.bin
```

**Step 4: build_fip() — 合并固件**

```
1. fix_blx(bl30):
   bl30.bin (≤40960B) + 零填充 → bl30_zero.bin
   bl301.bin (≤13312B) + 零填充 → bl301_zero.bin
   bl30_zero.bin + bl301_zero.bin → bl30_new.bin

2. acs_tool:
   bl2.bin → bl2_acs.bin (提取 DDR timing) + acs.bin

3. fix_blx(bl2):
   bl2_acs.bin (≤41984B) + 零填充 → bl2_zero.bin
   bl21.bin (≤7168B) + 零填充 → bl21_zero.bin
   bl2_zero.bin + bl21_zero.bin → bl2_new.bin

4. fip_create:
   --bl30 bl30_new.bin --bl31 bl31.img [--bl32 bl32.img] --bl33 bl33.bin
   → fip.bin

5. cat:
   bl2_new.bin + fip.bin → boot_new.bin
```

**Step 5: encrypt() — 加密签名**

```
1. 对每个 BLx 进行签名/加密:
   aml_encrypt_axg --bl3sig  (v3) 或 --bl3enc (v2)
   → bl30_new.bin.enc, bl31.img.enc, bl32.img.enc, bl33.bin.enc

2. BL2 签名:
   aml_encrypt_axg --bl2sig → bl2.n.bin.sig

3. 最终组装:
   aml_encrypt_axg --bootmk \
     --bl2 bl2.n.bin.sig \
     --bl30 bl30_new.bin.enc \
     --bl31 bl31.img.enc \
     --bl33 bl33.bin.enc \
     → u-boot.bin

4. 可选：Secure Boot 加密:
   aml_encrypt_axg --bootsig → u-boot.bin.encrypt
```

**Step 6: 拆分生成烧录文件**

```
u-boot.bin           → 完整 bootloader
u-boot.bin.usb.bl2   → BL2 部分（USB 烧录）
u-boot.bin.usb.tpl   → TPL 部分（BL30+BL31+BL33）
u-boot.bin.sd.bin    → SD 卡烧录格式
```

### 5.4 独立编译 Bootloader

```bash
cd bootloader/uboot-repo

# 基本编译
./mk axg_s420_v1

# 使用源码编译 BL31
./mk axg_s420_v1 --update-bl31

# 指定外部 BL2
./mk axg_s420_v1 --bl2 path/to/bl2.bin

# 编译所有 BLx 源码
./mk axg_s420_v1 --update-bl2 --update-bl31 --update-bl32
```

### 5.5 关键工具

| 工具 | 路径 | 说明 |
|------|------|------|
| `fip_create` | `fip/fip_create` | FIP 镜像组装 |
| `aml_encrypt_axg` | `fip/axg/aml_encrypt_axg` | AXG 加密/签名工具 |
| `acs_tool.pyc` | `fip/acs_tool.pyc` | DDR ACS 参数提取 |
| `ddr_parse` | `fip/tools/ddr_parse/` | DDR 参数解析 |
| `sign.sh` | `fip/stool/sign.sh` | Secure Boot 签名 |

### 5.6 DDR 双片支持（老版本特性）

在此 SDK 版本中，BL2 通过读取 U-Boot (BL33) 中的 DDR timing 配置来支持双片 DDR：

- **DDR timing 定义**: `bl33/v2015/board/amlogic/axg_s420_v1/firmware/timing.c`
  - `__ddr_timming[]`: DDR3/DDR4/LPDDR 时序表
  - `__ddr_setting`: 通道数、类型、频率、地址映射等
- **ACS 提取**: `acs_tool.pyc` 从编译后的 `bl2.bin` 中提取 DDR 配置生成 `acs.bin`
- **BL2 读取**: BL2 启动时读取 ACS 参数，根据 `__ddr_setting` 中的通道配置支持单/双片 DDR

> **重要说明**: 新一代 U-Boot (2024.01) 的 BL2 不再通过这种方式接受来自 BL33 的 DDR 参数。
> 新版本的 DDR 初始化流程更加独立，BL2 与 BL33 之间的耦合已被解除。

---

## 6. Linux Kernel 编译

### 6.1 Kernel 配置

| 项 | 值 |
|----|-----|
| 版本 | 5.4.180 |
| 源码路径 | `kernel/aml-5.4/` |
| Defconfig | `meson64_a64_smarthome_defconfig` |
| 设备树 | `arch/arm64/boot/dts/amlogic/axg_s420.dts` 等 |
| 输出格式 | `Image.gz` → Android boot.img (via `mkbootimg`) |
| 加载地址 | `0x1008000` |

### 6.2 独立编译 Kernel

```bash
# 通过 Buildroot
make linux-rebuild

# 手动编译
cd kernel/aml-5.4
export ARCH=arm64
export CROSS_COMPILE=<toolchain-path>/aarch64-none-linux-gnu-
make meson64_a64_smarthome_defconfig
make Image.gz dtbs -j$(nproc)
```

### 6.3 设备树

设备树文件位于 `kernel/aml-5.4/arch/arm64/boot/dts/amlogic/`：

- `axg_s420.dts` — 标准版
- `axg_s420_v03.dts` — V03 硬件版本
- `axg_s420_1g.dts` — 1GB DDR 版本
- `mesonaxg.dtsi` — AXG SoC 通用定义

---

## 7. 烧录镜像打包

### 7.1 USB 烧录镜像

`aml_upgrade_package.img` 由 `aml_image_v2_packer_new` 工具根据 `aml_upgrade_package.conf` 打包生成：

```ini
# aml_upgrade_package.conf 关键内容
[LIST_NORMAL]
file="u-boot.bin.usb.bl2"   main_type="USB"        sub_type="DDR"
file="u-boot.bin.usb.tpl"   main_type="USB"        sub_type="UBOOT"
file="u-boot.bin.sd.bin"    main_type="UBOOT"      sub_type="aml_sdc_burn"
file="platform.conf"        main_type="conf"       sub_type="platform"
file="aml_sdc_burn.ini"     main_type="ini"        sub_type="aml_sdc_burn"
file="dtb.img"              main_type="dtb"        sub_type="meson1"

[LIST_VERIFY]
file="boot.img"             main_type="PARTITION"  sub_type="boot"
file="recovery.img"         main_type="PARTITION"  sub_type="recovery"
file="rootfs.ubi"           main_type="PARTITION"  sub_type="system"
file="u-boot.bin"           main_type="PARTITION"  sub_type="bootloader"
file="dtb.img"              main_type="PARTITION"  sub_type="_aml_dtb"
```

### 7.2 打包命令

```bash
# 由 buildroot 的 ext2.mk / cpio.mk 自动调用
aml_image_v2_packer_new -r aml_upgrade_package.conf <images_dir>/ <output>.img
```

---

## 8. SWU 升级包创建

### 8.1 SWUpdate 简介

SDK 使用 SWUpdate (2019.11) 作为 OTA 升级框架，支持：

- 本地 USB 升级
- 网络 OTA 升级
- AWS IoT 集成 FOTA

### 8.2 sw-description 格式

`sw-description` 定义了升级包的内容和目标分区：

```
software = {
    version = "1.0.1";
    hardware-compatibility: [ "1.0" ];
    images: (
        { filename = "rootfs.ubifs";      volume = "rootfs"; },
        { filename = "dtb.img";           device = "/dev/dtb"; },
        { filename = "boot.img";          device = "/dev/mtd5"; type = "flash"; },
        { filename = "u-boot.bin.usb.bl2"; device = "/dev/mtd0"; type = "flash"; },
        { filename = "u-boot.bin.usb.tpl"; device = "/dev/mtd1"; type = "flash"; }
    );
    scripts: (
        { filename = "update.sh"; type = "shellscript"; },
        { filename = "3r_upgrade.sh"; type = "shellscript"; }
    );
};
```

BL2 写入 `/dev/mtd0` 的多个 offset（0, 256K, 512K, ...1792K），TPL 写入 `/dev/mtd1` 的多个 offset（0, 2M, 4M, 6M），确保冗余。

### 8.3 SWU 包构建流程

SWU 包由 `ota_package_create.sh` 生成：

```bash
# 由 Buildroot post-image 脚本自动调用
# 手动生成：
cd output/axg_s420_a6432_k54_release/images/

# Step 1: 计算各文件 SHA256 并插入 sw-description
for i in $HASH_FILES; do
    sha256sum $i → 插入到 sw-description 对应 filename 下
done

# Step 2: 用私钥签名 sw-description
openssl dgst -sha256 -sign swupdate-priv.pem sw-description > sw-description.sig

# Step 3: 打包成 CPIO 格式的 .swu 文件
# 注意: sw-description 必须是第一个文件
echo "sw-description sw-description.sig $FILES" | cpio -ov -H crc > software.swu
```

### 8.4 增量更新包

SDK 还支持增量更新（increment update）：

```bash
# 生成增量更新 zip 包
mkdir target_ota_<timestamp>
cp $HASH_FILES target_ota_<timestamp>/
tar -C <ota_target_dir> -czf target_ota_<timestamp>/rootfs.tgz .
cp sw-description-increment → sw-description
cp increment_update.sh → update.sh
zip target_ota_<timestamp>.zip target_ota_<timestamp>/
```

---

## 9. NAND Flash 分区布局（AXG）

根据 `sw-description` 和 `aml_upgrade_package.conf`，NAND 分区布局：

| MTD 设备 | 内容 | 说明 |
|----------|------|------|
| `/dev/mtd0` | BL2 (SPL) | 多份冗余（0~1792K，每份 256K） |
| `/dev/mtd1` | TPL (BL30+BL31+BL33) | 多份冗余（0, 2M, 4M, 6M） |
| `/dev/dtb` | DTB | 设备树 |
| `/dev/mtd5` | boot.img | kernel + initramfs |
| `rootfs` | rootfs.ubifs | UBI volume |

---

## 10. 关键目录结构

```
sdk_A113X_202210/
├── Makefile                     → buildroot/build/Makefile
├── setenv.sh                    → buildroot/build/setenv.sh
├── bootloader/
│   └── uboot-repo/
│       ├── mk                   ← Bootloader 编译入口
│       ├── fip/                 ← FIP 打包脚本与工具
│       │   ├── mk_script.sh     ← 主逻辑
│       │   ├── variables.sh     ← 全局变量
│       │   ├── lib.sh
│       │   ├── build_bl{2,30,31,32,33,40}.sh
│       │   ├── fip_create       ← FIP 组装工具
│       │   ├── acs_tool.pyc     ← DDR ACS 提取
│       │   ├── axg/             ← AXG 平台特定
│       │   │   ├── build.sh     ← 打包 + 加密
│       │   │   ├── aml_encrypt_axg  ← 加密工具
│       │   │   └── variable_soc.sh
│       │   └── stool/sign.sh    ← 签名工具
│       └── bl33/
│           └── v2015/           ← U-Boot 2015.01 源码
│               ├── board/amlogic/axg_s420_v1/
│               │   ├── axg_s420_v1.c
│               │   └── firmware/timing.c  ← DDR timing
│               ├── board/amlogic/configs/axg_s420_v1.h
│               └── board/amlogic/defconfigs/axg_s420_v1_defconfig
├── kernel/
│   └── aml-5.4/                 ← Linux 5.4.180
│       └── arch/arm64/boot/dts/amlogic/axg_s420*.dts
├── buildroot/                   ← Buildroot 2020.02.1
│   ├── configs/
│   │   ├── axg_s420_a6432_k54_release_defconfig
│   │   └── amlogic/             ← 分层配置
│   ├── board/amlogic/
│   │   ├── common/
│   │   │   ├── upgrade/upgrade-axg/   ← 烧录配置
│   │   │   └── ota/swu/              ← SWU 创建脚本
│   │   └── mesonaxg_s420/             ← 板级 overlay
│   └── package/
│       ├── swupdate/            ← SWUpdate 2019.11
│       └── amlogic/             ← Amlogic 定制包
├── toolchain/                   ← 交叉编译工具链
├── multimedia/                  ← 音频 HAL 等
├── vendor/                      ← 供应商包
├── hardware/                    ← 硬件相关
└── output/                      ← 编译输出
```

---

## 11. 与新版本 (Linux 6.6 / U-Boot 2024.01) 的差异分析

### 11.1 BL2 差异

| 特性 | 老版本 (本SDK) | 新版本 (2024.01) |
|------|---------------|-----------------|
| DDR 参数传递 | BL2 从 BL33 (U-Boot) 的 `timing.c` 提取 ACS 参数 | BL2 独立管理 DDR 参数，不依赖 BL33 |
| 双片 DDR | 通过 `__ddr_setting` 中的通道配置支持 | 需要在 BL2 层面独立配置 |
| ACS 工具 | `acs_tool.pyc` 从 bl2.bin 提取 | 不适用或使用新工具链 |
| FIP 格式 | 旧格式 (fip_create) | 新格式 (可能使用 fiptool/cert_create) |

### 11.2 BL31 差异

| 特性 | 老版本 | 新版本 |
|------|--------|--------|
| ATF 版本 | v1.0/v1.3 | v2.x |
| 安全启动 | v2/v3 流程 | 更新的安全启动链 |

### 11.3 U-Boot 差异

| 特性 | 老版本 (2015.01) | 新版本 (2024.01) |
|------|-----------------|-----------------|
| 配置系统 | 混合 (header + Kconfig) | 纯 Kconfig |
| DM (驱动模型) | 部分支持 | 全面 DM |
| Boot 流程 | 传统 | FIT Image / 标准 boot |
| SPL | Amlogic 定制 | 可能使用标准 SPL |

### 11.4 Linux 6.6 兼容性评估

**可行性**: **有条件可行，但需要大量适配工作**

1. ✅ **Linux 6.6 内核可以运行在 AXG 上** — 上游 mainline Linux 已对 AXG (A113X) 有基本支持
2. ⚠️ **本项目的 U-Boot (2015.01) + Linux 6.6** — 理论上可行，因为 U-Boot 只负责加载内核，但：
   - 需要更新 DTB 以匹配 6.6 的 DTS binding 变化
   - 老 U-Boot 的 boot 命令可能需要调整
3. ⚠️ **本项目的 BL2/BL31 + 新 U-Boot** — 问题较大：
   - 老版 BL2 期望特定格式的 BL33 参数传递
   - 新 U-Boot 不再提供兼容的 `timing.c` / ACS 接口
4. ❌ **新版 BL2 + 本项目 U-Boot** — 不兼容，接口已变化

---

## 附录 A: 快速参考命令

```bash
# 完整编译
source setenv.sh axg_s420_a6432_k54_release && make

# 清理
make clean

# 单独编译 bootloader（在 bootloader/uboot-repo/ 下）
./mk axg_s420_v1

# 生成 USB 烧录镜像
# (由 make 自动完成，使用 aml_image_v2_packer_new)

# 生成 SWU 包
# (由 make 自动完成，运行 ota_package_create.sh)
```

## 附录 B: 环境变量参考

```bash
# 必须的 PATH 设置
export PATH=/opt/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-elf/bin/:$PATH
export PATH=/opt/CodeSourcery/Sourcery_G++_Lite/bin/:$PATH
export PATH=/opt/gcc-linaro-aarch64-none-elf-4.8-2013.11_linux/bin/:$PATH

# Buildroot 设置（由 setenv.sh 自动配置）
TARGET_OUTPUT_DIR=output/axg_s420_a6432_k54_release
TARGET_BUILD_CONFIG=axg_s420_a6432_k54_release
TARGET_BUILD_TYPE=32  # 32位用户空间
```
