# Kernel Module Cleanup Record

Date: 2026-02-12
Target: `kernel-linuxbox-hubv3.config`
Platform: Amlogic A113X (Meson AXG), Mali-450 MP2 GPU

Before cleanup: **4112 modules**, ~145MB
After cleanup: estimated **~3350 modules**, significantly smaller rootfs

---

## 1. GPU/DRM (146 → ~16)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_DRM_LIMA=m` | `lima.ko` | Mali-450 GPU driver (A113X) |
| `CONFIG_DRM_SIMPLEDRM=m` | `simpledrm.ko` | Framebuffer fallback |
| `CONFIG_DRM_MESON=y` | (built-in) | Meson display controller |
| `CONFIG_DRM_MESON_DW_HDMI=y` | (built-in) | HDMI output |
| `CONFIG_DRM_MESON_DW_MIPI_DSI=y` | (built-in) | MIPI DSI |
| DRM core helpers | various | Required by lima/simpledrm |

### Removed (~130 modules)

| Config Pattern | Reason |
|----------------|--------|
| `CONFIG_DRM_PANFROST` | Mali-T/G series, not compatible with Mali-450 |
| `CONFIG_DRM_PANEL_*` (59 modules) | No display panel on Hub |
| `CONFIG_DRM_*_BRIDGE_*` (~20 modules) | No display bridge chips |
| `CONFIG_DRM_HDLCD`, `CONFIG_DRM_MALI_DISPLAY` | ARM reference SoC, not Meson |
| `CONFIG_DRM_TIDSS` | TI SoC display |
| `CONFIG_DRM_KIRIN` | HiSilicon Kirin SoC |
| `CONFIG_DRM_BOCHS`, `CONFIG_DRM_HYPERV`, `CONFIG_DRM_VMWGFX` | Virtual/x86 GPU |
| `CONFIG_DRM_UDL` | USB DisplayLink |
| `CONFIG_DRM_GUD` | USB Generic display |
| `CONFIG_DRM_VIRTIO_GPU` | VirtIO GPU |
| `CONFIG_DRM_XEN` | Xen GPU |
| `CONFIG_DRM_KUNIT_TEST*` (14 modules) | DRM unit tests |
| `CONFIG_DRM_TINY_*` (except simpledrm) | Small SPI/I2C displays |
| `CONFIG_DRM_I2C_CH7006`, `CONFIG_DRM_I2C_SIL164`, `CONFIG_DRM_I2C_NXP_TDA9950` | I2C display adapters |
| `CONFIG_DRM_LOGICVC` | LogiCVC FPGA display |
| `CONFIG_DRM_SSD130X*` | SSD1306 OLED |

### Restore instructions

To restore a DRM module, change in `kernel-linuxbox-hubv3.config`:
```
# CONFIG_DRM_PANFROST is not set
```
back to:
```
CONFIG_DRM_PANFROST=m
```

---

## 2. RTC (82 → 1 module + 2 built-in)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_RTC_DRV_PL031=y` | (built-in) | ARM PrimeCell RTC, used by Meson |
| `CONFIG_RTC_DRV_MAX77686=y` | (built-in) | Already built-in, cannot remove |
| `CONFIG_RTC_DRV_MESON_VRTC=m` | `rtc-meson-vrtc.ko` | Meson virtual RTC |

### Removed (~78 modules)

All other `CONFIG_RTC_DRV_*=m` entries, including:

| Config | Chip | Reason |
|--------|------|--------|
| `CONFIG_RTC_DRV_DS1307` | Dallas DS1307 I2C RTC | Not on board |
| `CONFIG_RTC_DRV_PCF8563` | NXP PCF8563 I2C RTC | Not on board |
| `CONFIG_RTC_DRV_DS3232` | Dallas DS3232 | Not on board |
| `CONFIG_RTC_DRV_ABX80X` | Abracon AB-RTCMC | Not on board |
| `CONFIG_RTC_DRV_HYM8563` | Hynix HYM8563 | Not on board |
| ... (78 total) | Various I2C/SPI RTC chips | None present on Hub hardware |

### Restore instructions

To restore an RTC driver (e.g., if adding an external RTC module):
```
# CONFIG_RTC_DRV_DS1307 is not set
```
back to:
```
CONFIG_RTC_DRV_DS1307=m
```

---

## 3. USB Serial (52 → 8)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_USB_SERIAL_CP210X=m` | `cp210x.ko` | Silicon Labs, common Zigbee adapter |
| `CONFIG_USB_SERIAL_CH341=m` | `ch341.ko` | WCH, common cheap USB-serial |
| `CONFIG_USB_SERIAL_FTDI_SIO=m` | `ftdi_sio.ko` | FTDI, most common USB-serial |
| `CONFIG_USB_SERIAL_PL2303=m` | `pl2303.ko` | Prolific, common USB-serial |
| `CONFIG_USB_SERIAL_OPTION=m` | `option.ko` | 4G/LTE modem support |
| `CONFIG_USB_SERIAL_WWAN=m` | `usb_wwan.ko` | Wireless WAN base driver |
| `CONFIG_USB_SERIAL_SIMPLE=m` | `usb-serial-simple.ko` | Generic USB serial base |
| `CONFIG_USB_SERIAL_DEBUG=m` | `usb_debug.ko` | USB debug device support |

