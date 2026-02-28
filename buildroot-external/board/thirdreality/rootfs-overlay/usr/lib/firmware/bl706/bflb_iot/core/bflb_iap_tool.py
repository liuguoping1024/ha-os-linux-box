# -*- coding:utf-8 -*-

import re
import os
import sys
import time
import shutil
import argparse
import traceback
import threading

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_eflash_loader
from libs import bflb_efuse_boothd_create
from libs import bflb_img_create
from libs import bflb_flash_select
from libs import bflb_utils
from libs.bflb_utils import get_eflash_loader, get_serial_ports, convert_path
from libs.bflb_configobj import BFConfigParser
from libs.bflb_utils import serial_enumerate
from libs.bflb_interface_uart import BflbUartPort
import libs.bflb_pt_creater as partition

parser_eflash = bflb_utils.eflash_loader_parser_init()
parser_image = bflb_utils.image_create_parser_init()

# Get app path
if getattr(sys, "frozen", False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(app_path)
chip_path = os.path.join(app_path, "chips")

try:
    import changeconf as cgc
    conf_sign = True
except ImportError:
    conf_sign = False


class BflbIapTool(object):

    def __init__(self, chipname="bl60x", chiptype="bl60x"):
        self.chiptype = chiptype
        self.chipname = chipname
        self.config = {}
        self.efuse_load_en = False
        self.eflash_loader_cfg = os.path.join(chip_path, chipname,
                                              "eflash_loader/eflash_loader_cfg.conf")
        self.eflash_loader_cfg_tmp = os.path.join(chip_path, chipname,
                                                  "eflash_loader/eflash_loader_cfg.ini")
        self.img_create_path = os.path.join(chip_path, chipname, "img_create_mcu")
        self.efuse_bh_path = os.path.join(chip_path, chipname, "efuse_bootheader")
        self.efuse_bh_default_cfg = os.path.join(chip_path, chipname,
                                                 "efuse_bootheader") + "/efuse_bootheader_cfg.conf"
        self.img_create_cfg_org = os.path.join(chip_path, chipname,
                                               "img_create_mcu") + "/img_create_cfg.conf"
        self.img_create_cfg = os.path.join(chip_path, chipname,
                                           "img_create_mcu") + "/img_create_cfg.ini"
        if not os.path.exists(self.img_create_path):
            os.makedirs(self.img_create_path)
        if os.path.isfile(self.eflash_loader_cfg_tmp) is False:
            shutil.copyfile(self.eflash_loader_cfg, self.eflash_loader_cfg_tmp)
        if os.path.isfile(self.img_create_cfg) is False:
            shutil.copyfile(self.img_create_cfg_org, self.img_create_cfg)

        self.xtal_type = gol.xtal_type[chiptype]
        self.xtal_type_ = gol.xtal_type_[chiptype]
        self.pll_clk = gol.pll_clk[chiptype]
        self.encrypt_type = gol.encrypt_type[chiptype]
        self.key_sel = gol.key_sel[chiptype]
        self.sign_type = gol.sign_type[chiptype]
        self.cache_way_disable = gol.cache_way_disable[chiptype]
        self.flash_clk_type = gol.flash_clk_type[chiptype]
        self.crc_ignore = gol.crc_ignore[chiptype]
        self.hash_ignore = gol.hash_ignore[chiptype]
        self.img_type = gol.img_type[chiptype]
        self.boot_src = gol.boot_src[chiptype]
        self.eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chipname, chiptype)
        self.uart_dev = BflbUartPort()
        self.timer = None

    def bl_create_flash_default_data(self, length):
        datas = bytearray(length)
        for i in range(length):
            datas[i] = 0xff
        return datas

    def bl_get_file_data(self, files):
        datas = []
        for file in files:
            with open(os.path.join(app_path, file), 'rb') as fp:
                data = fp.read()
            datas.append(data)
        return datas

    def eflash_loader_thread(self,
                             args,
                             eflash_loader_bin=None,
                             callback=None,
                             create_img_callback=None):
        ret = None
        try:
            bflb_utils.set_error_code("FFFF")
            ret = self.eflash_loader_t.efuse_flash_loader(args, None, eflash_loader_bin, callback,
                                                          None, create_img_callback)
            self.eflash_loader_t.object_status_clear()
        except Exception as e:
            traceback.print_exc(limit=5, file=sys.stdout)
            ret = str(e)
        finally:
            return ret

    def bind_img(self, values):
        error = None
        # decide file name
        try:
            if values["img_type"] == "SingleCPU":
                bootinfo_file = self.img_create_path + "/bootinfo.bin"
                img_file = self.img_create_path + "/img.bin"
                img_output_file = self.img_create_path + "/whole_img.bin"
            elif values["img_type"] == "BLSP_Boot2":
                bootinfo_file = self.img_create_path + "/bootinfo_blsp_boot2.bin"
                img_file = self.img_create_path + "/img_blsp_boot2.bin"
                img_output_file = self.img_create_path + "/whole_img_blsp_boot2.bin"
            elif values["img_type"] == "CPU0":
                bootinfo_file = self.img_create_path + "/bootinfo_cpu0.bin"
                img_file = self.img_create_path + "/img_cpu0.bin"
                img_output_file = self.img_create_path + "/whole_img_cpu0.bin"
            elif values["img_type"] == "CPU1":
                bootinfo_file = self.img_create_path + "/bootinfo_cpu1.bin"
                img_file = self.img_create_path + "/img_cpu1.bin"
                img_output_file = self.img_create_path + "/whole_img_cpu1.bin"
            if values["img_type"] == "SingleCPU":
                dummy_data = bytearray(8192)
            else:
                dummy_data = bytearray(4096)
            for i in range(len(dummy_data)):
                dummy_data[i] = 0xff
            fp = open(bootinfo_file, 'rb')
            data0 = fp.read() + bytearray(0)
            fp.close()
            fp = open(img_file, 'rb')
            data1 = fp.read() + bytearray(0)
            fp.close()
            fp = open(img_output_file, 'wb+')
            fp.write(data0 + dummy_data[0:len(dummy_data) - len(data0)] + data1)
            fp.close()
            bflb_utils.printf("Output:", img_output_file)
        except Exception as e:
            bflb_utils.printf("烧写执行出错：", e)
            error = str(e)
        return error

    def create_default_img(self, chipname, chiptype, values):
        if "encrypt_type" in values.keys():
            if "encrypt_key" in values.keys():
                if values["encrypt_type"] != "None" and values["encrypt_key"] == "":
                    error = "Please set AES key"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0064")
                    return bflb_utils.errorcode_msg()
            if "aes_iv" in values.keys():
                if values["encrypt_type"] != "None" and values["aes_iv"] == "":
                    error = "Please set AES IV"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0065")
                    return bflb_utils.errorcode_msg()
        if "sign_type" in values.keys():
            if "public_key_cfg" in values.keys():
                if values["sign_type"] != "None" and values["public_key_cfg"] == "":
                    error = "Please set public key"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0066")
                    return bflb_utils.errorcode_msg()
            if "private_key_cfg" in values.keys():
                if values["sign_type"] != "None" and values["private_key_cfg"] == "":
                    error = "Please set private key"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0067")
                    return bflb_utils.errorcode_msg()

        section = "BOOTHEADER_CFG"
        bh_cfg_file = self.img_create_path + "/efuse_bootheader_cfg.ini"
        bh_file = self.img_create_path + "/bootheader.bin"
        bootinfo_file = self.img_create_path + "/bootinfo.bin"
        img_output_file = self.img_create_path + "/img.bin"
        boot2_bootinfo_file = self.img_create_path + "/bootinfo_blsp_boot2.bin"
        boot2_img_output_file = self.img_create_path + "/img_blsp_boot2.bin"
        efuse_file = self.img_create_path + "/efusedata.bin"
        efuse_mask_file = self.img_create_path + "/efusedata_mask.bin"
        img_create_section = "Img_Cfg"
        if os.path.isfile(bh_cfg_file) is False:
            bflb_utils.copyfile(self.efuse_bh_default_cfg, bh_cfg_file)
        bflb_utils.copyfile(self.img_create_cfg_org, self.img_create_cfg)

        # add flash cfg
        if os.path.exists(self.eflash_loader_cfg_tmp):
            cfg1 = BFConfigParser()
            cfg1.read(self.eflash_loader_cfg_tmp)
            if cfg1.has_option("FLASH_CFG", "flash_id"):
                flash_id = cfg1.get("FLASH_CFG", "flash_id")
                self.eflash_loader_t.set_config_file(bh_cfg_file, self.img_create_cfg)
                if bflb_flash_select.update_flash_cfg(chipname, chiptype, flash_id, bh_cfg_file,
                                                      False, section) is False:
                    error = "flash_id:" + flash_id + " do not support"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0069")
                    return bflb_utils.errorcode_msg()
            else:
                error = "Do not find flash_id in eflash_loader_cfg.ini"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0070")
                return bflb_utils.errorcode_msg()
        else:
            bflb_utils.printf("Config file not found")
            bflb_utils.set_error_code("000B")
            return bflb_utils.errorcode_msg()
        # update config
        cfg = BFConfigParser()
        cfg.read(bh_cfg_file)
        for itrs in cfg.sections():
            bflb_utils.printf(itrs)
            if itrs != section and itrs != "EFUSE_CFG":
                cfg.delete_section(itrs)
        cfg.write(bh_cfg_file, "w+")
        cfg = BFConfigParser()
        cfg.read(bh_cfg_file)
        if chiptype == "bl702":
            bflb_utils.update_cfg(cfg, section, "boot2_enable", "0")
        if "xtal_type" in values.keys():
            bflb_utils.update_cfg(cfg, section, "xtal_type",
                                  self.xtal_type_.index(values["xtal_type"]))
        if "pll_clk" in values.keys():
            if chiptype == "bl602":
                if values["pll_clk"] == "160M":
                    bflb_utils.update_cfg(cfg, section, "pll_clk", "4")
                    bflb_utils.update_cfg(cfg, section, "bclk_div", "1")
            elif chiptype == "bl702":
                if values["pll_clk"] == "144M":
                    bflb_utils.update_cfg(cfg, section, "pll_clk", "4")
                    bflb_utils.update_cfg(cfg, section, "bclk_div", "1")
            elif chiptype == "bl60x":
                if values["pll_clk"] == "160M":
                    bflb_utils.update_cfg(cfg, section, "pll_clk", "2")
                    bflb_utils.update_cfg(cfg, section, "bclk_div", "1")
        if "flash_clk_type" in values.keys():
            if chiptype == "bl602":
                if values["flash_clk_type"] == "XTAL":
                    bflb_utils.update_cfg(cfg, section, "flash_clk_type", "1")
                    bflb_utils.update_cfg(cfg, section, "flash_clk_div", "0")
                    # Set flash clock delay = 1T
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_delay", "1")
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_invert", "0x01")
            elif chiptype == "bl702":
                if values["flash_clk_type"] == "XCLK":
                    bflb_utils.update_cfg(cfg, section, "flash_clk_type", "1")
                    bflb_utils.update_cfg(cfg, section, "flash_clk_div", "0")
                    # Set flash clock delay = 1T
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_delay", "1")
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_invert", "0x01")
            elif chiptype == "bl60x":
                if values["flash_clk_type"] == "XTAL":
                    bflb_utils.update_cfg(cfg, section, "flash_clk_type", "4")
                    bflb_utils.update_cfg(cfg, section, "flash_clk_div", "0")
                    # Set flash clock delay = 1T
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_delay", "1")
                    bflb_utils.update_cfg(cfg, section, "sfctrl_clk_invert", "0x01")

        if "sign_type" in values.keys():
            bflb_utils.update_cfg(cfg, section, "sign", self.sign_type.index(values["sign_type"]))
        if "encrypt_type" in values.keys():
            tmp = self.encrypt_type.index(values["encrypt_type"])
            bflb_utils.update_cfg(cfg, section, "encrypt_type", tmp)
            if tmp == 1 and len(values["encrypt_key"]) != 32:
                error = "Key length error"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0071")
                return bflb_utils.errorcode_msg()
            if tmp == 2 and len(values["encrypt_key"]) != 64:
                error = "Key length error"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0071")
                return bflb_utils.errorcode_msg()
            if tmp == 3 and len(values["encrypt_key"]) != 48:
                error = "Key length error"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0071")
                return bflb_utils.errorcode_msg()
            if tmp != 0:
                if len(values["aes_iv"]) != 32:
                    error = "AES IV length error"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0072")
                    return bflb_utils.errorcode_msg()
                if values["aes_iv"].endswith("00000000") is False:
                    error = "AES IV should endswith 4 bytes zero"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0073")
                    return bflb_utils.errorcode_msg()
        if "key_sel" in values.keys():
            bflb_utils.update_cfg(cfg, section, "key_sel", self.key_sel.index(values["key_sel"]))
        if "cache_way_disable" in values.keys():
            bflb_utils.update_cfg(
                cfg, section, "cache_way_disable",
                (1 << self.cache_way_disable.index(values["cache_way_disable"])) - 1)
        # boot2 bootheader set crc/hash ignore
        if "crc_ignore" in values.keys():
            bflb_utils.update_cfg(cfg, section, "crc_ignore", "1")
        if "hash_ignore" in values.keys():
            bflb_utils.update_cfg(cfg, section, "hash_ignore", "1")

        # any value except 0 is ok
        bflb_utils.update_cfg(cfg, section, "img_len", "0x100")
        bflb_utils.update_cfg(cfg, section, "img_start", "0x2000")
        cfg.write(bh_cfg_file, "w+")
        bflb_efuse_boothd_create.bootheader_create_process(
            chipname, chiptype, bh_cfg_file, bh_file,
            self.img_create_path + "/bootheader_dummy.bin")
        # create efuse data
        if self.chiptype == "bl602" or self.chiptype == "bl702":
            efuse_data = bytearray(128)
        else:
            efuse_data = bytearray(256)
        fp = open(efuse_file, 'wb+')
        fp.write(efuse_data)
        fp.close()
        fp = open(efuse_mask_file, 'wb+')
        fp.write(efuse_data)
        fp.close()
        # create img_create_cfg.ini
        img_cfg = BFConfigParser()
        img_cfg.read(self.img_create_cfg)
        bflb_utils.update_cfg(img_cfg, img_create_section, "boot_header_file", bh_file)
        bflb_utils.update_cfg(img_cfg, img_create_section, "efuse_file", efuse_file)
        bflb_utils.update_cfg(img_cfg, img_create_section, "efuse_mask_file", efuse_mask_file)
        # create segheader
        segheader = bytearray(12)
        segheader[0:4] = bflb_utils.int_to_4bytearray_l(
            int(values["img_addr"].replace("0x", ""), 16))
        segfp = open(self.img_create_path + "/segheader_tmp.bin", 'wb+')
        segfp.write(segheader)
        segfp.close()
        bflb_utils.update_cfg(img_cfg, img_create_section, "segheader_file",
                              self.img_create_path + "/segheader_tmp.bin")
        bflb_utils.update_cfg(img_cfg, img_create_section, "segdata_file", values["boot2_file"])

        encryptEn = False
        signEn = False
        if "encrypt_key" in values.keys() and "aes_iv" in values.keys():
            if values["encrypt_key"] != "" and values["aes_iv"]:
                encryptEn = True
        if "public_key_cfg" in values.keys() and "private_key_cfg" in values.keys():
            if values["public_key_cfg"] != "" and values["private_key_cfg"]:
                signEn = True
        if "encrypt_key" in values.keys():
            bflb_utils.update_cfg(img_cfg, img_create_section, "aes_key_org",
                                  values["encrypt_key"])
        if "aes_iv" in values.keys():
            bflb_utils.update_cfg(img_cfg, img_create_section, "aes_iv", values["aes_iv"])
        if "public_key_cfg" in values.keys():
            bflb_utils.update_cfg(img_cfg, img_create_section, "publickey_file",
                                  values["public_key_cfg"])
        if "private_key_cfg" in values.keys():
            bflb_utils.update_cfg(img_cfg, img_create_section, "privatekey_file_uecc",
                                  values["private_key_cfg"])

        bflb_utils.update_cfg(img_cfg, img_create_section, "bootinfo_file", boot2_bootinfo_file)
        bflb_utils.update_cfg(img_cfg, img_create_section, "img_file", boot2_img_output_file)
        bflb_utils.update_cfg(img_cfg, img_create_section, "whole_img_file",
                              boot2_img_output_file.replace(".bin", "_if.bin"))
        img_cfg.write(self.img_create_cfg, "w+")

        # udate efuse data
        if encryptEn or signEn:
            img_cfg = BFConfigParser()
            img_cfg.read(self.img_create_cfg)
            if chiptype == "bl60x":
                efusefile = img_cfg.get("Img_CPU0_Cfg", "efuse_file")
                efusemaskfile = img_cfg.get("Img_CPU0_Cfg", "efuse_mask_file")
            else:
                efusefile = img_cfg.get("Img_Cfg", "efuse_file")
                efusemaskfile = img_cfg.get("Img_Cfg", "efuse_mask_file")
            load_cfg = BFConfigParser()
            load_cfg.read(self.eflash_loader_cfg_tmp)
            load_cfg.set('EFUSE_CFG', 'file', convert_path(os.path.relpath(efusefile, app_path)))
            load_cfg.set('EFUSE_CFG', 'maskfile',
                         convert_path(os.path.relpath(efusemaskfile, app_path)))
            load_cfg.write(self.eflash_loader_cfg_tmp, 'w')
            self.efuse_load_en = True
        else:
            self.efuse_load_en = False
        # create img
        # TODO: double sign
        options = ["--image=media", "--signer=none"]
        args = parser_image.parse_args(options)
        if "opt_mode" in values.keys():
            if values["opt_mode"] == "program":
                if not values["pt_file"]:
                    error = "error: please select partition file"
                    bflb_utils.printf(error)
                    return error
                if not values["boot2_file"]:
                    error = "error: please select boot2 file"
                    bflb_utils.printf(error)
                    return error


