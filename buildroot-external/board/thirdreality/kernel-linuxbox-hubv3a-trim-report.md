# HubV3A Linux Kernel Config Trim Report

**Date:** 2026-02-28 (updated 2026-03-10)
**Target:** ThirdReality HubV3A (A113X, 1GB RAM)
**Purpose:** Reduce kernel memory footprint for embedded use
**Reference:** Amlogic official SDK kernel 5.4 config for A113X

## Summary

| Metric | Value |
|--------|-------|
| Configs enabled before | 5438 |
| Configs enabled after  | 4484 |
| Total disabled         | **958** |
| Value changed (m→y etc)| **11** |
| Re-enabled (post-trim) | **4** (EROFS_FS, EROFS_FS_ZIP, USB Audio MIDI V2, EROFS compression) |

## Boot Parameters Optimization

| Parameter | Old | New | Savings |
|-----------|-----|-----|---------|
| `swiotlb` | 8M | 4 slabs (8KB) | **~8 MB** |

## Disabled by Category

| Category | Count |
|----------|-------|
| ACPI | 34 |
| DRM/Display/Framebuffer | 40 |
| Sound/Audio | 279 |
| Security/Audit | 31 |
| Netfilter/nftables/Traffic Control | 145 |
| Filesystem | 35 |
| DM/RAID | 26 |
| HID/Input | 129 |
| USB Serial/Net | 38 |
| Crypto | 93 |
| I2C | 58 |
| SPI | 31 |
| Cgroup/BPF/Debug | 11 |
| HugeTLB/THP | 3 |
| Other | 5 |
| **Total** | **958** |

## Key Design Decisions

### Aligned with Amlogic Official SDK
- No ACPI (ARM embedded, not x86)
- No NUMA
- No HUGETLB / Transparent Hugepages
- No EFI
- No SELinux / SMACK / TOMOYO (disabled all heavy LSMs)
- No XFS / BTRFS / F2FS (only ext4 + squashfs + overlayfs + FAT + EROFS)
- No nftables (iptables only, matching official SDK)
- No BPF_SYSCALL (embedded device, no eBPF needed)
- Minimal I2C (only Meson), minimal SPI (only Meson)
- No PCI I2C controllers, no USB-to-I2C adapters
- No USB serial adapters, no USB net adapters
- No SoC audio codecs (SND_SOC_*, SND_MESON_*)
- No FRAMEBUFFER_CONSOLE
- DRM_MESON disabled

### Built-in (=y) for Boot-Critical Components
- `CONFIG_ZRAM=y` (was =m) — needed early for /var
- `CONFIG_BLK_DEV_DM=y` (was =m) — device-mapper core
- `CONFIG_DM_VERITY=y` (was =m) — HA OS rootfs verification
- `CONFIG_DM_BUFIO=y` (was =m) — DM buffer I/O
- `CONFIG_DM_BIO_PRISON=y` (was =m)
- `CONFIG_DM_PERSISTENT_DATA=y` (was =m)

### Memory Layout Optimizations
- `CONFIG_ARCH_FORCE_MAX_ORDER=9` (was 10) — max contiguous alloc 2MB, reduces buddy allocator overhead
- `CONFIG_CMA_AREAS=4` (was 7) — fewer CMA regions
- `CONFIG_CMA_SIZE_MBYTES=4` — minimal CMA (headless hub)
- `CONFIG_NODES_SHIFT=0` (was 2) — no NUMA
- `swiotlb=4` (was 8M) — A113X RAM fully below 4GB, bounce buffer unnecessary

### EROFS Root Filesystem (re-enabled after boot failure)
- `CONFIG_EROFS_FS=y` — HA OS root partition uses compressed EROFS
- `CONFIG_EROFS_FS_ZIP=y` — compression support (LZ4/LZMA/DEFLATE/ZSTD)
- Initially disabled during trim, caused kernel panic (`error -95 EOPNOTSUPP`)

