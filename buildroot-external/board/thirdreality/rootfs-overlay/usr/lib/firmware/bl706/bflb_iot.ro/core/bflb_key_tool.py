# -*- coding:utf-8 -*-

import os
import sys
import shutil
import traceback

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_eflash_loader
from libs import bflb_efuse_boothd_create
from libs import bflb_utils
from libs.bflb_utils import verify_hex_num, get_eflash_loader, convert_path
from libs.bflb_configobj import BFConfigParser

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

ef_sf_aes_mode_list = ["None", "AES128", "AES192", "AES256"]


def str_endian_switch(string):
    s = string[6:8] + string[4:6] + string[2:4] + string[0:2]
    return s


def create_key_data(values):
    sub_module = __import__("libs." + chip_type, fromlist=[chip_type])
    return sub_module.efuse_create_do.create_key_data_do(values, chip_name, chip_type, efuse_cfg,
                                                         efuse_data)


def program_key_data(values, callback=None):
    ret = None
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
    try:
        options = ["--write", "--efuse", "-c", eflash_loader_cfg_tmp]
        args = parser_eflash.parse_args(options)
        eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
        ret = eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
        eflash_loader_t.object_status_clear()
    except Exception as e:
        ret = str(e)
        traceback.print_exc(limit=5, file=sys.stdout)
    finally:
        return ret
