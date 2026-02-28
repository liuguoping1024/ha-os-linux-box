# -*- coding:utf-8 -*-

import os
import sys
import shutil

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_utils
from libs import bflb_eflash_loader
from libs import bflb_efuse_boothd_create
from libs.bflb_configobj import BFConfigParser
from libs.bflb_utils import get_eflash_loader, convert_path

chip_name = gol.type_chip[0]
chip_type = gol.type_chip[1]

parser_eflash = bflb_utils.eflash_loader_parser_init()

# Get app path
if getattr(sys, "frozen", False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chip_path = os.path.join(app_path, "chips")

eflash_loader_bin = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_40m.bin")
eflash_loader_cfg = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_cfg.conf")
eflash_loader_cfg_tmp = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_cfg.ini")
efuse_data = os.path.join(chip_path, chip_name, "efuse_bootheader/efusedata.bin")
efuse_data_mask = os.path.join(chip_path, chip_name, "efuse_bootheader/efusedata_mask.bin")
efuse_cfg = os.path.join(chip_path, chip_name, "efuse_bootheader/eflash_cfg.ini")

ef_flash_psram_info_list = ["NoMemory", "1M Flash", "2M Flash", "PSRAM"]
ef_pack_info_list = ["QFN40", "QFN56"]
sdio_pin_sel_list = ["GPIO16-21", "GPIO0-5"]
ef_wifi_mcu_info_list = ["WiFi", "MCU"]
ef_core_info_list = ["DualCore", "SingleCore"]
external_flash_list = ["Embedded Swap", "Embedded NoSwap", "GPIO0-5", "GPIO22-23,37-40"]
ef_dbg_mode_list = ["Open", "Password", "Close"]
ef_sf_aes_mode_list = ["None", "AES128", "AES192", "AES256"]
xtal_type_list = ["XTAL_None", "XTAL_32M", "XTAL_38.4M", "XTAL_40M", "XTAL_26M", "XTAL_52M"]
pll_clk_list = ["50M", "120M", "160M", "192M"]
vddio_18_user_ctrl_list = ["Default", "1.8V(VDDCPU)", "1.8V(VDDIO)", "3.3V(VDDCPU)"]


def create_img(values):
    fp = open(efuse_cfg, 'w+')
    fp.write("[EFUSE_CFG]\n")
    # basic check
    fp.write("ef_flash_psram_info = " +
             str(ef_flash_psram_info_list.index(values["ef_flash_psram_info"])) + "\n")
    fp.write("ef_pack_info = " + str(ef_pack_info_list.index(values["ef_pack_info"])) + "\n")
    fp.write("sdio_pin_sel = " + str(sdio_pin_sel_list.index(values["sdio_pin_sel"])) + "\n")

    fp.write("ef_wifi_mcu_info = " + str(ef_wifi_mcu_info_list.index(values["ef_wifi_mcu_info"])) +
             "\n")
    fp.write("ef_core_info = " + str(ef_core_info_list.index(values["ef_core_info"])) + "\n")
    fp.write("external_flash = " + str(external_flash_list.index(values["external_flash"])) + "\n")

    if values["ef_dbg_mode"] == "Open":
        fp.write("ef_dbg_mode = 0\n")
    elif values["ef_dbg_mode"] == "Password":
        fp.write("ef_dbg_mode = 3\n")
    if values["ef_dbg_mode"] == "Close":
        fp.write("ef_dbg_mode = 15\n")
    fp.write("ef_sf_aes_mode = " + str(ef_sf_aes_mode_list.index(values["ef_sf_aes_mode"])) + "\n")
    fp.write("xtal_type = " + str(xtal_type_list.index(values["xtal_type"])) + "\n")

    fp.write("pll_clk = " + str(pll_clk_list.index(values["pll_clk"])) + "\n")
    if values["pll_clk"] == "50M":
        fp.write("hclk_div = 0\n")
        fp.write("bclk_div = 0\n")
    else:
        fp.write("hclk_div = 0\n")
        fp.write("bclk_div = 1\n")
    if values["vddio_18_user_ctrl"] == "Default":
        fp.write("vddio_18_user_ctrl = 0\n")
        fp.write("vddio_18_sw1 = 0\n")
        fp.write("vddio_18_sw2 = 0\n")
        fp.write("vddio_18_sw3 = 0\n")
        fp.write("vddio_18_bypass = 0\n")
    if values["vddio_18_user_ctrl"] == "1.8V(VDDCPU)":
        fp.write("vddio_18_user_ctrl = 1\n")
        fp.write("vddio_18_sw1 = 0\n")
        fp.write("vddio_18_sw2 = 1\n")
        fp.write("vddio_18_sw3 = 0\n")
        fp.write("vddio_18_bypass = 0\n")
    if values["vddio_18_user_ctrl"] == "1.8V(VDDIO)":
        fp.write("vddio_18_user_ctrl = 1\n")
        fp.write("vddio_18_sw1 = 1\n")
        fp.write("vddio_18_sw2 = 0\n")
        fp.write("vddio_18_sw3 = 0\n")
        fp.write("vddio_18_bypass = 0\n")
    if values["vddio_18_user_ctrl"] == "3.3V(VDDCPU)":
        fp.write("vddio_18_user_ctrl = 1\n")
        fp.write("vddio_18_sw1 = 0\n")
        fp.write("vddio_18_sw2 = 1\n")
        fp.write("vddio_18_sw3 = 0\n")
        fp.write("vddio_18_bypass = 1\n")

    if values["ef_dbg_jtag_dis"] is True:
        fp.write("ef_dbg_jtag_dis = 3\n")
    else:
        fp.write("ef_dbg_jtag_dis = 0\n")

    if values["ef_sw_sf_dis"] is True:
        fp.write("ef_sw_sf_dis = 1\n")
    else:
        fp.write("ef_sw_sf_dis = 0\n")

    if values["ef_sw_cam_dis"] is True:
        fp.write("ef_sw_cam_dis = 1\n")
    else:
        fp.write("ef_sw_cam_dis = 0\n")

    if values["ef_sboot_en"] is True:
        fp.write("ef_sboot_en = 15\n")
    else:
        fp.write("ef_sboot_en = 0\n")

    if values["ef_sboot_sign_mode"] is True:
        fp.write("ef_sboot_sign_mode = 1\n")
    else:
        fp.write("ef_sboot_sign_mode = 0\n")

    if values["bootrom_protect"] is True:
        fp.write("bootrom_protect = 1\n")
    else:
        fp.write("bootrom_protect = 0\n")

    if values["uart_disable"] is True:
        fp.write("uart_disable = 1\n")
    else:
        fp.write("uart_disable = 0\n")

    if values["jtag_switch"] is True:
        fp.write("jtag_switch = 1\n")
    else:
        fp.write("jtag_switch = 0\n")

    if values["tz_boot"] is True:
        fp.write("tz_boot = 1\n")
    else:
        fp.write("tz_boot = 0\n")

    if values["encryped_with_sign"] is True:
        fp.write("encryped_with_sign = 1\n")
    else:
        fp.write("encryped_with_sign = 0\n")

    if values["mediaboot_disable"] is True:
        fp.write("mediaboot_disable = 1\n")
    else:
        fp.write("mediaboot_disable = 0\n")

    if values["uartboot_disable"] is True:
        fp.write("uartboot_disable = 1\n")
    else:
        fp.write("uartboot_disable = 0\n")

    if values["sdioboot_disable"] is True:
        fp.write("sdioboot_disable = 1\n")
    else:
        fp.write("sdioboot_disable = 0\n")

    if values["keep_dbg_port_closed"] is True:
        fp.write("keep_dbg_port_closed = 1\n")
    else:
        fp.write("keep_dbg_port_closed = 0\n")

    if values["hbn_check_sign"] is True:
        fp.write("hbn_check_sign = 1\n")
    else:
        fp.write("hbn_check_sign = 0\n")

    fp.close()
    bflb_efuse_boothd_create.efuse_create_process(efuse_cfg, efuse_data)


def program_img_thread(values):
    eflash_loader_bin = os.path.join(chip_path, chip_name,
                                     "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))
    # create eflash_loader_cfg.ini
    cfg = BFConfigParser()
    if os.path.isfile(eflash_loader_cfg_tmp) is False:
        shutil.copyfile(eflash_loader_cfg, eflash_loader_cfg_tmp)
    cfg.read(eflash_loader_cfg_tmp)
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "interface", values["dl_device"].lower())
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "device", values["dl_comport"])
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "speed_uart_load", values["dl_comspeed"])
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "speed_jlink", values["dl_jlinkspeed"])
    if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
        bflb_utils.printf(ret)
        return ret
    if values["dl_chiperase"] == "True":
        bflb_utils.update_cfg(cfg, "LOAD_CFG", "erase", "2")
    else:
        bflb_utils.update_cfg(cfg, "LOAD_CFG", "erase", "1")
    if "dl_verify" in values.keys():
        if values["dl_verify"] == "True":
            bflb_utils.update_cfg(cfg, "LOAD_CFG", "verify", "1")
        else:
            bflb_utils.update_cfg(cfg, "LOAD_CFG", "verify", "0")
    # specify the efuse files created by Create_key_data
    bflb_utils.update_cfg(cfg, "EFUSE_CFG", "file",
                          convert_path(os.path.relpath(efuse_data, app_path)))
    bflb_utils.update_cfg(cfg, "EFUSE_CFG", "maskfile",
                          convert_path(os.path.relpath(efuse_data_mask, app_path)))
    cfg.write(eflash_loader_cfg_tmp, "w+")
    if not values["dl_comport"] and values["dl_device"].lower() == "uart":
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
        bflb_utils.printf(ret)
        return ret
    options = ["--write", "--efuse", "-c", eflash_loader_cfg_tmp]
    args = parser_eflash.parse_args(options)
    eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
    eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
    eflash_loader_t.object_status_clear()