### Kept for Hardware Requirements
- `CONFIG_PREEMPT=y` — full preemption (embedded responsiveness)
- `CONFIG_MAC80211=y` — WiFi (required)
- `CONFIG_CFG80211=y` — WiFi configuration
- `CONFIG_BT=y` — Bluetooth
- `CONFIG_SOUND=m` + `CONFIG_SND_USB_AUDIO=m` — USB Audio support
- `CONFIG_SCSI=y` + `CONFIG_USB_STORAGE=y` — USB storage
- `CONFIG_OVERLAY_FS=y` — OverlayFS
- `CONFIG_SQUASHFS=y` — SquashFS (HA OS)
- `CONFIG_EROFS_FS=y` — EROFS (HA OS root partition)
- `CONFIG_SERIAL_MESON=y` — Meson UART
- `CONFIG_I2C_MESON=y` — Meson I2C
- `CONFIG_PINCTRL_MESON_AXG=y` — AXG GPIO/Pinctrl
- `CONFIG_CRYPTO_DEV_AMLOGIC_GXL=y` — HW crypto accelerator

## Critical Configs Preserved

- `CONFIG_SCSI=y` — USB storage support
- `CONFIG_USB_STORAGE=y` — USB mass storage
- `CONFIG_DM_VERITY=y` — dm-verity (HA OS, now built-in)
- `CONFIG_OVERLAY_FS=y` — OverlayFS
- `CONFIG_SQUASHFS=y` — SquashFS
- `CONFIG_EROFS_FS=y` — EROFS (root filesystem)
- `CONFIG_EROFS_FS_ZIP=y` — Compressed EROFS
- `CONFIG_EXT4_FS=y` — ext4 filesystem
- `CONFIG_FAT_FS=y` — FAT filesystem
- `CONFIG_VFAT_FS=y` — VFAT filesystem
- `CONFIG_FUSE_FS=y` — FUSE
- `CONFIG_TMPFS=y` — tmpfs
- `CONFIG_ZRAM=y` — zram (now built-in)
- `CONFIG_SWAP=y` — Swap support
- `CONFIG_ZSWAP=y` — zswap (compressed swap cache)
- `CONFIG_CMA=y` — Contiguous Memory Allocator
- `CONFIG_PREEMPT=y` — Full preemption
- `CONFIG_BT=y` — Bluetooth
- `CONFIG_CFG80211=y` — WiFi (cfg80211)
- `CONFIG_MAC80211=y` — WiFi (mac80211)
- `CONFIG_SOUND=m` — Sound subsystem
- `CONFIG_SND_USB_AUDIO=m` — USB Audio
- `CONFIG_I2C_MESON=y` — Meson I2C controller
- `CONFIG_SERIAL_MESON=y` — Meson UART
- `CONFIG_PINCTRL_MESON_AXG=y` — AXG pin control
- `CONFIG_MMC=y` — MMC/eMMC
- `CONFIG_CRYPTO_DEV_AMLOGIC_GXL=y` — Amlogic HW crypto

## Value Changes

| Config | Old | New | Reason |
|--------|-----|-----|--------|
| `CONFIG_BLK_DEV_DM` | m | y | DM core, needed for dm-verity |
| `CONFIG_DM_BIO_PRISON` | m | y | DM dependency |
| `CONFIG_DM_BUFIO` | m | y | DM buffer I/O |
| `CONFIG_DM_PERSISTENT_DATA` | m | y | DM dependency |
| `CONFIG_DM_VERITY` | m | y | HA OS rootfs verification |
| `CONFIG_NODES_SHIFT` | 2 | 0 | No NUMA needed |
| `CONFIG_SND_USB_AUDIO_MIDI_V2` | n | y | USB Audio MIDI v2 support |
| `CONFIG_ZRAM` | m | y | Boot-critical, needed for /var zram |
| `CONFIG_ARCH_FORCE_MAX_ORDER` | 10 | 9 | Reduce buddy allocator overhead (max 2MB contiguous) |
| `CONFIG_CMA_AREAS` | 7 | 4 | Fewer CMA regions needed |
| `CONFIG_EROFS_FS` | disabled→y | y | HA OS root partition uses compressed EROFS |

## Re-enabled After Initial Trim

| Config | Reason |
|--------|--------|
| `CONFIG_EROFS_FS=y` | Root partition uses EROFS; kernel panic without it |
| `CONFIG_EROFS_FS_ZIP=y` | Root partition uses compressed EROFS |
| `CONFIG_EROFS_FS_ZIP_LZMA=y` | EROFS LZMA compression algorithm |
| `CONFIG_EROFS_FS_ZIP_DEFLATE=y` | EROFS DEFLATE compression algorithm |
| `CONFIG_EROFS_FS_ZIP_ZSTD=y` | EROFS ZSTD compression algorithm |
| `CONFIG_SOUND=m` | USB Audio support (initially disabled) |
| `CONFIG_SND_USB_AUDIO=m` | USB Audio device support |
| `CONFIG_SND_USB_AUDIO_MIDI_V2=y` | USB Audio MIDI v2 |
| `CONFIG_SND_USB_AUDIO_USE_MEDIA_CONTROLLER=y` | USB Audio media controller |