#                 if not values["img_file"]:
#                     error = "error: please select firmware file"
#                     bflb_utils.printf(error)
#                     return error
                bflb_img_create.img_create(args, chipname, chiptype, self.img_create_path,
                                           self.img_create_cfg)

        # img bootheader use user select crc/hash ignore
        cfg = BFConfigParser()
        cfg.read(bh_cfg_file)
        if "crc_ignore" in values.keys():
            bflb_utils.update_cfg(cfg, section, "crc_ignore",
                                  self.crc_ignore.index(values["crc_ignore"]))
        if "hash_ignore" in values.keys():
            bflb_utils.update_cfg(cfg, section, "hash_ignore",
                                  self.hash_ignore.index(values["hash_ignore"]))
        cfg.write(bh_cfg_file, "w+")
        bflb_efuse_boothd_create.bootheader_create_process(
            chipname, chiptype, bh_cfg_file, bh_file,
            self.img_create_path + "/bootheader_dummy.bin")

        if values["img_file"] != "":
            cfg = BFConfigParser()
            cfg.read(self.img_create_cfg)
            bflb_utils.update_cfg(cfg, img_create_section, "segdata_file", values["img_file"])
            bflb_utils.update_cfg(cfg, img_create_section, "bootinfo_file", bootinfo_file)
            bflb_utils.update_cfg(cfg, img_create_section, "img_file", img_output_file)
            bflb_utils.update_cfg(cfg, img_create_section, "whole_img_file",
                                  img_output_file.replace(".bin", "_if.bin"))
            cfg.write(self.img_create_cfg, "w+")
            bflb_img_create.img_create(args, chipname, chiptype, self.img_create_path,
                                       self.img_create_cfg)
        else:
            if values["opt_mode"] == "upgrade":
                error = "error: please select firmware file"
                bflb_utils.printf(error)
                return error

        os.remove(self.img_create_path + "/segheader_tmp.bin")
        if os.path.exists(self.img_create_path + '/bootheader_dummy.bin'):
            os.remove(self.img_create_path + "/bootheader_dummy.bin")

        bind_bootinfo = True
        if bind_bootinfo is True:
            pt_parcel = {}
            partition_file = os.path.join(chip_path, self.chipname, "partition/partition.bin")
            create_output_path = os.path.relpath(self.img_create_path, app_path)
            bootinfo_file = create_output_path + "/bootinfo.bin"
            img_output_file = create_output_path + "/img.bin"
            whole_img_output_file = create_output_path + "/whole_img.bin"
            boot2_bootinfo_file = create_output_path + "/bootinfo_blsp_boot2.bin"
            boot2_img_output_file = create_output_path + "/img_blsp_boot2.bin"
            boot2_whole_img_output_file = create_output_path + "/whole_img_blsp_boot2.bin"
            whole_flash_data_file = create_output_path + "/whole_flash_data.bin"
            if "pt_file" in values.keys():
                pt = values["pt_file"]
                if pt is not None and len(pt) > 0:
                    pt_helper = partition.PtCreater(pt)
                    # TODO name should not a fixed value
                    bflb_utils.printf("create partition.bin, pt_new is True")
                    pt_helper.create_pt_table(partition_file)
                    pt_parcel, name_list = pt_helper.construct_table()
            else:
                bflb_utils.set_error_code("0076")
                return bflb_utils.errorcode_msg()
            if values["opt_mode"] == "program":
                img_addr = 0x2000
                boot2_whole_img_len = img_addr + os.path.getsize(
                    os.path.join(app_path, boot2_img_output_file))
                boot2_whole_img_data = self.bl_create_flash_default_data(boot2_whole_img_len)
                filedata = self.bl_get_file_data([boot2_bootinfo_file])[0]
                boot2_whole_img_data[0:len(filedata)] = filedata
                filedata = self.bl_get_file_data([boot2_img_output_file])[0]
                boot2_whole_img_data[img_addr:img_addr + len(filedata)] = filedata
                fp = open(os.path.join(app_path, boot2_whole_img_output_file), 'wb+')
                fp.write(boot2_whole_img_data)
                fp.close()

            if values["img_file"] != "":
                img_addr = 0x1000
                whole_img_len = img_addr + os.path.getsize(os.path.join(app_path, img_output_file))
                whole_img_data = self.bl_create_flash_default_data(whole_img_len)
                filedata = self.bl_get_file_data([bootinfo_file])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = self.bl_get_file_data([img_output_file])[0]
                whole_img_data[img_addr:img_addr + len(filedata)] = filedata
                fp = open(os.path.join(app_path, whole_img_output_file), 'wb+')
                fp.write(whole_img_data)
                fp.close()

            if values["opt_mode"] == "program":
                parttion_data = self.bl_get_file_data([partition_file])[0]
                if values["img_file"] != "":
                    whole_flash_len = pt_parcel["fw_addr"] + whole_img_len
                else:
                    whole_flash_len = pt_parcel["fw_addr"]
                whole_flash_data = self.bl_create_flash_default_data(whole_flash_len)
                whole_flash_data[0:boot2_whole_img_len] = boot2_whole_img_data
                whole_flash_data[pt_parcel["pt_addr0"]:pt_parcel["pt_addr0"] +
                                 len(parttion_data)] = parttion_data
                whole_flash_data[pt_parcel["pt_addr1"]:pt_parcel["pt_addr1"] +
                                 len(parttion_data)] = parttion_data
                if values["img_file"] != "":
                    whole_flash_data[pt_parcel["fw_addr"]:whole_flash_len - 1] = whole_img_data
                fp = open(os.path.join(app_path, whole_flash_data_file), 'wb+')
                fp.write(whole_flash_data)
                fp.close()
        return True

    def create_img(self, chipname, chiptype, values):
        # basic check
        self.config = values
        error = True
        try:
            error = self.create_default_img(chipname, chiptype, values)
            return error
        except Exception as e:
            error = str(e)
            bflb_utils.printf(error)
            bflb_utils.set_error_code("0075")
            traceback.print_exc(limit=5, file=sys.stdout)
        finally:
            return error

    def program_img_thread(self, values, callback=None):
        bflb_utils.printf("========= eflash loader config =========")
        ret = None
        options = ""
        pt_parcel = {}
        partition_file = os.path.join(chip_path, self.chipname, "partition/partition.bin")
        create_output_path = os.path.relpath(self.img_create_path, app_path)
        try:
            if "pt_file" in values.keys():
                pt = values["pt_file"]
                if pt is not None and len(pt) > 0:
                    pt_helper = partition.PtCreater(pt)
                    # TODO name should not a fixed value
                    bflb_utils.printf("create partition.bin, pt_new is True")
                    pt_helper.create_pt_table(partition_file)
                    pt_parcel, name_list = pt_helper.construct_table()
            else:
                bflb_utils.set_error_code("0076")
                return bflb_utils.errorcode_msg()

            # decide file name
            bootinfo_file = create_output_path + "/bootinfo.bin"
            img_output_file = create_output_path + "/img.bin"
            whole_img_output_file = create_output_path + "/whole_img.bin"
            boot2_bootinfo_file = create_output_path + "/bootinfo_blsp_boot2.bin"
            boot2_img_output_file = create_output_path + "/img_blsp_boot2.bin"
            boot2_whole_img_output_file = create_output_path + "/whole_img_blsp_boot2.bin"
            whole_flash_data_file = create_output_path + "/whole_flash_data.bin"
            # program flash,create eflash_loader_cfg.ini
            cfg = BFConfigParser()
            if os.path.isfile(self.eflash_loader_cfg_tmp) is False:
                shutil.copyfile(self.eflash_loader_cfg, self.eflash_loader_cfg_tmp)
            cfg.read(self.eflash_loader_cfg_tmp)
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

            eflash_loader_bin = os.path.join(
                chip_path, self.chipname, "eflash_loader/" + get_eflash_loader(values["dl_xtal"]))

            if cfg.has_option("LOAD_CFG", "xtal_type"):
                bflb_utils.update_cfg(cfg, "LOAD_CFG", "xtal_type",
                                      self.xtal_type_.index(values["xtal_type"]))
            bind_bootinfo = True
            if bind_bootinfo is True:
                if values["opt_mode"] == "program":
                    img_addr = 0x2000
                    boot2_whole_img_len = img_addr + os.path.getsize(
                        os.path.join(app_path, boot2_img_output_file))
                    boot2_whole_img_data = self.bl_create_flash_default_data(boot2_whole_img_len)
                    filedata = self.bl_get_file_data([boot2_bootinfo_file])[0]
                    boot2_whole_img_data[0:len(filedata)] = filedata
                    filedata = self.bl_get_file_data([boot2_img_output_file])[0]
                    boot2_whole_img_data[img_addr:img_addr + len(filedata)] = filedata
                    fp = open(os.path.join(app_path, boot2_whole_img_output_file), 'wb+')
                    fp.write(boot2_whole_img_data)
                    fp.close()

                if values["img_file"] != "":
                    img_addr = 0x1000
                    whole_img_len = img_addr + os.path.getsize(
                        os.path.join(app_path, img_output_file))
                    whole_img_data = self.bl_create_flash_default_data(whole_img_len)
                    filedata = self.bl_get_file_data([bootinfo_file])[0]
                    whole_img_data[0:len(filedata)] = filedata
                    filedata = self.bl_get_file_data([img_output_file])[0]
                    whole_img_data[img_addr:img_addr + len(filedata)] = filedata
                    fp = open(os.path.join(app_path, whole_img_output_file), 'wb+')
                    fp.write(whole_img_data)
                    fp.close()

                if values["opt_mode"] == "program":
                    parttion_data = self.bl_get_file_data([partition_file])[0]
                    if values["img_file"] != "":
                        whole_flash_len = pt_parcel["fw_addr"] + whole_img_len
                    else:
                        whole_flash_len = pt_parcel["fw_addr"]
                    whole_flash_data = self.bl_create_flash_default_data(whole_flash_len)
                    whole_flash_data[0:boot2_whole_img_len] = boot2_whole_img_data
                    whole_flash_data[pt_parcel["pt_addr0"]:pt_parcel["pt_addr0"] +
                                     len(parttion_data)] = parttion_data
                    whole_flash_data[pt_parcel["pt_addr1"]:pt_parcel["pt_addr1"] +
                                     len(parttion_data)] = parttion_data
                    if values["img_file"] != "":
                        whole_flash_data[pt_parcel["fw_addr"]:whole_flash_len - 1] = whole_img_data
                    fp = open(os.path.join(app_path, whole_flash_data_file), 'wb+')
                    fp.write(whole_flash_data)
                    fp.close()

            if values["opt_mode"] == "upgrade":
                bflb_utils.update_cfg(cfg, "FLASH_CFG", "file",
                                      convert_path(whole_img_output_file))
                bflb_utils.update_cfg(cfg, "FLASH_CFG", "address", "00010000")
            else:
                file_path = convert_path(boot2_whole_img_output_file) + " " + \
                            convert_path(partition_file) + " " + convert_path(partition_file)
                if values["img_file"] != "":
                    file_path = file_path + " " + convert_path(whole_img_output_file)
                bflb_utils.update_cfg(cfg, "FLASH_CFG", "file", file_path)
                bflb_utils.update_cfg(cfg, "FLASH_CFG", "address", "00000000 %08x %08x %08x" \
                                      % (pt_parcel["pt_addr0"], pt_parcel["pt_addr1"], pt_parcel["fw_addr"]))
            cfg.write(self.eflash_loader_cfg_tmp, "w+")
            # call eflash_loader
            if values["dl_device"].lower() == "uart":
                options = [
                    "--write", "--flash", "-p", values["dl_comport"], "-c",
                    self.eflash_loader_cfg_tmp
                ]
            else:
                options = ["--write", "--flash", "-c", self.eflash_loader_cfg_tmp]
            if  "encrypt_key" in values.keys() and\
                "aes_iv" in values.keys():
                if  values["encrypt_key"] != "" and\
                    values["aes_iv"] != "":
                    options.extend(["--efuse",\
                    "--createcfg=" + self.img_create_cfg])
                    self.efuse_load_en = True
            ret = bflb_img_create.compress_dir(self.chipname, "img_create_mcu", self.efuse_load_en)
            if ret is not True:
                return bflb_utils.errorcode_msg()
            if not values["dl_comport"] and values["dl_device"].lower() == "uart":
                ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
                bflb_utils.printf(ret)
                return ret
            if not values["dl_comspeed"].isdigit() or not values["dl_jlinkspeed"].isdigit():
                ret = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
                bflb_utils.printf(ret)
                return ret
            if "opt_mode" in values.keys():
                if values["opt_mode"] == "upgrade":
                    if values["dl_device"].lower() != "uart":
                        ret = '{"ErrorCode":"FFFF","ErrorMsg":"INTERFACE MUST BE UART WHEN UPGRADE"}'
                        return ret
                    elif not values["dl_comport"]:
                        ret = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
                        return ret
                    options.extend(["--iap"])
                    # usb iap download
                    bflb_utils.printf("========= opening port, please wait ====")
                    self.progress_bar()
                    self.uart_dev.if_init(values["dl_comport"], values["dl_comspeed"],
                                          self.chiptype)
                    self.timer.cancel()
                    print('>')
                    self.uart_dev.if_set_rx_timeout(0.02)
                    bflb_utils.printf("sending enter_ota cmd")
                    if sys.platform.startswith("win"):
                        sb = bytes('enter_ota\r\n', encoding="ascii")
                        self.uart_dev.if_write(sb)
                        self.uart_dev._ser.flush()
                    else:
                        sb = bytes('\n', encoding="ascii")
                        self.uart_dev.if_write(sb)
                        time.sleep(0.001)
                        data = self.uart_dev.if_raw_read()
                        sb = bytes('enter_ota\n', encoding="ascii")
                        self.uart_dev.if_write(sb)
                    time.sleep(0.001)
                    data = self.uart_dev.if_raw_read()
                    self.uart_dev.if_close()
                    ack = data.decode('ascii')
                    #bflb_utils.printf("received: " + str(ack))
                    if "enter_ota" in ack:
                        bflb_utils.printf("enter ota success, start to check com port")
                        port = values["dl_comport"]
                        cnt = 0
                        while cnt < 10:
                            cnt += 1
                            time.sleep(0.5)
                            port_list = serial_enumerate()
                            if port in port_list:
                                break
                        if cnt == 10:
                            bflb_utils.printf("usb iap download fail")
                            return "usb iap download fail"
            args = parser_eflash.parse_args(options)
            ret = self.eflash_loader_thread(args, eflash_loader_bin, callback,
                                            self.create_img_callback)
        except Exception as e:
            ret = str(e)
            traceback.print_exc(limit=5, file=sys.stdout)
        finally:
            if self.timer:
                self.timer.cancel()
            return ret

    def create_img_callback(self):
        error = None
        values = self.config
        error = self.create_img(self.chipname, self.chiptype, values)
        if error:
            bflb_utils.printf(error)
        return error

    def log_read_thread(self):
        try:
            ret, data = self.eflash_loader_t.log_read_process()
            self.eflash_loader_t.close_port()
            return ret, data
        except Exception as e:
            traceback.print_exc(limit=10, file=sys.stdout)
            ret = str(e)
            return False, ret

    def progress_bar(self):
        if not self.uart_dev._ser:
            print("progressbar", end='')
            # 每隔0.2秒执行一次
            self.timer = threading.Timer(0.2, self.progress_bar)
            self.timer.start()