### Removed (~44 modules)

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_USB_SERIAL_AIRCABLE` | `aircable.ko` | AIRcable Bluetooth dongle |
| `CONFIG_USB_SERIAL_ARK3116` | `ark3116.ko` | Obsolete Arkmicro chip |
| `CONFIG_USB_SERIAL_BELKIN` | `belkin_sa.ko` | Belkin serial adapter |
| `CONFIG_USB_SERIAL_CYBERJACK` | `cyberjack.ko` | Smart card reader |
| `CONFIG_USB_SERIAL_CYPRESS_M8` | `cypress_m8.ko` | Cypress M8 chip |
| `CONFIG_USB_SERIAL_DIGI_ACCELEPORT` | `digi_acceleport.ko` | Digi AccelePort |
| `CONFIG_USB_SERIAL_EDGEPORT` | `io_edgeport.ko` | Inside Out Edgeport |
| `CONFIG_USB_SERIAL_EDGEPORT_TI` | `io_ti.ko` | Inside Out Edgeport TI |
| `CONFIG_USB_SERIAL_EMPEG` | `empeg.ko` | empeg car MP3 player |
| `CONFIG_USB_SERIAL_F81232` | `f81232.ko` | Fintek F81232 |
| `CONFIG_USB_SERIAL_F81534` | `f81534.ko` | Fintek F81534 |
| `CONFIG_USB_SERIAL_GARMIN` | `garmin_gps.ko` | Garmin GPS |
| `CONFIG_USB_SERIAL_IPAQ` | `ipaq.ko` | HP iPAQ PDA |
| `CONFIG_USB_SERIAL_IPW` | `ipw.ko` | IPWireless modem |
| `CONFIG_USB_SERIAL_IR` | `ir-usb.ko` | USB IrDA |
| `CONFIG_USB_SERIAL_IUU` | `iuu_phoenix.ko` | IUU smart card |
| `CONFIG_USB_SERIAL_KEYSPAN` | `keyspan.ko` | Keyspan serial |
| `CONFIG_USB_SERIAL_KEYSPAN_PDA` | `keyspan_pda.ko` | Keyspan PDA |
| `CONFIG_USB_SERIAL_KLSI` | `kl5kusb105.ko` | KLSI KL5KUSB105 |
| `CONFIG_USB_SERIAL_KOBIL_SCT` | `kobil_sct.ko` | KOBIL smart card |
| `CONFIG_USB_SERIAL_MCT_U232` | `mct_u232.ko` | MCT U232 |
| `CONFIG_USB_SERIAL_METRO` | `metro-usb.ko` | Metrologic barcode |
| `CONFIG_USB_SERIAL_MOS7720` | `mos7720.ko` | MosChip 7720 |
| `CONFIG_USB_SERIAL_MOS7840` | `mos7840.ko` | MosChip 7840 |
| `CONFIG_USB_SERIAL_MXUPORT` | `mxuport.ko` | MOXA UPort |
| `CONFIG_USB_SERIAL_NAVMAN` | `navman.ko` | Navman GPS |
| `CONFIG_USB_SERIAL_OMNINET` | `omninet.ko` | ZyXEL omni.net |
| `CONFIG_USB_SERIAL_OPTICON` | `opticon.ko` | Opticon barcode |
| `CONFIG_USB_SERIAL_OTI6858` | `oti6858.ko` | Ours Technology |
| `CONFIG_USB_SERIAL_QCAUX` | `qcaux.ko` | Qualcomm aux |
| `CONFIG_USB_SERIAL_QUALCOMM` | `qcserial.ko` | Qualcomm modem |
| `CONFIG_USB_SERIAL_QUATECH2` | `quatech2.ko` | Quatech serial |
| `CONFIG_USB_SERIAL_SAFE` | `safe_serial.ko` | Safe serial |
| `CONFIG_USB_SERIAL_SIERRA` | `sierra.ko` | Sierra modem |
| `CONFIG_USB_SERIAL_SPCP8X5` | `spcp8x5.ko` | Sunplus SPCP8x5 |
| `CONFIG_USB_SERIAL_SSU100` | `ssu100.ko` | Quatech SSU100 |
| `CONFIG_USB_SERIAL_SYMBOL` | `symbolserial.ko` | Symbol barcode |
| `CONFIG_USB_SERIAL_TI` | `ti_usb_3410_5052.ko` | TI USB serial |
| `CONFIG_USB_SERIAL_UPD78F0730` | `upd78f0730.ko` | Renesas |
| `CONFIG_USB_SERIAL_VISOR` | `visor.ko` | PalmOS Visor |
| `CONFIG_USB_SERIAL_WHITEHEAT` | `whiteheat.ko` | ConnectTech WhiteHEAT |
| `CONFIG_USB_SERIAL_WISHBONE` | `wishbone-serial.ko` | Wishbone bus |
| `CONFIG_USB_SERIAL_XR` | `xr_serial.ko` | MaxLinear XR |
| `CONFIG_USB_SERIAL_XSENS_MT` | `xsens_mt.ko` | Xsens motion tracker |

---

## 4. hwmon (216 → 4)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_SENSORS_PWM_FAN=m` | `pwm-fan.ko` | PWM fan control |
| `CONFIG_SENSORS_GPIO_FAN=m` | `gpio-fan.ko` | GPIO fan control |
| `CONFIG_NTC_THERMISTOR=m` | `ntc_thermistor.ko` | NTC temperature sensor |
| `CONFIG_IIO_HWMON=m` | `iio_hwmon.ko` | IIO to hwmon bridge |

