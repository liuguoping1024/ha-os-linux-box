# -*- coding:utf-8 -*-

import os
import sys
import binascii
import shutil

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_eflash_loader
from libs import bflb_utils
from libs.bflb_utils import get_eflash_loader, convert_path
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
efuse_boothd_cfg = os.path.join(chip_path, chip_name, "img_create_mcu/efuse_bootheader_cfg.ini")
img_create_cfg = os.path.join(chip_path, chip_name, "img_create_mcu/img_create_cfg.ini")


def update_cfg(values):
    cfg = BFConfigParser()
    if os.path.isfile(eflash_loader_cfg_tmp) is False:
        shutil.copyfile(eflash_loader_cfg, eflash_loader_cfg_tmp)
    cfg.read(eflash_loader_cfg_tmp)
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "interface", values["dl_device"].lower())
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "device", values["dl_comport"])
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "speed_uart_load", values["dl_comspeed"])
    bflb_utils.update_cfg(cfg, "LOAD_CFG", "speed_jlink", values["dl_jlinkspeed"])
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


def program_read_id(values, callback=None):
    eflash_loader_bin = os.path.join(chip_path, chip_name,
                                     "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))
    try:
        if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
            ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
            bflb_utils.printf(ret)
            return False, ret
        bflb_utils.set_error_code("FFFF")
        update_cfg(values)
        options = ["--none", "--flash", "-c", eflash_loader_cfg_tmp]
        args = parser_eflash.parse_args(options)
        eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
        eflash_loader_t.set_config_file(efuse_boothd_cfg, img_create_cfg)
        eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
        eflash_loader_t.object_status_clear()
        ret, data = eflash_loader_t.flash_read_jedec_id_process()
        if ret:
            data = binascii.hexlify(data).decode('utf-8')
        eflash_loader_t.close_port()
        return ret, data
    except Exception as e:
        ret = str(e)
        bflb_utils.printf("error:" + ret)
        return False, ret


def program_read_reg(values, callback=None):
    eflash_loader_bin = os.path.join(chip_path, chip_name,
                                     "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))
    try:
        if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
            ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
            bflb_utils.printf(ret)
            return False, ret
        bflb_utils.set_error_code("FFFF")
        update_cfg(values)
        options = ["--none", "--flash", "-c", eflash_loader_cfg_tmp]
        args = parser_eflash.parse_args(options)
        eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
        eflash_loader_t.set_config_file(efuse_boothd_cfg, img_create_cfg)
        eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
        eflash_loader_t.object_status_clear()
        cmd = values["cmd"]
        length = int(values["len"])
        cmd_value = int(cmd, 16)
        if cmd_value != 0x05 and cmd_value != 0x35 and cmd_value != 0x15:
            eflash_loader_t.close_port()
            ret = "read register command value not recognize"
            bflb_utils.printf(ret)
            return False, ret
        if length > 3:
            eflash_loader_t.close_port()
            ret = "read register len is too long"
            bflb_utils.printf(ret)
            return False, ret
        ret, data = eflash_loader_t.flash_read_status_reg_process(cmd, length)
        if ret:
            data = binascii.hexlify(data).decode('utf-8')
        eflash_loader_t.close_port()
        return ret, data
    except Exception as e:
        ret = str(e)
        bflb_utils.printf("error:" + ret)
        return False, ret


def program_write_reg(values, callback=None):
    ret = None
    eflash_loader_bin = os.path.join(chip_path, chip_name,
                                     "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))
    try:
        if not values["dl_comport"] and values["dl_device"].lower() == "uart":
            ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
            bflb_utils.printf(ret)
            return False, ret
        if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
            ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
            bflb_utils.printf(ret)
            return False, ret
        bflb_utils.set_error_code("FFFF")
        update_cfg(values)
        options = ["--none", "--flash", "-c", eflash_loader_cfg_tmp]
        args = parser_eflash.parse_args(options)
        eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
        eflash_loader_t.set_config_file(efuse_boothd_cfg, img_create_cfg)
        eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
        eflash_loader_t.object_status_clear()
        cmd = values["cmd"]
        length = int(values["len"])
        val = values["val"]
        cmd_value = int(cmd, 16)
        if cmd_value != 0x01 and cmd_value != 0x31 and cmd_value != 0x11:
            eflash_loader_t.close_port()
            ret = "write register command value not recognize"
            bflb_utils.printf(ret)
            return False, ret
        if length > 3:
            eflash_loader_t.close_port()
            ret = "write register len is too long"
            bflb_utils.printf(ret)
            return False, ret
        ret, data = eflash_loader_t.flash_write_status_reg_process(cmd, length, val)
        eflash_loader_t.close_port()
        return ret, data
    except Exception as e:
        ret = str(e)
        bflb_utils.printf("error:" + ret)
        return False, ret
