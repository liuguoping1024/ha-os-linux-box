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

partition_path = os.path.join(chip_path, chip_name, "partition/partition.bin")
eflash_loader_bin = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_40m.bin")
eflash_loader_cfg = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_cfg.conf")
eflash_loader_cfg_tmp = os.path.join(chip_path, chip_name, "eflash_loader/eflash_loader_cfg.ini")
efuse_data = os.path.join(chip_path, chip_name, "efuse_bootheader/efusedata.bin")
efuse_data_mask = os.path.join(chip_path, chip_name, "efuse_bootheader/efusedata_mask.bin")
entry_max = 6


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


def create_partition_table(values):
    entry_table = bytearray(36 * entry_max)
    entry_cnt = 0
    for i in range(entry_max):
        entry_type = values["entry" + str(i + 1) + "_type"]
        entry_name = values["entry" + str(i + 1) + "_name"]
        entry_addr0 = values["entry" + str(i + 1) + "_addr0"]
        entry_addr1 = values["entry" + str(i + 1) + "_addr1"]
        entry_maxlen0 = values["entry" + str(i + 1) + "_maxlen0"]
        entry_maxlen1 = values["entry" + str(i + 1) + "_maxlen1"]
        if entry_type != "":
            entry_table[36 * entry_cnt + 0] = bflb_utils.int_to_2bytearray_l(int(entry_type))[0]
            if len(entry_name) >= 8:
                return "Entry name is too long!"
            entry_table[36 * entry_cnt + 3:36 * entry_cnt + 3 +
                        len(entry_name)] = bflb_utils.get_byte_array(entry_name)
            entry_table[36 * entry_cnt + 12:36 * entry_cnt + 16] = bflb_utils.int_to_4bytearray_l(
                int(entry_addr0, 16))
            entry_table[36 * entry_cnt + 16:36 * entry_cnt + 20] = bflb_utils.int_to_4bytearray_l(
                int(entry_addr1, 16))
            entry_table[36 * entry_cnt + 20:36 * entry_cnt + 24] = bflb_utils.int_to_4bytearray_l(
                int(entry_maxlen0, 16))
            entry_table[36 * entry_cnt + 24:36 * entry_cnt + 28] = bflb_utils.int_to_4bytearray_l(
                int(entry_maxlen1, 16))
            entry_cnt += 1
    # 0x54504642
    pt_table = bytearray(16)
    pt_table[0] = 0x42
    pt_table[1] = 0x46
    pt_table[2] = 0x50
    pt_table[3] = 0x54
    pt_table[6:8] = bflb_utils.int_to_2bytearray_l(int(entry_cnt))
    pt_table[12:16] = bflb_utils.get_crc32_bytearray(pt_table[0:12])
    entry_table[36 * entry_cnt:36 * entry_cnt + 4] = bflb_utils.get_crc32_bytearray(
        entry_table[0:36 * entry_cnt])
    data = pt_table + entry_table[0:36 * entry_cnt + 4]
    fp = open(partition_path, 'wb+')
    fp.write(data)
    fp.close()
    return True


def flash_partition_thread(values, action):
    eflash_loader_bin = os.path.join(chip_path, chip_name,
                                     "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))
    ret = None
    if action == "erase partition1":
        start_addr = values["p1_start_addr"]
        end_addr = hex(int(start_addr, 16) + 4 * 1024 - 1).replace("0x", "")
        update_cfg(values)
        options = [
            "--erase", "--flash", "-c", eflash_loader_cfg_tmp, "--start=" + start_addr,
            "--end=" + end_addr
        ]
    elif action == "erase partition2":
        start_addr = values["p2_start_addr"]
        end_addr = hex(int(start_addr, 16) + 4 * 1024 - 1).replace("0x", "")
        update_cfg(values)
        options = [
            "--erase", "--flash", "-c", eflash_loader_cfg_tmp, "--start=" + start_addr,
            "--end=" + end_addr
        ]
    elif action == "program":
        if create_partition_table(values) is False:
            return
        start_addr = values["p1_start_addr"]
        end_addr = hex(int(start_addr, 16) + 4 * 1024 - 1).replace("0x", "")
        update_cfg(values)
        options = [
            "--write", "--flash", "-c", eflash_loader_cfg_tmp, "--file=" + partition_path,
            "--addr=" + start_addr
        ]
    elif action == "create":
        create_partition_table(values)
        return True
    if not values["dl_comport"] and values["dl_device"].lower() == "uart":
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
        bflb_utils.printf(ret)
        return ret
    if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
        bflb_utils.printf(ret)
        return ret
    try:
        args = parser_eflash.parse_args(options)
        eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chip_name, chip_type)
        ret = eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin)
        eflash_loader_t.object_status_clear()
    except Exception as e:
        ret = str(e)
        traceback.print_exc(limit=5, file=sys.stdout)
    finally:
        return ret