### Removed (~212 modules)

All PC/server hardware monitoring chips (LM75, LM90, ADT7470, W83627, IT87, etc.)
and PMBus power supply controllers. None of these ICs are present on the Hub.

### Restore instructions

To restore a hwmon driver (e.g., if adding a temperature sensor):
```
# CONFIG_SENSORS_LM75 is not set
```
back to:
```
CONFIG_SENSORS_LM75=m
```

---

## 5. Regulator (84 → 2)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_REGULATOR_VIRTUAL_CONSUMER=m` | `virtual.ko` | Virtual regulator consumer |
| `CONFIG_REGULATOR_USERSPACE_CONSUMER=m` | `userspace-consumer.ko` | Userspace consumer |

### Removed (~82 modules)

All external PMIC/LDO regulator drivers. A113X uses fixed regulators,
no external PMIC (DA9063, TPS65910, AXP20x, etc.) is present.

---

## 6. IR Remote Control (172 → 3)

### Kept

| Config | Module | Reason |
|--------|--------|--------|
| `CONFIG_IR_MESON=m` | `meson-ir.ko` | Meson built-in IR receiver |
| `CONFIG_RC_CORE=m` | `rc-core.ko` | RC subsystem core |
| `CONFIG_IR_NEC_DECODER=m` | `ir-nec-decoder.ko` | NEC protocol (most common) |

### Removed (~169 modules)

- All `rc-*.ko` keymap modules (136 modules) - specific remote control mappings
- All other protocol decoders: `ir-rc5-decoder`, `ir-rc6-decoder`, `ir-sony-decoder`, etc.
- All USB IR receivers: `mceusb`, `igorplugusb`, `iguanair`, `imon`, `redrat3`, etc.
- `meson-ir-tx.ko` - IR transmitter (Hub has no IR LED)
- `gpio-ir-recv.ko`, `gpio-ir-tx.ko` - GPIO IR (not used)
- `serial_ir.ko` - Serial port IR

### Restore instructions

To add support for additional IR protocols:
```
# CONFIG_IR_RC5_DECODER is not set
```
back to:
```
CONFIG_IR_RC5_DECODER=m
```

To add a specific remote keymap:
```
# CONFIG_RC_MAP_xxx is not set
```
back to:
```
CONFIG_RC_MAP_xxx=m
```

---

## 7. Touchscreen (40 → 0)

### Removed (all ~40 modules)

Hub has no touchscreen. All touchscreen controller drivers removed:
`atmel_mxt_ts`, `ads7846`, `silead`, `goodix`, `ilitek_ts_i2c`, etc.

### Restore instructions

To restore (e.g., `atmel_mxt_ts`):
```
# CONFIG_TOUCHSCREEN_ATMEL_MXT is not set
```
back to:
```
CONFIG_TOUCHSCREEN_ATMEL_MXT=m
```

---

## 8. 1-Wire / drivers/w1 (5 → 0)

### Removed (all 5 modules)

| Module | Reason |
|--------|--------|
| `ds2482.ko` | Dallas I2C-to-1Wire bridge |
| `ds2490.ko` | Dallas USB-to-1Wire bridge |
| `w1_ds2780.ko` | DS2780 battery monitor |
| `w1_ds2781.ko` | DS2781 battery monitor |
| `w1-gpio.ko` | GPIO 1-Wire master |

**Note**: These are Linux 1-Wire bus protocol drivers (Dallas temperature sensors, etc.),
**NOT** related to Amlogic W1 WiFi/BT chip. The Amlogic W1 drivers are at:
- `drivers/net/wireless/w1/vmac/` (WiFi)
- `drivers/bluetooth/aml_bt/` (Bluetooth)

---

## How to apply / revert

The changes are in `buildroot-external/board/thirdreality/kernel-linuxbox-hubv3.config`.

### Full rebuild after config change

```bash
./make-buildroot-release.sh -b hubv3 clean
```

### Revert all changes

```bash
git checkout buildroot-external/board/thirdreality/kernel-linuxbox-hubv3.config
```

### Verify modules on running system

```bash
# List loaded modules
lsmod

# Check specific module
modinfo <module-name>

# Load a module manually
modprobe <module-name>
```