def get_value(args):
    chipname = args.chipname
    chiptype = gol.dict_chip_cmd.get(chipname, "unkown chip type")
    config = dict()
    config.setdefault('xtal_type', 'XTAL_38.4M')
    config.setdefault('pll_clk', '160M')
    config.setdefault('boot_src', 'Flash')
    config.setdefault('img_type', 'SingleCPU')
    config.setdefault('encrypt_type', 'None')
    config.setdefault('key_sel', '0')
    config.setdefault('cache_way_disable', 'None')
    config.setdefault('sign_type', 'None')
    config.setdefault('crc_ignore', 'False')
    config.setdefault('hash_ignore', 'False')
    config.setdefault('encrypt_key', '')
    config.setdefault('aes_iv', '')
    config.setdefault('public_key_cfg', '')
    config.setdefault('private_key_cfg', '')
    config.setdefault('bootinfo_addr', '0x0')
    config["dl_device"] = args.interface.lower()
    config["dl_comport"] = args.port
    config["dl_comspeed"] = str(args.baudrate)
    config["dl_jlinkspeed"] = str(args.baudrate)
    config["img_file"] = args.firmware
    config["img_addr"] = "0x" + str(args.addr)
    config["device_tree"] = args.dts

    if chiptype == "bl602":
        if not args.xtal:
            config["dl_xtal"] = "40M"
            config["xtal_type"] = 'XTAL_40M'
            bflb_utils.printf("Default xtal is 40M")
        else:
            config["dl_xtal"] = args.xtal
            config["xtal_type"] = 'XTAL_' + args.xtal
        if not args.flashclk:
            config["flash_clk_type"] = "48M"
            bflb_utils.printf("Default flash clock is 48M")
        else:
            config["flash_clk_type"] = args.flashclk
        if not args.pllclk:
            config["pll_clk"] = "160M"
            bflb_utils.printf("Default pll clock is 160M")
        else:
            config["pll_clk"] = args.pllclk
    elif chiptype == "bl702":
        if not args.xtal:
            config["dl_xtal"] = "32M"
            config["xtal_type"] = 'XTAL_32M'
            bflb_utils.printf("Default xtal is 32M")
        else:
            config["dl_xtal"] = args.xtal
            config["xtal_type"] = 'XTAL_' + args.xtal
        if not args.flashclk:
            config["flash_clk_type"] = "72M"
            bflb_utils.printf("Default flash clock is 72M")
        else:
            config["flash_clk_type"] = args.flashclk
        if not args.pllclk:
            config["pll_clk"] = "144M"
            bflb_utils.printf("Default pll clock is 144M")
        else:
            config["pll_clk"] = args.pllclk
    elif chiptype == "bl60x":
        if not args.xtal:
            config["dl_xtal"] = "38.4M"
            config["xtal_type"] = 'XTAL_38.4M'
        else:
            config["dl_xtal"] = args.xtal
            config["xtal_type"] = 'XTAL_' + args.xtal
            bflb_utils.printf("Default xtal is 38.4M")
        if not args.flashclk:
            config["flash_clk_type"] = "80M"
        else:
            config["flash_clk_type"] = args.flashclk
            bflb_utils.printf("Default flash clock is 80M")
        if not args.pllclk:
            config["pll_clk"] = "160M"
        else:
            config["pll_clk"] = args.pllclk
            bflb_utils.printf("Default pll clock is 160M")
    else:
        bflb_utils.printf("Chip type is not correct")
        sys.exit(1)

    if config["dl_device"] == "jlink" and args.baudrate > 12000:
        config["dl_jlinkspeed"] = "12000"

    if args.erase:
        config["dl_chiperase"] = "True"
    else:
        config["dl_chiperase"] = "False"
    return config