## Measured Results (1GB device)

### Memory Usage Comparison

| Metric | Before Trim | After Trim | Improvement |
|--------|-------------|------------|-------------|
| MemTotal | 982720 kB | 985244 kB | +2.5 MB |
| MemAvailable | 758276 kB | 839508 kB | **+79 MB** |
| Used | 218 MB | 142 MB | **-76 MB** |
| Slab | ~60 MB | 40 MB | -20 MB |
| SUnreclaim | ~40 MB | 29 MB | -11 MB |
| Kernel code | ~20 MB | 12 MB | **-8 MB** |

### vs Amlogic Official SDK (256MB device)

| Metric | SDK (256MB) | Our Kernel (1GB) |
|--------|-------------|-----------------|
| Memory overhead ratio | 12% (31/256 MB) | **6%** (62/1024 MB) |
| Kernel code size | 20.4 MB | **12 MB** |
| Slab total | 46.7 MB | **39.3 MB** |
| CMA | 12 MB | **4 MB** |

## Expected Impact

- **Kernel image size reduction:** ~8MB smaller than original (12MB vs ~20MB)
- **Runtime memory savings:** ~80MB additional available memory
- **swiotlb savings:** ~8MB (reduced from 8M to 4 slabs)
- **Buddy allocator savings:** ~2-4MB (ARCH_FORCE_MAX_ORDER 10→9)
- **Faster boot:** ZRAM/DM built-in avoids module loading delay
- **Lower attack surface:** no nftables, no BPF_SYSCALL, no heavy LSMs

## Detailed Disabled Configs

### ACPI (34 items)

| Config | Previous Value |
|--------|---------------|
| `CONFIG_ACPI_AC` | y |
| `CONFIG_ACPI_ALS` | m |
| `CONFIG_ACPI_APEI_EINJ` | y |
| `CONFIG_ACPI_APEI_GHES` | y |
| `CONFIG_ACPI_APEI_MEMORY_FAILURE` | y |
| `CONFIG_ACPI_APEI_SEA` | y |
| `CONFIG_ACPI_APMT` | y |
| `CONFIG_ACPI_BATTERY` | y |
| `CONFIG_ACPI_BUTTON` | y |
| `CONFIG_ACPI_CCA_REQUIRED` | y |
| `CONFIG_ACPI_CPPC_CPUFREQ` | m |
| `CONFIG_ACPI_CPPC_CPUFREQ_FIE` | y |
| `CONFIG_ACPI_CPPC_LIB` | y |
| `CONFIG_ACPI_FAN` | y |
| `CONFIG_ACPI_GENERIC_GSI` | y |
| `CONFIG_ACPI_GTDT` | y |
| `CONFIG_ACPI_HED` | y |
| `CONFIG_ACPI_I2C_OPREGION` | y |
| `CONFIG_ACPI_IORT` | y |
| `CONFIG_ACPI_MCFG` | y |
| `CONFIG_ACPI_MDIO` | y |
| `CONFIG_ACPI_PCC` | y |
| `CONFIG_ACPI_PPTT` | y |
| `CONFIG_ACPI_PRMT` | y |
| `CONFIG_ACPI_PROCESSOR` | y |
| `CONFIG_ACPI_PROCESSOR_IDLE` | y |
| `CONFIG_ACPI_REDUCED_HARDWARE_ONLY` | y |
| `CONFIG_ACPI_SPCR_TABLE` | y |
| `CONFIG_ACPI_TABLE_LIB` | y |
| `CONFIG_ACPI_TABLE_UPGRADE` | y |
| `CONFIG_ACPI_THERMAL` | y |
| `CONFIG_ACPI_VIDEO` | m |
| `CONFIG_ACPI_WATCHDOG` | y |
| `CONFIG_I2C_HID_ACPI` | m |

*(Remaining detailed categories unchanged — see diff file for full details)*
