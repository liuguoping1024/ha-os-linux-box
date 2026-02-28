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


def create_sec_aes_data(values):
    tips = ""
    bflb_utils.printf("Create_Sec_Aes_data")
    fp = open(efuse_cfg, 'w+')
    fp.write("[EFUSE_CFG]\n")

    aes_mode = ef_sf_aes_mode_list.index(values["ef_sf_aes_mode"])
    fp.write("ef_sf_aes_mode = " + str(ef_sf_aes_mode_list.index(values["ef_sf_aes_mode"])) + "\n")
    if aes_mode != 0:
        fp.write("ef_cpu_enc_en = 1\n")

    if "slot_2_simple" in values.keys():
        if values["slot_2_simple"] != "":
            if verify_hex_num(values["slot_2_simple"]) is True:
                if len(values["slot_2_simple"]) == 32:
                    fp.write("ef_key_slot_2_w0 = 0x" +
                             str_endian_switch(values["slot_2_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_2_w1 = 0x" +
                             str_endian_switch(values["slot_2_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_2_w2 = 0x" +
                             str_endian_switch(values["slot_2_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_2_w3 = 0x" +
                             str_endian_switch(values["slot_2_simple"][24:32]) + "\n")
                elif len(values["slot_2_simple"]) == 16:
                    fp.write("ef_key_slot_2_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_2_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_2_w2 = 0x" +
                             str_endian_switch(values["slot_2_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_2_w3 = 0x" +
                             str_endian_switch(values["slot_2_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_2 len")
                    return "Error: Please check ef_key_slot_2 len"
                if values["slot_2_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_2 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_2 = 0\n")
                if values["slot_2_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_2 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_2 = 0\n")
                tips += "ef_key_slot_2\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_2 data")
                return "Error: Please check ef_key_slot_2 data"
    if "slot_3_simple" in values.keys():
        if values["slot_3_simple"] != "":
            if verify_hex_num(values["slot_3_simple"]) is True:
                if len(values["slot_3_simple"]) == 32:
                    fp.write("ef_key_slot_3_w0 = 0x" +
                             str_endian_switch(values["slot_3_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_3_w1 = 0x" +
                             str_endian_switch(values["slot_3_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_3_w2 = 0x" +
                             str_endian_switch(values["slot_3_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_3_w3 = 0x" +
                             str_endian_switch(values["slot_3_simple"][24:32]) + "\n")
                elif len(values["slot_3_simple"]) == 16:
                    fp.write("ef_key_slot_3_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_3_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_3_w2 = 0x" +
                             str_endian_switch(values["slot_3_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_3_w3 = 0x" +
                             str_endian_switch(values["slot_3_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_3 len")
                    return "Error: Please check ef_key_slot_3 len"
                if values["slot_3_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_3 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_3 = 0\n")
                if values["slot_3_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_3 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_3 = 0\n")
                tips += "ef_key_slot_3\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_3 data")
                return "Error: Please check ef_key_slot_3 data"
    if "slot_4_simple" in values.keys():
        if values["slot_4_simple"] != "":
            if verify_hex_num(values["slot_4_simple"]) is True:
                if len(values["slot_4_simple"]) == 32:
                    fp.write("ef_key_slot_4_w0 = 0x" +
                             str_endian_switch(values["slot_4_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_4_w1 = 0x" +
                             str_endian_switch(values["slot_4_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_4_w2 = 0x" +
                             str_endian_switch(values["slot_4_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_4_w3 = 0x" +
                             str_endian_switch(values["slot_4_simple"][24:32]) + "\n")
                elif len(values["slot_4_simple"]) == 16:
                    fp.write("ef_key_slot_4_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_4_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_4_w2 = 0x" +
                             str_endian_switch(values["slot_4_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_4_w3 = 0x" +
                             str_endian_switch(values["slot_4_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_4 len")
                    return "Error: Please check ef_key_slot_4 len"
                if chip_type == "bl602" or chip_type == "bl702":
                    if values["slot_4_wp_enable"] is True:
                        fp.write("wr_lock_key_slot_4_l = 1\n")
                        fp.write("wr_lock_key_slot_4_h = 1\n")
                    else:
                        fp.write("wr_lock_key_slot_4_l = 0\n")
                        fp.write("wr_lock_key_slot_4_h = 0\n")
                else:
                    if values["slot_4_wp_enable"] is True:
                        fp.write("wr_lock_key_slot_4 = 1\n")
                    else:
                        fp.write("wr_lock_key_slot_4 = 0\n")
                if values["slot_4_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_4 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_4 = 0\n")
                tips += "ef_key_slot_4\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_4 data")
                return "Error: Please check ef_key_slot_4 data"
    if "slot_7_simple" in values.keys():
        if values["slot_7_simple"] != "":
            if verify_hex_num(values["slot_7_simple"]) is True:
                if len(values["slot_7_simple"]) == 32:
                    fp.write("ef_key_slot_7_w0 = 0x" +
                             str_endian_switch(values["slot_7_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_7_w1 = 0x" +
                             str_endian_switch(values["slot_7_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_7_w2 = 0x" +
                             str_endian_switch(values["slot_7_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_7_w3 = 0x" +
                             str_endian_switch(values["slot_7_simple"][24:32]) + "\n")
                elif len(values["slot_7_simple"]) == 16:
                    fp.write("ef_key_slot_7_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_7_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_7_w2 = 0x" +
                             str_endian_switch(values["slot_7_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_7_w3 = 0x" +
                             str_endian_switch(values["slot_7_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_7 len")
                    return "Error: Please check ef_key_slot_7 len"
                if values["slot_7_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_7 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_7 = 0\n")
                if values["slot_7_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_7 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_7 = 0\n")
                tips += "ef_key_slot_7\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_7 data")
                return "Error: Please check ef_key_slot_7 data"
    if "slot_8_simple" in values.keys():
        if values["slot_8_simple"] != "":
            if verify_hex_num(values["slot_8_simple"]) is True:
                if len(values["slot_8_simple"]) == 32:
                    fp.write("ef_key_slot_8_w0 = 0x" +
                             str_endian_switch(values["slot_8_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_8_w1 = 0x" +
                             str_endian_switch(values["slot_8_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_8_w2 = 0x" +
                             str_endian_switch(values["slot_8_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_8_w3 = 0x" +
                             str_endian_switch(values["slot_8_simple"][24:32]) + "\n")
                elif len(values["slot_8_simple"]) == 16:
                    fp.write("ef_key_slot_8_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_8_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_8_w2 = 0x" +
                             str_endian_switch(values["slot_8_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_8_w3 = 0x" +
                             str_endian_switch(values["slot_8_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_8 len")
                    return "Error: Please check ef_key_slot_8 len"
                if values["slot_8_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_8 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_8 = 0\n")
                if values["slot_8_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_8 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_8 = 0\n")
                tips += "ef_key_slot_8\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_8 data")
                return "Error: Please check ef_key_slot_8 data"
    if "slot_9_simple" in values.keys():
        if values["slot_9_simple"] != "":
            if verify_hex_num(values["slot_9_simple"]) is True:
                if len(values["slot_9_simple"]) == 32:
                    fp.write("ef_key_slot_9_w0 = 0x" +
                             str_endian_switch(values["slot_9_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_9_w1 = 0x" +
                             str_endian_switch(values["slot_9_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_9_w2 = 0x" +
                             str_endian_switch(values["slot_9_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_9_w3 = 0x" +
                             str_endian_switch(values["slot_9_simple"][24:32]) + "\n")
                elif len(values["slot_9_simple"]) == 16:
                    fp.write("ef_key_slot_9_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_9_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_9_w2 = 0x" +
                             str_endian_switch(values["slot_9_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_9_w3 = 0x" +
                             str_endian_switch(values["slot_9_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_9 len")
                    return "Error: Please check ef_key_slot_9 len"
                if values["slot_9_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_9 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_9 = 0\n")
                if values["slot_9_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_9 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_9 = 0\n")
                tips += "ef_key_slot_9\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_9 data")
                return "Error: Please check ef_key_slot_9 data"
    if "slot_10_simple" in values.keys():
        if values["slot_10_simple"] != "":
            if verify_hex_num(values["slot_10_simple"]) is True:
                if len(values["slot_10_simple"]) == 32:
                    fp.write("ef_key_slot_10_w0 = 0x" +
                             str_endian_switch(values["slot_10_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_10_w1 = 0x" +
                             str_endian_switch(values["slot_10_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_10_w2 = 0x" +
                             str_endian_switch(values["slot_10_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_10_w3 = 0x" +
                             str_endian_switch(values["slot_10_simple"][24:32]) + "\n")
                elif len(values["slot_10_simple"]) == 16:
                    fp.write("ef_key_slot_10_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_10_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_10_w2 = 0x" +
                             str_endian_switch(values["slot_10_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_10_w3 = 0x" +
                             str_endian_switch(values["slot_10_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_10 len")
                    return "Error: Please check ef_key_slot_10 len"
                if values["slot_10_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_10 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_10 = 0\n")
                if values["slot_10_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_10 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_10 = 0\n")
                tips += "ef_key_slot_10\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_10 data")
                return "Error: Please check ef_key_slot_10 data"
    if "slot_11_simple" in values.keys():
        if values["slot_11_simple"] != "":
            if verify_hex_num(values["slot_11_simple"]) is True:
                if len(values["slot_11_simple"]) == 32:
                    fp.write("ef_key_slot_11_w0 = 0x" +
                             str_endian_switch(values["slot_11_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_11_w1 = 0x" +
                             str_endian_switch(values["slot_11_simple"][8:16]) + "\n")
                    fp.write("ef_key_slot_11_w2 = 0x" +
                             str_endian_switch(values["slot_11_simple"][16:24]) + "\n")
                    fp.write("ef_key_slot_11_w3 = 0x" +
                             str_endian_switch(values["slot_11_simple"][24:32]) + "\n")
                elif len(values["slot_11_simple"]) == 16:
                    fp.write("ef_key_slot_11_w0 = 0x00000000\n")
                    fp.write("ef_key_slot_11_w1 = 0x00000000\n")
                    fp.write("ef_key_slot_11_w2 = 0x" +
                             str_endian_switch(values["slot_11_simple"][0:8]) + "\n")
                    fp.write("ef_key_slot_11_w3 = 0x" +
                             str_endian_switch(values["slot_11_simple"][8:16]) + "\n")
                else:
                    bflb_utils.printf("Error: Please check ef_key_slot_11 len")
                    return "Error: Please check ef_key_slot_11 len"
                if values["slot_11_wp_enable"] is True:
                    fp.write("wr_lock_key_slot_11 = 1\n")
                else:
                    fp.write("wr_lock_key_slot_11 = 0\n")
                if values["slot_11_rp_enable"] is True:
                    fp.write("rd_lock_key_slot_11 = 1\n")
                else:
                    fp.write("rd_lock_key_slot_11 = 0\n")
                tips += "ef_key_slot_11\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_key_slot_11 data")
                return "Error: Please check ef_key_slot_11 data"
    if "usage_1_simple" in values.keys():
        if values["usage_1_simple"] != "":
            if values["usage_1_simple"][0:2] != "0x" and values["usage_1_simple"][0:2] != "0X":
                bflb_utils.printf("Error: usage_1_simple is HEX data, must begin with 0x")
                return
            if len(values["usage_1_simple"]) == 10 and verify_hex_num(
                    values["usage_1_simple"][2:]) is True:
                fp.write("ef_sw_usage_1 = 0x" + str_endian_switch(values["usage_1_simple"][2:10]) +
                         "\n")
                if values["usage_1_wp_enable"] is True:
                    fp.write("wr_lock_sw_usage_1 = 1\n")
                else:
                    fp.write("wr_lock_sw_usage_1 = 0\n")
                tips += "ef_sw_usage_1\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_sw_usage_1 data and len")
                return "Error: Please check ef_sw_usage_1 data and len"
    if "usage_2_simple" in values.keys():
        if values["usage_2_simple"] != "":
            if values["usage_2_simple"][0:2] != "0x" and values["usage_2_simple"][0:2] != "0X":
                bflb_utils.printf("Error: usage_2_simple is HEX data, must begin with 0x")
                return
            if len(values["usage_2_simple"]) == 10 and verify_hex_num(
                    values["usage_2_simple"][2:]) is True:
                fp.write("ef_sw_usage_2 = 0x" + str_endian_switch(values["usage_2_simple"][2:10]) +
                         "\n")
                if values["usage_2_wp_enable"] is True:
                    fp.write("wr_lock_sw_usage_2 = 1\n")
                else:
                    fp.write("wr_lock_sw_usage_2 = 0\n")
                tips += "ef_sw_usage_2\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_sw_usage_2 data and len")
                return "Error: Please check ef_sw_usage_2 data and len"
    if "usage_3_simple" in values.keys():
        if values["usage_3_simple"] != "":
            if values["usage_3_simple"][0:2] != "0x" and values["usage_3_simple"][0:2] != "0X":
                bflb_utils.printf("Error: usage_3_simple is HEX data, must begin with 0x")
                return
            if len(values["usage_3_simple"]) == 10 and verify_hex_num(
                    values["usage_3_simple"][2:]) is True:
                fp.write("ef_sw_usage_3 = 0x" + str_endian_switch(values["usage_3_simple"][2:10]) +
                         "\n")
                if values["usage_3_wp_enable"] is True:
                    fp.write("wr_lock_sw_usage_3 = 1\n")
                else:
                    fp.write("wr_lock_sw_usage_3 = 0\n")
                tips += "ef_sw_usage_3\r\n"
            else:
                bflb_utils.printf("Error: Please check ef_sw_usage_3 data and len")
                return "Error: Please check ef_sw_usage_3 data and len"

    # lines = len(tips.split("\r\n")) + 1
    bflb_utils.printf("Following will be burned:\r\n" + tips)
    fp.close()
    bflb_efuse_boothd_create.efuse_create_process(chip_name, chip_type, efuse_cfg, efuse_data)


def program_sec_aes_data(values, callback=None):
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
    if values["dl_chiperase"] == "True":
        bflb_utils.update_cfg(cfg, "LOAD_CFG", "erase", "2")
    else:
        bflb_utils.update_cfg(cfg, "LOAD_CFG", "erase", "1")
    if "dl_verify" in values.keys():
        if values["dl_verify"] == "True":
            bflb_utils.update_cfg(cfg, "LOAD_CFG", "verify", "1")
        else:
            bflb_utils.update_cfg(cfg, "LOAD_CFG", "verify", "0")
    # specify the efuse files created by Create_sec_aes_data
    bflb_utils.update_cfg(cfg, "EFUSE_CFG", "file",
                          convert_path(os.path.relpath(efuse_data, app_path)))
    bflb_utils.update_cfg(cfg, "EFUSE_CFG", "maskfile",
                          convert_path(os.path.relpath(efuse_data_mask, app_path)))
    cfg.write(eflash_loader_cfg_tmp, "w+")
    if not values["dl_comport"] and values["dl_device"].lower() == "uart":
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
        bflb_utils.printf(ret)
        return ret
    if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
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