def run():
    port = None
    ports = []
    for item in get_serial_ports():
        ports.append(item["port"])
    if ports:
        try:
            port = sorted(ports, key=lambda x: int(re.match('COM(\d+)', x).group(1)))[0]
        except Exception:
            port = sorted(ports)[0]
    firmware_default = os.path.join(app_path, "img/project.bin")
    parser = argparse.ArgumentParser(description='mcu-tool')
    parser.add_argument('--chipname', required=True, help='chip name')
    parser.add_argument("--interface", dest="interface", default="uart", help="interface to use")
    parser.add_argument("--bootsrc", dest="bootsrc", default="flash", help="boot source select")
    parser.add_argument("--port", dest="port", default=port, help="serial port to use")
    parser.add_argument("--baudrate",
                        dest="baudrate",
                        default=115200,
                        type=int,
                        help="the speed at which to communicate")
    parser.add_argument("--xtal", dest="xtal", help="xtal type")
    parser.add_argument("--flashclk", dest="flashclk", help="flash clock")
    parser.add_argument("--pllclk", dest="pllclk", help="pll clock")
    parser.add_argument("--firmware",
                        dest="firmware",
                        default=firmware_default,
                        help="image to write")
    parser.add_argument("--addr", dest="addr", default="2000", help="address to write")
    parser.add_argument("--dts", dest="dts", help="device tree")
    parser.add_argument("--build", dest="build", action="store_true", help="build image")
    parser.add_argument("--erase", dest="erase", action="store_true", help="chip erase")
    args = parser.parse_args()
    bflb_utils.printf("==================================================")
    bflb_utils.printf("Chip name is %s" % args.chipname)
    if not args.port:
        bflb_utils.printf("Serial port is not found")
    else:
        bflb_utils.printf("Serial port is " + str(port))
    bflb_utils.printf("Baudrate is " + str(args.baudrate))
    bflb_utils.printf("Firmware is " + args.firmware)
    config = get_value(args)
    obj_iap = BflbIapTool(args.chipname, gol.dict_chip_cmd.get(args.chipname, "unkown chip type"))
    bflb_utils.printf("==================================================")
    try:
        obj_iap.create_img(args.chipname, gol.dict_chip_cmd[args.chipname], config)
        if args.build:
            obj_iap.bind_img(config)
            f_org = os.path.join(chip_path, args.chipname, "img_create_mcu", "whole_img.bin")
            f = "firmware.bin"
            shutil.copyfile(f_org, f)
        else:
            obj_iap.program_img_thread(config)
    except Exception as e:
        error = str(e)
        bflb_utils.printf(error)
        traceback.print_exc(limit=5, file=sys.stdout)


if __name__ == '__main__':
    run()
