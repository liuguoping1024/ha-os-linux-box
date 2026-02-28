# -*- coding:utf-8 -*-

import re
import os
import sys
import shutil
import argparse
import subprocess
import traceback
import hashlib
import lzma

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_utils
from libs import bflb_eflash_loader
from libs import bflb_toml as toml
from libs import bflb_flash_select
from libs.bflb_utils import verify_hex_num, get_eflash_loader, get_serial_ports, convert_path
from libs.bflb_configobj import BFConfigParser
import libs.bflb_pt_creater as partition
import libs.bflb_eflash_loader as eflash_loader
import libs.bflb_efuse_boothd_create as eb_create
import libs.bflb_img_create as img_create
import libs.bflb_ro_params_device_tree as bl_ro_device_tree

parser_eflash = bflb_utils.eflash_loader_parser_init()

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


def find_boot2(path, boot2):
    for root, dirs, files in os.walk(path, True):
        for item in files:
            if item == boot2:
                filepath = os.path.join(root, item)
                return (filepath)
    return None


def parse_rfpa(bin):
    with open(bin, "rb") as fp:
        content = fp.read()
        return content[1024:1032]


def flash_type(chip_flash_name):
    cfg_file_name_list = chip_flash_name.split("_")
    _type = cfg_file_name_list[1]
    vendor = cfg_file_name_list[2]
    size = cfg_file_name_list[3]
    return (_type, vendor, size)


def img_create_sha256_data(data_bytearray):
    hashfun = hashlib.sha256()
    hashfun.update(data_bytearray)
    return bflb_utils.hexstr_to_bytearray(hashfun.hexdigest())


def bl_get_largest_addr(addrs, files):
    maxlen = 0
    datalen = 0
    for i in range(len(addrs)):
        if int(addrs[i], 16) > maxlen:
            maxlen = int(addrs[i], 16)
            datalen = os.path.getsize(os.path.join(app_path, files[i]))
    return maxlen + datalen


def bl_get_file_data(files):
    datas = []
    for file in files:
        with open(os.path.join(app_path, file), 'rb') as fp:
            data = fp.read()
        datas.append(data)
    return datas


def bl_create_flash_default_data(length):
    datas = bytearray(length)
    for i in range(length):
        datas[i] = 0xff
    return datas


def generate_romfs_img(romfs_dir, dst_img_name):
    exe = None
    if os.name == 'nt':
        exe = os.path.join(app_path, 'utils/genromfs', 'genromfs.exe')
    elif os.name == 'posix':
        machine = os.uname().machine
        if machine == 'x86_64':
            exe = os.path.join(app_path, 'utils/genromfs', 'genromfs_amd64')
        elif machine == 'armv7l':
            exe = os.path.join(app_path, 'utils/genromfs', 'genromfs_armel')
        elif machine == 'arm64':
            exe = os.path.join(app_path, 'utils/genromfs', 'genromfs_arm64')
    if exe is None:
        bflb_utils.printf('NO supported genromfs exe for your platform!')
        return -1
    dir = os.path.abspath(romfs_dir)
    dst = os.path.abspath(dst_img_name)
    bflb_utils.printf('Generating romfs image %s using directory %s ... ' % (dst, dir))
    try:
        ret = subprocess.call([exe, '-d', dir, '-f', dst, '-a', '64'])
    except Exception as e:
        exe = os.path.join(app_path, 'utils/genromfs', 'genromfs_arm64')
        ret = subprocess.call([exe, '-d', dir, '-f', dst, '-a', '64'])
    return ret


def check_pt_table(pt_parcel, file):
    if len(file) > 0:
        i = 0
        try:
            while i < len(file):
                file_name = file[i]
                file_size = os.path.getsize(os.path.join(app_path, file_name))
                if "whole_img_boot2.bin" in file_name:
                    if file_size > pt_parcel['pt_addr0']:
                        bflb_utils.printf("Error: boot2 bin size is overflow with partition table")
                        return False
                if "whole_img_cpu0.bin" in file_name:
                    if file_size > pt_parcel['fw_cpu0_len']:
                        bflb_utils.printf(
                            "Error: cpu0 fw bin size is overflow with partition table")
                        return False
                if "whole_img_group0.bin" in file_name:
                    if file_size > pt_parcel['fw_group0_len']:
                        bflb_utils.printf(
                            "Error: group0 fw bin size is overflow with partition table")
                        return False
                if "whole_img_group1.bin" in file_name:
                    if file_size > pt_parcel['fw_group1_len']:
                        bflb_utils.printf(
                            "Error: group1 fw bin size is overflow with partition table")
                        return False
                if "whole_img_d0fw.bin" in file_name:
                    if file_size > pt_parcel['fw_d0_len']:
                        bflb_utils.printf("Error: d0fw bin size is overflow with partition table")
                        return False
                if "whole_img.bin" in file_name:
                    if file_size > pt_parcel['fw_len']:
                        bflb_utils.printf("Error: fw bin size is overflow with partition table")
                        return False
                if "whole_img_mfg.bin" in file_name:
                    if file_size > pt_parcel['mfg_len']:
                        bflb_utils.printf("Error: mfg bin size is overflow with partition table")
                        return False
                if "media.bin" in file_name:
                    if file_size > pt_parcel['media_len']:
                        bflb_utils.printf("Error: media bin size is overflow with partition table")
                        return False
                if "whole_img_imgloader.bin" in file_name:
                    if file_size > pt_parcel['imgloader_len']:
                        bflb_utils.printf(
                            "Error: imgloader bin size is overflow with partition table")
                        return False
                if "whole_img_sbi.bin" in file_name:
                    if file_size > pt_parcel['sbi_len']:
                        bflb_utils.printf("Error: sbi bin size is overflow with partition table")
                        return False
                if "whole_img_kernel.bin" in file_name:
                    if file_size > pt_parcel['kernel_len']:
                        bflb_utils.printf(
                            "Error: kernel bin size is overflow with partition table")
                        return False
                if "imtb.bin" in file_name:
                    if file_size > pt_parcel['imtb_len']:
                        bflb_utils.printf("Error: imtb bin size is overflow with partition table")
                        return False
                if "whole_img_rootfs.bin" in file_name:
                    if file_size > pt_parcel['rootfs_len']:
                        bflb_utils.printf(
                            "Error: rootfs bin size is overflow with partition table")
                        return False
                if "whole_img_dtb.bin" in file_name:
                    if file_size > pt_parcel['dtb_len']:
                        bflb_utils.printf("Error: dtb bin size is overflow with partition table")
                        return False
                i += 1
        except Exception as e:
            bflb_utils.printf(e)
            return False
    return True


def exe_genitor(list_args):
    p = subprocess.Popen(list_args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while subprocess.Popen.poll(p) is None:
        try:
            r = p.stdout.readline().strip().decode('utf-8')
            if r == '':
                break
            bflb_utils.printf(r)
        except UnicodeDecodeError:
            continue


class BflbLinuxTool(object):

    def __init__(self, chipname="bl808", chiptype="bl808"):
        self.efuse_load_en = False
        self.config = {}
        self.chipname = chipname
        self.chiptype = chiptype
        self.eflash_loader_t = bflb_eflash_loader.BflbEflashLoader(chipname, chiptype)

        eflash_loader_cfg_org = os.path.join(chip_path, chipname,
                                             "eflash_loader/eflash_loader_cfg.conf")
        self.eflash_loader_cfg = os.path.join(chip_path, chipname,
                                              "eflash_loader/eflash_loader_cfg.ini")
        if os.path.isfile(self.eflash_loader_cfg) is False:
            shutil.copyfile(eflash_loader_cfg_org, self.eflash_loader_cfg)
        bh_cfg_file_org = os.path.join(chip_path, chipname,
                                       "efuse_bootheader/efuse_bootheader_cfg.conf")
        self.bh_cfg_file = os.path.join(chip_path, chipname,
                                        "img_create_linux/efuse_bootheader_cfg.ini")
        if os.path.isfile(self.bh_cfg_file) is False:
            shutil.copyfile(bh_cfg_file_org, self.bh_cfg_file)

    def bflb_image_bootheader_gen(self,
                                  boot2,
                                  xtal,
                                  config,
                                  encrypt=False,
                                  sign=False,
                                  chipname="bl808",
                                  chiptype="bl808",
                                  cpu_type=None,
                                  boot2_en=False):
        cfg = BFConfigParser()
        cfg.read(config)
        dict_xtal = gol.xtal_type[chiptype]

        if cpu_type is not None:
            bootheader_section_name = "BOOTHEADER_" + cpu_type.upper() + "_CFG"
        else:
            if "BOOTHEADER_CPU0_CFG" in cfg.sections():
                bootheader_section_name = "BOOTHEADER_CPU0_CFG"
            elif "BOOTHEADER_GROUP0_CFG" in cfg.sections():
                bootheader_section_name = "BOOTHEADER_GROUP0_CFG"
            else:
                bootheader_section_name = "BOOTHEADER_CFG"

        if boot2 is True:
            if chiptype == "bl808":
                cfg.set(bootheader_section_name, 'group_image_offset', '0x2000')
                cfg.set(bootheader_section_name, 'd0_config_enable', '0')
                cfg.set(bootheader_section_name, 'lp_config_enable', '0')
                # cfg.set(bootheader_section_name, 'd0_halt_cpu', '1')
                # cfg.set(bootheader_section_name, 'lp_halt_cpu', '1')
            elif chiptype == "bl616" or chiptype == "wb03":
                cfg.set(bootheader_section_name, 'group_image_offset', '0x2000')
                cfg.set(bootheader_section_name, 'custom_vendor_boot_offset', "0x2000")
            else:
                cfg.set(bootheader_section_name, 'img_start', '0x2000')
                cfg.set(bootheader_section_name, 'cache_enable', '1')
                if cpu_type is not None:
                    cfg.set(bootheader_section_name, 'halt_cpu1', '1')
            #cfg.set(bootheader_section_name, 'key_sel', '0')

        if encrypt:
            cfg.set(bootheader_section_name, 'encrypt_type', '1')
        else:
            cfg.set(bootheader_section_name, 'encrypt_type', '0')

        if sign:
            cfg.set(bootheader_section_name, 'sign', '1')
        else:
            cfg.set(bootheader_section_name, 'sign', '0')

        bflb_utils.printf('bflb_image_bootheader_gen xtal: %s' % xtal)
        cfg.set(bootheader_section_name, 'xtal_type', dict_xtal.index(xtal))

        cfg.write(config)
        eb_create.efuse_boothd_create_process(chipname, chiptype, config)

    def bflb_mfg_bootheader_gen(self,
                                mfg_addr,
                                xtal,
                                config,
                                chipname="bl808",
                                chiptype="bl808",
                                cpu_type=None):
        cfg = BFConfigParser()
        cfg.read(config)
        dict_xtal = gol.xtal_type[chiptype]

        if cpu_type is not None:
            bootheader_section_name = "BOOTHEADER_" + cpu_type.upper() + "_CFG"
        else:
            if "BOOTHEADER_CPU0_CFG" in cfg.sections():
                bootheader_section_name = "BOOTHEADER_CPU0_CFG"
            elif "BOOTHEADER_GROUP0_CFG" in cfg.sections():
                bootheader_section_name = "BOOTHEADER_GROUP0_CFG"
            else:
                bootheader_section_name = "BOOTHEADER_CFG"

        if chiptype == "bl808":
            cfg.set(bootheader_section_name, 'group_image_offset', hex(int(mfg_addr, 16) + 0x1000))
            cfg.set(bootheader_section_name, 'd0_config_enable', '0')
            cfg.set(bootheader_section_name, 'lp_config_enable', '0')
            # cfg.set(bootheader_section_name, 'd0_halt_cpu', '1')
            # cfg.set(bootheader_section_name, 'lp_halt_cpu', '1')
        elif chiptype == "bl616" or chiptype == "wb03":
            cfg.set(bootheader_section_name, 'group_image_offset', hex(int(mfg_addr, 16) + 0x1000))
        else:
            cfg.set(bootheader_section_name, 'img_start', mfg_addr)
            cfg.set(bootheader_section_name, 'cache_enable', '1')
            if cpu_type is not None:
                cfg.set(bootheader_section_name, 'halt_cpu1', '1')

        #cfg.set(bootheader_section_name, 'key_sel', '0')

        bflb_utils.printf('bflb_mfg_bootheader_gen xtal: %s' % xtal)
        cfg.set(bootheader_section_name, 'xtal_type', dict_xtal.index(xtal))

        cfg.write(config)
        eb_create.efuse_boothd_create_process(chipname, chiptype, config)

    def bflb_image_gen_cfg(self,
                           chipname,
                           chiptype,
                           raw_bin_name,
                           bintype,
                           key=None,
                           iv=None,
                           publickey=None,
                           privatekey=None,
                           cfg_ini=None,
                           group_type=None):
        efuse_file = os.path.join(chip_path, chipname, "efuse_bootheader/efusedata.bin")
        efuse_mask_file = os.path.join(chip_path, chipname, "efuse_bootheader/efusedata_mask.bin")
        if chiptype == "bl808" or chiptype == "bl616" or chiptype == "wb03":
            if group_type == "Group1":
                bh_file = os.path.join(chip_path, chipname,
                                       "efuse_bootheader/bootheader_group1.bin")
            else:
                bh_file = os.path.join(chip_path, chipname,
                                       "efuse_bootheader/bootheader_group0.bin")
        else:
            bh_file = os.path.join(chip_path, chipname, "efuse_bootheader/bootheader.bin")
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f_org = os.path.join(chip_path, chipname, "img_create_linux", "img_create_cfg.conf")
            f = os.path.join(chip_path, chipname, "img_create_linux", "img_create_cfg.ini")
            if os.path.isfile(f) is False:
                shutil.copyfile(f_org, f)
        else:
            f = cfg_ini
        cfg.read(f)
        if bintype == "fw":
            if group_type is None or group_type == "Group0":
                bootinfo_file = os.path.join(chip_path, chipname, "img_create_linux",
                                             "bootinfo.bin")
                img_file = os.path.join(chip_path, chipname, "img_create_linux", "img.bin")
            else:
                bootinfo_file = os.path.join(chip_path, chipname, "img_create_linux",
                                             "bootinfo_{0}.bin".format(group_type.lower()))
                img_file = os.path.join(chip_path, chipname, "img_create_linux",
                                        "img_{0}.bin".format(group_type.lower()))
        else:
            bootinfo_file = os.path.join(chip_path, chipname, "img_create_linux",
                                         "bootinfo_{0}.bin".format(bintype))
            img_file = os.path.join(chip_path, chipname, "img_create_linux",
                                    "img_{0}.bin".format(bintype))

        if group_type is not None:
            img_section_name = "Img_" + group_type + "_Cfg"
        else:
            if "Img_Group0_Cfg" in cfg.sections() and group_type == "Group0":
                img_section_name = "Img_Group0_Cfg"
            elif "Img_Group1_Cfg" in cfg.sections() and group_type == "Group1":
                img_section_name = "Img_Group1_Cfg"
            else:
                img_section_name = "Img_Cfg"
        cfg.set(img_section_name, 'boot_header_file', bh_file)
        cfg.set(img_section_name, 'efuse_file', efuse_file)
        cfg.set(img_section_name, 'efuse_mask_file', efuse_mask_file)
        cfg.set(img_section_name, 'segdata_file', raw_bin_name)
        cfg.set(img_section_name, 'bootinfo_file', bootinfo_file)
        cfg.set(img_section_name, 'img_file', img_file)
        if key:
            cfg.set(img_section_name, 'aes_key_org', key)
        if iv:
            cfg.set(img_section_name, 'aes_iv', iv)
        if publickey:
            cfg.set(img_section_name, 'publickey_file', publickey)
        if privatekey:
            cfg.set(img_section_name, 'privatekey_file_uecc', privatekey)
        cfg.write(f, 'w')
        return f

    def bflb_ota_header_gen(self, chipname, file_bytearray, use_xz):
        ota_cfg = os.path.join(chip_path, chipname, "conf/ota.toml")
        parsed_toml = toml.load(ota_cfg)
        header_len = 512
        header = bytearray()
        file_len = len(file_bytearray)
        m = hashlib.sha256()

        # 16 Bytes header
        data = b'BL60X_OTA_Ver1.0'
        for b in data:
            header.append(b)
        # 4 Byte ota file type
        if use_xz:
            data = b'XZ  '
        else:
            data = b'RAW '
        for b in data:
            header.append(b)

        # 4 Bytes file length
        file_len_bytes = file_len.to_bytes(4, byteorder='little')
        for b in file_len_bytes:
            header.append(b)

        # 8 Bytes pad
        header.append(0x01)
        header.append(0x02)
        header.append(0x03)
        header.append(0x04)
        header.append(0x05)
        header.append(0x06)
        header.append(0x07)
        header.append(0x08)

        # 16 Bytes Hardware version
        data = bytearray(parsed_toml["ota"]["version_hardware"].encode('utf-8'))
        data_len = 16 - len(data)
        for b in data:
            header.append(b)
        while data_len > 0:
            header.append(0x00)
            data_len = data_len - 1

        # 16 Bytes firmware version
        data = bytearray(parsed_toml["ota"]["version_software"].encode('utf-8'))
        data_len = 16 - len(data)
        for b in data:
            header.append(b)
        while data_len > 0:
            header.append(0x00)
            data_len = data_len - 1

        # 32 Bytes SHA256
        m.update(file_bytearray)
        hash_bytes = m.digest()
        for b in hash_bytes:
            header.append(b)
        header_len = header_len - len(header)
        while header_len > 0:
            header.append(0xFF)
            header_len = header_len - 1
        return header

    def bflb_ota_xz_gen(self, ota_path, chipname="bl808", chiptype="bl808", cpu_type=None):
        bflb_xz_filters = [
            {
                "id": lzma.FILTER_LZMA2,
                "dict_size": 32768
            },
        ]

        fw_ota_bin = bytearray()
        fw_ota_bin_xz = bytearray()
        if cpu_type is None or cpu_type == "Group0":
            fw_ota_path = os.path.join(ota_path, "FW_OTA.bin")
        else:
            fw_ota_path = os.path.join(ota_path, cpu_type + "_OTA.bin")
        with open(fw_ota_path, mode="rb") as bin_f:
            file_bytes = bin_f.read()
            for b in file_bytes:
                fw_ota_bin.append(b)
        if cpu_type is None or cpu_type == "Group0":
            fw_ota_path = os.path.join(ota_path, "FW_OTA.bin.xz")
        else:
            fw_ota_path = os.path.join(ota_path, cpu_type + "_OTA.bin.xz")
        with lzma.open(fw_ota_path, mode="wb", check=lzma.CHECK_CRC32,
                       filters=bflb_xz_filters) as xz_f:
            xz_f.write(fw_ota_bin)
        with open(fw_ota_path, mode="rb") as f:
            file_bytes = f.read()
            for b in file_bytes:
                fw_ota_bin_xz.append(b)
        fw_ota_bin_xz_ota = self.bflb_ota_header_gen(chipname, fw_ota_bin_xz, use_xz=1)
        for b in fw_ota_bin_xz:
            fw_ota_bin_xz_ota.append(b)
        if cpu_type is None or cpu_type == "Group0":
            fw_ota_path = os.path.join(ota_path, "FW_OTA.bin.xz.ota")
            fw_ota_path1 = os.path.join(ota_path, "FW_OTA.bin.hash")
        else:
            fw_ota_path = os.path.join(ota_path, cpu_type + "_OTA.bin.xz.ota")
            fw_ota_path1 = os.path.join(ota_path, cpu_type + "_OTA.bin.hash")
        with open(fw_ota_path, mode="wb") as f:
            f.write(fw_ota_bin_xz_ota)
        with open(fw_ota_path.replace(".ota", ".hash"), mode="wb") as f:
            f.write(fw_ota_bin_xz + img_create_sha256_data(fw_ota_bin_xz))
        with open(fw_ota_path1, mode="wb") as f:
            f.write(fw_ota_bin + img_create_sha256_data(fw_ota_bin))

    def bflb_ota_bin_gen(self,
                         chipname="bl808",
                         chiptype="bl808",
                         cpu_type=None,
                         version="",
                         dir_ota=None):
        fw_header_len = 4096
        fw_ota_bin = bytearray()
        if dir_ota:
            ota_path = dir_ota
        else:
            ota_path = os.path.join(chip_path, chipname, "ota")
        if os.path.isdir(ota_path) is False:
            os.mkdir(ota_path)

        if cpu_type is None or cpu_type == "Group0":
            bootinfo_fw_path = os.path.join(chip_path, chipname, "img_create_linux",
                                            "bootinfo.bin")
        else:
            bootinfo_fw_path = os.path.join(chip_path, chipname, "img_create_linux",
                                            "bootinfo_" + cpu_type.lower() + ".bin")
        with open(bootinfo_fw_path, mode="rb") as f:
            if chiptype == "bl808":
                fw_header_len = 4096
            file_bytes = f.read(fw_header_len)
            for b in file_bytes:
                fw_ota_bin.append(b)
        i = fw_header_len - len(fw_ota_bin)
        bflb_utils.printf("FW Header is %d, %d still needed" % (len(fw_ota_bin), i))
        while i > 0:
            fw_ota_bin.append(0xFF)
            i = i - 1
        bflb_utils.printf("FW OTA bin header is Done. Len is %d" % len(fw_ota_bin))
        if cpu_type is None or cpu_type == "Group0":
            img_fw_path = os.path.join(chip_path, chipname, "img_create_linux", "img.bin")
        else:
            img_fw_path = os.path.join(chip_path, chipname, "img_create_linux",
                                       "img_" + cpu_type.lower() + ".bin")
        with open(img_fw_path, mode="rb") as f:
            file_bytes = f.read()
            for b in file_bytes:
                fw_ota_bin.append(b)
        fw_ota_bin_header = self.bflb_ota_header_gen(chipname, fw_ota_bin, use_xz=0)
        if cpu_type is None or cpu_type == "Group0":
            fw_ota_path = os.path.join(ota_path, "FW_OTA.bin")
        else:
            fw_ota_path = os.path.join(ota_path, cpu_type + "_OTA.bin")
        with open(fw_ota_path, mode="wb") as f:
            f.write(fw_ota_bin)

        for b in fw_ota_bin:
            fw_ota_bin_header.append(b)
        if cpu_type is None or cpu_type == "Group0":
            fw_ota_path = os.path.join(ota_path, "FW_OTA.bin.ota")
        else:
            fw_ota_path = os.path.join(ota_path, cpu_type + "_OTA.bin.ota")
        with open(fw_ota_path, mode="wb") as f:
            f.write(fw_ota_bin_header)
        bflb_utils.printf("FW OTA bin is Done. Len is %d" % len(fw_ota_bin))
        self.bflb_ota_xz_gen(ota_path, chipname, chiptype, cpu_type)
        bflb_utils.printf("FW OTA xz is Done")

    def bflb_image_gen(self,
                       chipname,
                       chiptype,
                       cpu_type,
                       bintype,
                       raw_bin_name,
                       key=None,
                       iv=None,
                       publickey=None,
                       privarekey=None,
                       cfg_ini=None):
        # python bflb_img_create.py -c np -i media -s none
        f = self.bflb_image_gen_cfg(chipname, chiptype, raw_bin_name, bintype, key, iv, publickey,
                                    privarekey, cfg_ini, cpu_type)
        if key or (publickey and privarekey):
            img_cfg = BFConfigParser()
            img_cfg.read(f)
            if chiptype == "bl808":
                efusefile = img_cfg.get("Img_Group0_Cfg", "efuse_file")
                efusemaskfile = img_cfg.get("Img_Group0_Cfg", "efuse_mask_file")
            else:
                efusefile = img_cfg.get("Img_Cfg", "efuse_file")
                efusemaskfile = img_cfg.get("Img_Cfg", "efuse_mask_file")
            cfg = BFConfigParser()
            cfg.read(self.eflash_loader_cfg)
            cfg.set('EFUSE_CFG', 'file', convert_path(os.path.relpath(efusefile, app_path)))
            cfg.set('EFUSE_CFG', 'maskfile', convert_path(os.path.relpath(efusemaskfile,
                                                                          app_path)))
            cfg.write(self.eflash_loader_cfg, 'w')
            self.efuse_load_en = True
        else:
            self.efuse_load_en = False
        return img_create.create_sp_media_image_file(f, chiptype, cpu_type)

    def bflb_flasher_uart_cfg(self, uart, baudrate='57600', cfg_ini=None):
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f = self.eflash_loader_cfg
        else:
            f = cfg_ini
        cfg.read(f)
        cfg.set('LOAD_CFG', 'interface', 'uart')
        cfg.set('LOAD_CFG', 'device', uart)
        cfg.set('LOAD_CFG', 'speed_uart_load', baudrate)
        cfg.write(f, 'w')

    def bflb_flasher_jlink_cfg(self, rate="1000", cfg_ini=None):
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f = self.eflash_loader_cfg
        else:
            f = cfg_ini
        cfg.read(f)
        cfg.set('LOAD_CFG', 'interface', 'jlink')
        cfg.set('LOAD_CFG', 'speed_jlink', rate)
        cfg.write(f, 'w')

    def bflb_flasher_cklink_cfg(self, rate="1000", cfg_ini=None):
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f = self.eflash_loader_cfg
        else:
            f = cfg_ini
        cfg.read(f)
        cfg.set('LOAD_CFG', 'interface', 'cklink')
        cfg.set('LOAD_CFG', 'speed_jlink', rate)
        cfg.write(f, 'w')

    def bflb_flasher_openocd_cfg(self, rate="8000", cfg_ini=None):
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f = self.eflash_loader_cfg
        else:
            f = cfg_ini
        cfg.read(f)
        cfg.set('LOAD_CFG', 'interface', 'openocd')
        cfg.set('LOAD_CFG', 'speed_jlink', rate)
        cfg.write(f, 'w')

    def bflb_flasher_erase_all(self, erase, cfg_ini=None):
        cfg = BFConfigParser()
        if cfg_ini in [None, '']:
            f = self.eflash_loader_cfg
        else:
            f = cfg_ini
        cfg.read(f)
        if erase is True:
            cfg.set('LOAD_CFG', 'erase', '2')
        else:
            cfg.set('LOAD_CFG', 'erase', '1')
        cfg.write(f, 'w')

    def bflb_write_flash_img(self, d_addrs, d_files, flash_size):
        whole_img_len = bl_get_largest_addr(d_addrs, d_files)
        whole_img_data = bl_create_flash_default_data(whole_img_len)
        whole_img_file = os.path.join(chip_path, self.chipname, "img_create_linux",
                                      "whole_flash_data.bin")
        filedatas = bl_get_file_data(d_files)
        # create_whole_image_flash
        for i in range(len(d_addrs)):
            start_addr = int(d_addrs[i], 16)
            whole_img_data[start_addr:start_addr + len(filedatas[i])] = filedatas[i]
        fp = open(whole_img_file, 'wb+')
        fp.write(whole_img_data)
        fp.close()

    def bflb_flasher_eflash_loader_cfg(self,
                                       chipname,
                                       chiptype,
                                       bin_file,
                                       boot2,
                                       ro_params,
                                       pt_parcel,
                                       media,
                                       mfg,
                                       d0fw=False,
                                       imtb=False,
                                       imgloader=False,
                                       sbi=False,
                                       kernel=False,
                                       rootfs=False,
                                       dtb=False,
                                       flash_opt="1M"):
        bflb_utils.printf("========= eflash loader config =========")
        d_files = []
        d_addrs = []
        bind_bootinfo = True
        chipnamedir = os.path.join(chip_path, chipname)

        if pt_parcel is None:
            bflb_utils.set_error_code("007B")
            return bflb_utils.errorcode_msg()

        if boot2 is True:
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_boot2.bin"
                whole_img_len = 0x2000 + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_boot2.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_boot2.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_boot2.bin"])[0]
                whole_img_data[0x2000:0x2000 + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_boot2.bin")
                d_addrs.append("00000000")
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_boot2.bin")
                d_addrs.append("00000000")
                d_files.append("chips/" + chipname + "/img_create_linux/img_boot2.bin")
                d_addrs.append("00002000")

        if pt_parcel is not None and len(pt_parcel) > 0 and pt_parcel['pt_new'] is True:
            d_files.append("chips/" + chipname + "/partition/partition.bin")
            d_addrs.append(hex(pt_parcel['pt_addr0'])[2:])
            d_files.append("chips/" + chipname + "/partition/partition.bin")
            d_addrs.append(hex(pt_parcel['pt_addr1'])[2:])

        if bin_file is True:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if 'fw_group0_addr' in pt_parcel:
                if bind_bootinfo is True:
                    whole_img = chipnamedir + "/img_create_linux/whole_img_group0.bin"
                    whole_img_len = offset + os.path.getsize(chipnamedir +
                                                             "/img_create_linux/img_group0.bin")
                    whole_img_data = bl_create_flash_default_data(whole_img_len)
                    filedata = bl_get_file_data(
                        ["chips/" + chipname + "/img_create_linux/bootinfo_group0.bin"])[0]
                    whole_img_data[0:len(filedata)] = filedata
                    filedata = bl_get_file_data(
                        ["chips/" + chipname + "/img_create_linux/img_group0.bin"])[0]
                    whole_img_data[offset:offset + len(filedata)] = filedata
                    fp = open(whole_img, 'wb+')
                    fp.write(whole_img_data)
                    fp.close()
                    d_files.append("chips/" + chipname + "/img_create_linux/whole_img_group0.bin")
                    d_addrs.append(hex(pt_parcel['fw_group0_addr'])[2:])
                else:
                    d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_group0.bin")
                    d_addrs.append(hex(pt_parcel['fw_group0_addr'])[2:])
                    d_files.append("chips/" + chipname + "/img_create_linux/img_group0.bin")
                    d_addrs.append(hex(pt_parcel['fw_group0_addr'] + offset)[2:])

        if bin_file is True and 'fw_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir + "/img_create_linux/img.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(["chips/" + chipname + "/img_create_linux/img.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img.bin")
                d_addrs.append(hex(pt_parcel['fw_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo.bin")
                d_addrs.append(hex(pt_parcel['fw_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img.bin")
                d_addrs.append(hex(pt_parcel['fw_addr'] + offset)[2:])

        if d0fw is True and 'fw_d0_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_d0fw.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_d0fw.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_d0fw.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_d0fw.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_d0fw.bin")
                d_addrs.append(hex(pt_parcel['fw_d0_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_d0fw.bin")
                d_addrs.append(hex(pt_parcel['fw_d0_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_d0fw.bin")
                d_addrs.append(hex(pt_parcel['fw_d0_addr'] + offset)[2:])

        if imgloader is True and 'imgloader_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_imgloader.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_imgloader.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_imgloader.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_imgloader.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_imgloader.bin")
                d_addrs.append(hex(pt_parcel['imgloader_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_imgloader.bin")
                d_addrs.append(hex(pt_parcel['imgloader_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_imgloader.bin")
                d_addrs.append(hex(pt_parcel['imgloader_addr'] + offset)[2:])

        if sbi is True and 'sbi_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_sbi.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_sbi.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_sbi.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_sbi.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_sbi.bin")
                d_addrs.append(hex(pt_parcel['sbi_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_sbi.bin")
                d_addrs.append(hex(pt_parcel['sbi_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_sbi.bin")
                d_addrs.append(hex(pt_parcel['sbi_addr'] + offset)[2:])

        if kernel is True and 'kernel_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_kernel.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_kernel.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_kernel.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_kernel.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_kernel.bin")
                d_addrs.append(hex(pt_parcel['kernel_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_kernel.bin")
                d_addrs.append(hex(pt_parcel['kernel_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_kernel.bin")
                d_addrs.append(hex(pt_parcel['kernel_addr'] + offset)[2:])

        if imtb is True and 'imtb_addr' in pt_parcel:
            d_files.append("chips/" + chipname + "/img_create_linux/imtb.bin")
            d_addrs.append(hex(pt_parcel['imtb_addr'])[2:])

        if rootfs is True and 'rootfs_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_rootfs.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_rootfs.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_rootfs.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_rootfs.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_rootfs.bin")
                d_addrs.append(hex(pt_parcel['rootfs_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_rootfs.bin")
                d_addrs.append(hex(pt_parcel['rootfs_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_rootfs.bin")
                d_addrs.append(hex(pt_parcel['rootfs_addr'] + offset)[2:])

        if dtb is True and 'dtb_addr' in pt_parcel:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_dtb.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_dtb.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_dtb.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_dtb.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_dtb.bin")
                d_addrs.append(hex(pt_parcel['dtb_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_dtb.bin")
                d_addrs.append(hex(pt_parcel['dtb_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_dtb.bin")
                d_addrs.append(hex(pt_parcel['dtb_addr'] + offset)[2:])

        conf_addr = pt_parcel.get('conf_addr', None)
        if ro_params is not None and len(ro_params) > 0 and conf_addr is not None:
            bl_ro_device_tree.bl_ro_params_device_tree(ro_params,
                                                       chipnamedir + "/device_tree/ro_params.dtb")
            d_files.append("chips/" + chipname + "/device_tree/ro_params.dtb")
            d_addrs.append(hex(pt_parcel['conf_addr'])[2:])

        if media is True and 'media_addr' in pt_parcel:
            d_files.append("chips/" + chipname + "/img_create_linux/media.bin")
            d_addrs.append(hex(pt_parcel['media_addr'])[2:])

        if mfg is True:
            offset = 0x1000
            if chiptype == "bl808":
                offset = 0x1000
            if bind_bootinfo is True:
                whole_img = chipnamedir + "/img_create_linux/whole_img_mfg.bin"
                whole_img_len = offset + os.path.getsize(chipnamedir +
                                                         "/img_create_linux/img_mfg.bin")
                whole_img_data = bl_create_flash_default_data(whole_img_len)
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/bootinfo_mfg.bin"])[0]
                whole_img_data[0:len(filedata)] = filedata
                filedata = bl_get_file_data(
                    ["chips/" + chipname + "/img_create_linux/img_mfg.bin"])[0]
                whole_img_data[offset:offset + len(filedata)] = filedata
                fp = open(whole_img, 'wb+')
                fp.write(whole_img_data)
                fp.close()
                d_files.append("chips/" + chipname + "/img_create_linux/whole_img_mfg.bin")
                d_addrs.append(hex(pt_parcel['mfg_addr'])[2:])
            else:
                d_files.append("chips/" + chipname + "/img_create_linux/bootinfo_mfg.bin")
                d_addrs.append(hex(pt_parcel['mfg_addr'])[2:])
                d_files.append("chips/" + chipname + "/img_create_linux/img_mfg.bin")
                d_addrs.append(hex(pt_parcel['mfg_addr'] + offset)[2:])

        if len(d_files) > 0 and len(d_addrs) > 0:
            if check_pt_table(pt_parcel, d_files) != True:
                bflb_utils.set_error_code("0082")
                return bflb_utils.errorcode_msg()
            cfg = BFConfigParser()
            cfg.read(self.eflash_loader_cfg)
            self.bflb_write_flash_img(d_addrs, d_files, flash_opt)
            files_str = " ".join(d_files)
            addrs_str = " ".join(d_addrs)
            cfg.set('FLASH_CFG', 'file', files_str)
            cfg.set('FLASH_CFG', 'address', addrs_str)
            cfg.write(self.eflash_loader_cfg, 'w')

            ret = img_create.compress_dir(chipname, "img_create_linux", self.efuse_load_en)
            if ret is not True:
                return bflb_utils.errorcode_msg()
            return True
        else:
            bflb_utils.set_error_code("0060")
            return bflb_utils.errorcode_msg()

    def flasher_download_cfg_ini_gen(self, chipname, chiptype, cpu_type, config):
        bin_d = False
        boot2_d = False
        ro_params_d = None
        pt_parcel = None
        media_bin_d = False
        mfg_bin_d = False
        dtb_bin_d = False
        d0_bin_d = False
        imtb_bin_d = False
        imgloader_bin_d = False
        sbi_bin_d = False
        kernel_bin_d = False
        rootfs_bin_d = False
        boot2_en = False
        dts_bytearray = None

        partition_path = os.path.join(chip_path, chipname, "partition/partition.bin")
        error = "Please check your partition table file"
        self.config = config

        cfg = BFConfigParser()
        cfg.read(self.eflash_loader_cfg)
        if cfg.has_option("FLASH_CFG", "flash_id"):
            flash_id = cfg.get("FLASH_CFG", "flash_id")
            bflb_utils.printf("========= chip flash id: %s =========" % flash_id)
            if chiptype == "bl808" or chiptype == "bl616":
                if bflb_flash_select.update_flash_cfg(chipname, chiptype, flash_id,
                                                      self.bh_cfg_file, False,
                                                      "BOOTHEADER_GROUP0_CFG") is False:
                    error = "flash_id:" + flash_id + " do not support"
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("0069")
                    return bflb_utils.errorcode_msg()
        else:
            error = "Do not find flash_id in eflash_loader_cfg.ini"
            bflb_utils.printf(error)
            bflb_utils.set_error_code("0070")
            return bflb_utils.errorcode_msg()

        if config["check_box"]['ro_params_download'] is True:
            ro = config['input_path']['dts_input']
            if not os.path.isfile(ro):
                bflb_utils.printf("Don't Find %s as bl_factory image" % ro)
                error = "Don't Find %s as bl_factory image" % ro
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0079")
                return bflb_utils.errorcode_msg()
            if ro is not None and len(ro) > 0:
                ro_params_d = ro
                try:
                    dts_hex = bl_ro_device_tree.bl_dts2hex(ro_params_d)
                    dts_bytearray = bflb_utils.hexstr_to_bytearray(dts_hex)
                except Exception as e:
                    dts_bytearray = None

        pt = config['input_path']['pt_bin_input']
        if pt is not None and len(pt) > 0:
            pt_helper = partition.PtCreater(pt)
            # TODO name should not a fixed value
            if config["check_box"]['partition_download'] is True:
                bflb_utils.printf("create partition.bin, pt_new is True")
                pt_helper.create_pt_table(partition_path)
            pt_parcel, name_list = pt_helper.construct_table()
        else:
            bflb_utils.set_error_code("0076")
            return bflb_utils.errorcode_msg()

        if config["check_box"]["encrypt"] is True:
            aes_key = config["param"]["aes_key"].replace(" ", "")
            aes_iv = config["param"]["aes_iv"].replace(" ", "")
            if (verify_hex_num(aes_key) is True) and ((len(aes_key) == 32) or (len(aes_key) == 48) or (len(aes_key) == 64)):
                pass
            else:
                error = "Error: Please check AES key data and len"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0077")
                return bflb_utils.errorcode_msg()
            if (verify_hex_num(aes_iv) is not True) or (len(aes_iv) != 32):
                error = "Error: Please check AES iv data and len"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0078")
                return bflb_utils.errorcode_msg()
            if aes_iv.endswith("00000000") is False:
                error = "AES IV should endswith 4 bytes zero"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0073")
                return bflb_utils.errorcode_msg()

        if config["check_box"]["sign"] is True:
            if not config["input_path"]["publickey"]:
                error = "Please set public key"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0066")
                return bflb_utils.errorcode_msg()
            if not config["input_path"]["privatekey"]:
                error = "Please set private key"
                bflb_utils.printf(error)
                bflb_utils.set_error_code("0067")
                return bflb_utils.errorcode_msg()

        # set boot2 header crc and hash ignore
        cfg_t = BFConfigParser()
        cfg_t.read(self.bh_cfg_file)
        if "BOOTHEADER_CPU0_CFG" in cfg_t.sections():
            bootheader_section_name = "BOOTHEADER_CPU0_CFG"
        elif "BOOTHEADER_GROUP0_CFG" in cfg_t.sections():
            bootheader_section_name = "BOOTHEADER_GROUP0_CFG"
        else:
            bootheader_section_name = "BOOTHEADER_CFG"
        crc_ignore = cfg_t.get(bootheader_section_name, 'crc_ignore')
        hash_ignore = cfg_t.get(bootheader_section_name, 'hash_ignore')
        cfg_t.set(bootheader_section_name, 'crc_ignore', 1)
        cfg_t.set(bootheader_section_name, 'hash_ignore', 1)
        cfg_t.write(self.bh_cfg_file)

        if chiptype == "bl808":
            cfg_t.read(self.bh_cfg_file)
            cfg_t.set("BOOTHEADER_GROUP0_CFG", 'crc_ignore', crc_ignore)
            cfg_t.set("BOOTHEADER_GROUP0_CFG", 'm0_image_address_offset', "0x00000000")
            cfg_t.set("BOOTHEADER_GROUP0_CFG", 'd0_image_address_offset', "0x00000000")
            cfg_t.set("BOOTHEADER_GROUP0_CFG", 'lp_image_address_offset', "0x00000000")
            cfg_t.set("BOOTHEADER_GROUP1_CFG", 'm0_image_address_offset', "0x00000000")
            cfg_t.set("BOOTHEADER_GROUP1_CFG", 'd0_image_address_offset', "0x00000000")
            cfg_t.set("BOOTHEADER_GROUP1_CFG", 'lp_image_address_offset', "0x00000000")
            cfg_t.write(self.bh_cfg_file)

        # boot2 image gen
        if config["check_box"]['boot2_download'] is True:
            if chiptype == "bl808":
                boot2 = "%s|UNUSED|UNUSED|" % config['input_path']['boot2_bin_input']
                cfg_t.read(self.bh_cfg_file)
                cfg_t.set("BOOTHEADER_GROUP0_CFG", 'group_image_offset', "0x2000")
                cfg_t.write(self.bh_cfg_file)
            else:
                boot2 = config['input_path']['boot2_bin_input']
            if boot2 is not None and len(boot2) > 0:
                self.bflb_image_bootheader_gen(True, config['param']["chip_xtal"],
                                               self.bh_cfg_file, config["check_box"]['encrypt'],
                                               config["check_box"]['sign'], chipname, chiptype,
                                               cpu_type, boot2_en)
                f_org = os.path.join(chip_path, chipname, "img_create_linux",
                                     "img_create_cfg_boot2.conf")
                f = os.path.join(chip_path, chipname, "img_create_linux",
                                 "img_create_cfg_boot2.ini")
                if os.path.isfile(f) is False:
                    shutil.copyfile(f_org, f)
                self.bflb_image_gen(chipname, chiptype, cpu_type, "boot2", boot2,
                                    config["param"]['aes_key'], config["param"]['aes_iv'],
                                    config["input_path"]["publickey"],
                                    config["input_path"]["privatekey"], f)
                boot2_d = True

        # recover bootheader cfg file crc and hash ignore
        cfg_t = BFConfigParser()
        cfg_t.read(self.bh_cfg_file)
        cfg_t.set(bootheader_section_name, 'crc_ignore', crc_ignore)
        cfg_t.set(bootheader_section_name, 'hash_ignore', hash_ignore)
        cfg_t.write(self.bh_cfg_file)

        # firmware image gen
        if config["check_box"]['bin_download'] is True:
            if chiptype == "bl808":
                bin = "%s|UNUSED|UNUSED|" % config['input_path']['cfg2_bin_input']
                cfg_t.read(self.bh_cfg_file)
                cfg_t.set("BOOTHEADER_GROUP0_CFG", 'group_image_offset',
                          "0x%x" % (pt_parcel['fw_addr'] + 0x1000))
                cfg_t.write(self.bh_cfg_file)
            else:
                bin = config['input_path']['cfg2_bin_input']
            if bin is not None and len(bin) > 0:
                temp = bin.split("|")[0]
                if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                    length = len(dts_bytearray)
                    with open(temp, "rb") as fp:
                        bin_byte = fp.read()
                        bin_bytearray = bytearray(bin_byte)
                        bin_bytearray[1032:1032 + length] = dts_bytearray
                    filedir, ext = os.path.splitext(temp)
                    temp = filedir + "_rfpa" + ext
                    with open(temp, "wb") as fp:
                        fp.write(bin_bytearray)
                    bin = temp
                    if chiptype == "bl808":
                        bin = "%s|UNUSED|UNUSED|" % bin
                self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                               self.bh_cfg_file, config["check_box"]['encrypt'],
                                               config["check_box"]['sign'], chipname, chiptype,
                                               cpu_type, boot2_en)
                self.bflb_image_gen(chipname, chiptype, cpu_type, "fw", bin,
                                    config["param"]['aes_key'], config["param"]['aes_iv'],
                                    config["input_path"]["publickey"],
                                    config["input_path"]["privatekey"])
                self.bflb_ota_bin_gen(chipname, chiptype, cpu_type, config["param"]["version"],
                                      config["param"]["ota"])
                bin_d = True

        # image loader gen
        if 'imgloader_download' in config["check_box"] and 'imgloader_bin_input' in config[
                'input_path']:
            if config["check_box"]['imgloader_download'] is True:
                if chiptype == "bl808":
                    imgloader_bin = "UNUSED|%s|UNUSED|" % config['input_path'][
                        'imgloader_bin_input']
                    cfg_t.read(self.bh_cfg_file)
                    cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                              "0x%x" % (pt_parcel['imgloader_addr'] + 0x1000))
                    cfg_t.write(self.bh_cfg_file)
                else:
                    imgloader_bin = config['input_path']['imgloader_bin_input']
                if imgloader_bin is not None and len(imgloader_bin) > 0:
                    temp = imgloader_bin.split("|")[1]
                    if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                        length = len(dts_bytearray)
                        with open(temp, "rb") as fp:
                            bin_byte = fp.read()
                            bin_bytearray = bytearray(bin_byte)
                            bin_bytearray[1032:1032 + length] = dts_bytearray
                        filedir, ext = os.path.splitext(temp)
                        temp = filedir + "_rfpa" + ext
                        with open(temp, "wb") as fp:
                            fp.write(bin_bytearray)
                        imgloader_bin = temp
                        if chiptype == "bl808":
                            imgloader_bin = "UNUSED|%s|UNUSED|" % imgloader_bin
                    self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                                   self.bh_cfg_file,
                                                   config["check_box"]['encrypt'],
                                                   config["check_box"]['sign'], chipname, chiptype,
                                                   "Group1", boot2_en)
                    self.bflb_image_gen(chipname, chiptype, "Group1", "imgloader", imgloader_bin,
                                        config["param"]['aes_key'], config["param"]['aes_iv'],
                                        config["input_path"]["publickey"],
                                        config["input_path"]["privatekey"])
                    imgloader_bin_d = True

        # sbi image gen
        if 'sbi_download' in config["check_box"] and 'sbi_bin_input' in config['input_path']:
            if config["check_box"]['sbi_download'] is True:
                if chiptype == "bl808":
                    sbi_bin = "UNUSED|%s|UNUSED|" % config['input_path']['sbi_bin_input']
                    cfg_t.read(self.bh_cfg_file)
                    cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                              "0x%x" % (pt_parcel['sbi_addr'] + 0x1000))
                    cfg_t.write(self.bh_cfg_file)
                else:
                    sbi_bin = config['input_path']['sbi_bin_input']
                if sbi_bin is not None and len(sbi_bin) > 0:
                    temp = sbi_bin.split("|")[1]
                    if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                        length = len(dts_bytearray)
                        with open(temp, "rb") as fp:
                            bin_byte = fp.read()
                            bin_bytearray = bytearray(bin_byte)
                            bin_bytearray[1032:1032 + length] = dts_bytearray
                        filedir, ext = os.path.splitext(temp)
                        temp = filedir + "_rfpa" + ext
                        with open(temp, "wb") as fp:
                            fp.write(bin_bytearray)
                        sbi_bin = temp
                        if chiptype == "bl808":
                            sbi_bin = "UNUSED|%s|UNUSED|" % sbi_bin
                    self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                                   self.bh_cfg_file,
                                                   config["check_box"]['encrypt'],
                                                   config["check_box"]['sign'], chipname, chiptype,
                                                   "Group1", boot2_en)
                    self.bflb_image_gen(chipname, chiptype, "Group1", "sbi", sbi_bin,
                                        config["param"]['aes_key'], config["param"]['aes_iv'],
                                        config["input_path"]["publickey"],
                                        config["input_path"]["privatekey"])
                    sbi_bin_d = True

        # kernel image gen
        if 'kernel_download' in config["check_box"] and 'kernel_bin_input' in config['input_path']:
            if config["check_box"]['kernel_download'] is True:
                if chiptype == "bl808":
                    kernel_bin = "UNUSED|%s|UNUSED|" % config['input_path']['kernel_bin_input']
                    cfg_t.read(self.bh_cfg_file)
                    cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                              "0x%x" % (pt_parcel['kernel_addr'] + 0x1000))
                    cfg_t.write(self.bh_cfg_file)
                else:
                    kernel_bin = config['input_path']['kernel_bin_input']
                if kernel_bin is not None and len(kernel_bin) > 0:
                    temp = kernel_bin.split("|")[1]
                    if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                        length = len(dts_bytearray)
                        with open(temp, "rb") as fp:
                            bin_byte = fp.read()
                            bin_bytearray = bytearray(bin_byte)
                            bin_bytearray[1032:1032 + length] = dts_bytearray
                        filedir, ext = os.path.splitext(temp)
                        temp = filedir + "_rfpa" + ext
                        with open(temp, "wb") as fp:
                            fp.write(bin_bytearray)
                        kernel_bin = temp
                        if chiptype == "bl808":
                            kernel_bin = "UNUSED|%s|UNUSED|" % kernel_bin
                    self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                                   self.bh_cfg_file,
                                                   config["check_box"]['encrypt'],
                                                   config["check_box"]['sign'], chipname, chiptype,
                                                   "Group1", boot2_en)
                    self.bflb_image_gen(chipname, chiptype, "Group1", "kernel", kernel_bin,
                                        config["param"]['aes_key'], config["param"]['aes_iv'],
                                        config["input_path"]["publickey"],
                                        config["input_path"]["privatekey"])
                    kernel_bin_d = True

        # rootfs image gen
        if 'rootfs_download' in config["check_box"] and 'rootfs_bin_input' in config['input_path']:
            if config["check_box"]['rootfs_download'] is True:
                if chiptype == "bl808":
                    rootfs_bin = "UNUSED|%s|UNUSED|" % config['input_path']['rootfs_bin_input']
                    cfg_t.read(self.bh_cfg_file)
                    cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                              "0x%x" % (pt_parcel['rootfs_addr'] + 0x1000))
                    cfg_t.write(self.bh_cfg_file)
                else:
                    rootfs_bin = config['input_path']['rootfs_bin_input']
                if rootfs_bin is not None and len(rootfs_bin) > 0:
                    temp = rootfs_bin.split("|")[1]
                    if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                        length = len(dts_bytearray)
                        with open(temp, "rb") as fp:
                            bin_byte = fp.read()
                            bin_bytearray = bytearray(bin_byte)
                            bin_bytearray[1032:1032 + length] = dts_bytearray
                        filedir, ext = os.path.splitext(temp)
                        temp = filedir + "_rfpa" + ext
                        with open(temp, "wb") as fp:
                            fp.write(bin_bytearray)
                        rootfs_bin = temp
                        if chiptype == "bl808":
                            rootfs_bin = "UNUSED|%s|UNUSED|" % rootfs_bin
                    self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                                   self.bh_cfg_file,
                                                   config["check_box"]['encrypt'],
                                                   config["check_box"]['sign'], chipname, chiptype,
                                                   "Group1", boot2_en)
                    self.bflb_image_gen(chipname, chiptype, "Group1", "rootfs", rootfs_bin,
                                        config["param"]['aes_key'], config["param"]['aes_iv'],
                                        config["input_path"]["publickey"],
                                        config["input_path"]["privatekey"])
                    rootfs_bin_d = True

        # dtb image gen
        if 'dtb_download' in config["check_box"] and 'dtb_bin_input' in config['input_path']:
            if config["check_box"]['dtb_download'] is True:
                if chiptype == "bl808":
                    dtb_bin = "UNUSED|%s|UNUSED|" % config['input_path']['dtb_bin_input']
                    cfg_t.read(self.bh_cfg_file)
                    cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                              "0x%x" % (pt_parcel['dtb_addr'] + 0x1000))
                    cfg_t.write(self.bh_cfg_file)
                else:
                    dtb_bin = config['input_path']['dtb_bin_input']
                if dtb_bin is not None and len(dtb_bin) > 0:
                    temp = dtb_bin.split("|")[1]
                    if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                        length = len(dts_bytearray)
                        with open(temp, "rb") as fp:
                            bin_byte = fp.read()
                            bin_bytearray = bytearray(bin_byte)
                            bin_bytearray[1032:1032 + length] = dts_bytearray
                        filedir, ext = os.path.splitext(temp)
                        temp = filedir + "_rfpa" + ext
                        with open(temp, "wb") as fp:
                            fp.write(bin_bytearray)
                        dtb_bin = temp
                        if chiptype == "bl808":
                            dtb_bin = "UNUSED|%s|UNUSED|" % dtb_bin
                    self.bflb_image_bootheader_gen(False, config['param']["chip_xtal"],
                                                   self.bh_cfg_file,
                                                   config["check_box"]['encrypt'],
                                                   config["check_box"]['sign'], chipname, chiptype,
                                                   "Group1", boot2_en)
                    self.bflb_image_gen(chipname, chiptype, "Group1", "dtb", dtb_bin,
                                        config["param"]['aes_key'], config["param"]['aes_iv'],
                                        config["input_path"]["publickey"],
                                        config["input_path"]["privatekey"])
                    dtb_bin_d = True

        if config["check_box"]['media_download'] is True:
            media_bin = config['input_path']['media_bin_input']
            if media_bin is not None and len(media_bin) > 0:
                try:
                    shutil.copyfile(
                        media_bin,
                        os.path.join(chip_path, chipname, "img_create_linux", "media.bin"))
                except Exception as e:
                    bflb_utils.printf(e)
            media_bin_d = True

        if config["check_box"]['use_romfs'] is True:
            romfs_dir = config['input_path']['romfs_dir_input']
            if romfs_dir is not None and len(romfs_dir) > 0:
                ret = generate_romfs_img(
                    romfs_dir, os.path.join(chip_path, chipname, "img_create_linux", "media.bin"))
                if ret != 0:
                    bflb_utils.printf('ERROR, ret %s.' % ret)
                    error = 'ERROR, ret %s.' % ret
                    bflb_utils.printf(error)
                    bflb_utils.set_error_code("007A")
                    return bflb_utils.errorcode_msg()
                media_bin_d = True

        if config["check_box"]['mfg_download'] is True:
            if chiptype == "bl808":
                mfg = "%s|UNUSED|UNUSED|" % config['input_path']['mfg_bin_input']
                cfg_t.read(self.bh_cfg_file)
                cfg_t.set("BOOTHEADER_GROUP1_CFG", 'group_image_offset',
                          "0x%x" % (pt_parcel['mfg_addr'] + 0x1000))
                cfg_t.write(self.bh_cfg_file)
            else:
                mfg = config['input_path']['mfg_bin_input']
            if mfg is not None and len(mfg) > 0:
                temp = mfg.split("|")[0]
                if parse_rfpa(temp) == b'BLRFPARA' and dts_bytearray:
                    length = len(dts_bytearray)
                    with open(temp, "rb") as fp:
                        bin_byte = fp.read()
                        bin_bytearray = bytearray(bin_byte)
                        bin_bytearray[1032:1032 + length] = dts_bytearray
                    filedir, ext = os.path.splitext(temp)
                    temp = filedir + "_rfpa" + ext
                    with open(temp, "wb") as fp:
                        fp.write(bin_bytearray)
                    mfg = temp
                    if chiptype == "bl808":
                        mfg = "%s|UNUSED|UNUSED|" % mfg
                self.bflb_mfg_bootheader_gen(hex(pt_parcel['mfg_addr']),
                                             config['param']["chip_xtal"], self.bh_cfg_file,
                                             chipname, chiptype, cpu_type)
                f_org = os.path.join(chip_path, chipname, "img_create_linux",
                                     "img_create_cfg_mfg.conf")
                f = os.path.join(chip_path, chipname, "img_create_linux", "img_create_cfg_mfg.ini")
                if os.path.isfile(f) is False:
                    shutil.copyfile(f_org, f)
                self.bflb_image_gen(chipname, chiptype, cpu_type, "mfg", mfg,
                                    config["param"]['aes_key'], config["param"]['aes_iv'],
                                    config["input_path"]["publickey"],
                                    config["input_path"]["privatekey"], f)
                mfg_bin_d = True
        return self.bflb_flasher_eflash_loader_cfg(chipname, chiptype, bin_d, boot2_d, ro_params_d,
                                                   pt_parcel, media_bin_d, mfg_bin_d, d0_bin_d,
                                                   imtb_bin_d, imgloader_bin_d, sbi_bin_d,
                                                   kernel_bin_d, rootfs_bin_d, dtb_bin_d)

    def flasher_download_thread(self, chipname, chiptype, act, config, callback=None):
        self.config = config
        error = None
        cpu_type = None
        ota_path = os.path.join(chip_path, chipname, "ota")
        imgcreate_path = os.path.join(chip_path, chipname, "img_create_linux")
        if not os.path.exists(ota_path):
            os.makedirs(ota_path)
        if not os.path.exists(imgcreate_path):
            os.makedirs(imgcreate_path)

        if chipname in gol.cpu_type.keys():
            cpu_type = gol.cpu_type[chipname][0]

        if act != "build" and act != "download":
            return "no such action!"
        try:
            # config loader ini
            if config['param']['interface_type'] == 'uart':
                uart = config['param']['comport_uart']
                uart_brd = config['param']['speed_uart']
                if not uart_brd.isdigit():
                    error = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
                    bflb_utils.printf(error)
                    return error
                bflb_utils.printf("========= Interface is Uart =========")
                self.bflb_flasher_uart_cfg(uart, uart_brd)
            elif config['param']['interface_type'] == 'jlink':
                jlink_brd = config['param']['speed_jlink']
                if not jlink_brd.isdigit():
                    error = '{"ErrorCode":"FFFF","ErrorMsg":"BAUDRATE MUST BE DIGIT"}'
                    bflb_utils.printf(error)
                    return error
                bflb_utils.printf("========= Interface is JLink =========")
                self.bflb_flasher_jlink_cfg(rate=jlink_brd)
            elif config['param']['interface_type'] == 'cklink':
                bflb_utils.printf("========= Interface is CKLink =========")
                self.bflb_flasher_cklink_cfg()
            else:
                openocd_brd = config['param']['speed_jlink']
                bflb_utils.printf("========= Interface is Openocd =========")
                self.bflb_flasher_openocd_cfg(rate=openocd_brd)

            cfg = BFConfigParser()
            cfg.read(self.eflash_loader_cfg)
            if "dl_verify" in config["param"].keys():
                if config["param"]["verify"] == "True":
                    cfg.set('LOAD_CFG', 'verify', '1')
                else:
                    cfg.set('LOAD_CFG', 'verify', '0')
            cfg.write(self.eflash_loader_cfg, 'w')

            bflb_xtal = config["param"]["chip_xtal"]
            bflb_utils.printf("eflash loader bin is " + get_eflash_loader(bflb_xtal))
            eflash_loader_bin = os.path.join(chip_path, chipname,
                                             "eflash_loader/" + get_eflash_loader(bflb_xtal))

            if config["check_box"]["single_download"] is True and act == "download":
                cfg = BFConfigParser()
                cfg.read(self.eflash_loader_cfg)
                files_str = config["input_path"]["img_bin_input"]
                files_single = os.path.join(imgcreate_path, "img_single.bin")
                shutil.copyfile(files_str, files_single)
                files_single = "chips/" + chipname + '/img_create_linux/img_single.bin'
                addrs_str = config["param"]["addr"].replace("0x", "")
                cfg.set('FLASH_CFG', 'file', files_single)
                cfg.set('FLASH_CFG', 'address', addrs_str)
                cfg.write(self.eflash_loader_cfg, 'w')
                self.eflash_loader_t = eflash_loader.BflbEflashLoader(chipname, chiptype)
                if not config["param"]["comport_uart"] and config['param'][
                        'interface_type'] == 'uart':
                    error = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
                    bflb_utils.printf(error)
                    return error
                if 'ckb_erase_all' in config["check_box"]:
                    if config["check_box"]['ckb_erase_all'] == "True":
                        self.bflb_flasher_erase_all(True)
                    else:
                        self.bflb_flasher_erase_all(False)
                if config['param']['interface_type'] == 'uart':
                    options = ["--write", "--flash", "-p", uart]
                    args = parser_eflash.parse_args(options)
                    error = self.eflash_loader_t.efuse_flash_loader(args, self.eflash_loader_cfg,
                                                                    eflash_loader_bin, callback,
                                                                    None, None)
                    self.eflash_loader_t.object_status_clear()
                else:
                    options = ["--write", "--flash"]
                    args = parser_eflash.parse_args(options)
                    error = self.eflash_loader_t.efuse_flash_loader(args, self.eflash_loader_cfg,
                                                                    eflash_loader_bin, callback,
                                                                    None, None)
                    self.eflash_loader_t.object_status_clear()
            # generation partition table/boot2/fw bin files and rf files
            elif self.flasher_download_cfg_ini_gen(chipname, chiptype, cpu_type, config) is True:
                if act == "download":
                    # burn into flash
                    self.eflash_loader_t = eflash_loader.BflbEflashLoader(chipname, chiptype)
                    self.eflash_loader_t.set_config_file(self.bh_cfg_file, "")
                    if not config["param"]["comport_uart"] and config['param'][
                            'interface_type'] == 'uart':
                        error = '{"ErrorCode":"FFFF","ErrorMsg":"BFLB INTERFACE HAS NO COM PORT"}'
                        bflb_utils.printf(error)
                        return error
                    if 'ckb_erase_all' in config["check_box"]:
                        if config["check_box"]['ckb_erase_all'] == "True":
                            self.bflb_flasher_erase_all(True)
                        else:
                            self.bflb_flasher_erase_all(False)
                    options = ["--write", "--flash"]
                    if  config["check_box"]["encrypt"] is True or\
                        config["check_box"]["sign"] is True:
                        # options.append("--efuse")
                        options.extend(["--efuse"])
                        if  config["check_box"]["encrypt"] is True or\
                            config["check_box"]["sign"] is True:
                            cfg_file = os.path.join(chip_path, chipname, "img_create_linux",
                                                    "img_create_cfg.ini")
                            options.extend(["--createcfg=" + cfg_file])
                    if config['param']['interface_type'] == 'uart':
                        options.extend(["-p", uart])
                    args = parser_eflash.parse_args(options)
                    error = self.eflash_loader_t.efuse_flash_loader(args, self.eflash_loader_cfg,
                                                                    eflash_loader_bin, callback,
                                                                    self.create_simple_callback,
                                                                    None)
                    self.eflash_loader_t.object_status_clear()
            else:
                error = self.flasher_download_cfg_ini_gen(chipname, chiptype, cpu_type, config)
                bflb_utils.printf("Please check your partition table file")
        except Exception as e:
            traceback.print_exc(limit=10, file=sys.stdout)
            error = str(e)
        finally:
            return error

    def create_simple_callback(self):
        cpu_type = None
        if self.chipname in gol.cpu_type.keys():
            cpu_type = gol.cpu_type[self.chipname][0]
        # values = gol.GlobalVar.values
        values = self.config
        error = self.flasher_download_cfg_ini_gen(self.chipname, self.chiptype, cpu_type, values)
        if error is not True:
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


def flasher_download_cmd(args):
    config = toml.load(args.config)
    chipname = args.chipname
    chiptype = gol.dict_chip_cmd.get(chipname, "unkown chip type")
    if chiptype not in ["bl60x", "bl602", "bl702", "bl702l", "bl808", "bl616", "wb03"]:
        bflb_utils.printf("Chip type is not in bl60x/bl602/bl702/bl702l/bl808/bl616/wb03")
        return
    act = "download"
    obj_iot = BflbLinuxTool(chipname, chiptype)
    obj_iot.flasher_download_thread(chipname, chiptype, act, config)


def iot_download_cmd(args):
    chipname = args.chipname.lower()
    chiptype = gol.dict_chip_cmd.get(chipname, "unkown chip type")
    #partition_cfg = os.path.join(chip_path, chipname, "partition/partition_cfg_2M.toml")
    config = dict()
    config["param"] = dict()
    config["check_box"] = dict()
    config["input_path"] = dict()
    config["param"]["interface_type"] = args.interface.lower()
    config["param"]["comport_uart"] = args.port
    config["param"]["speed_uart"] = str(args.baudrate)
    config["param"]["speed_jlink"] = str(args.baudrate)
    config["param"]["chip_xtal"] = args.xtal
    config["param"]["aes_key"] = ""
    config["param"]["aes_iv"] = ""
    config["check_box"]["partition_download"] = True
    config["check_box"]["bin_download"] = True
    config["check_box"]["media_download"] = False
    config["check_box"]["use_romfs"] = False
    config["check_box"]["mfg_download"] = False
    config["check_box"]["ro_params_download"] = True
    config["check_box"]["ckb_erase_all"] = args.erase
    config["check_box"]["encrypt"] = False
    config["check_box"]["sign"] = False
    config["input_path"]["dts_input"] = args.dts
    #config["input_path"]["pt_bin_input"] = partition_cfg
    config["input_path"]["cfg2_bin_input"] = args.firmware
    config["input_path"]["media_bin_input"] = ""
    config["input_path"]["romfs_dir_input"] = ""
    config["input_path"]["mfg_bin_input"] = ""
    config["input_path"]["publickey"] = ""
    config["input_path"]["privatekey"] = ""
    config["check_box"]["single_download"] = args.single
    config["input_path"]["img_bin_input"] = args.firmware
    config["param"]["addr"] = "0x" + args.addr
    #     config["param"]["version"] = ""
    #     config["param"]["ota"] = ""

    if not args.version:
        config["param"]["version"] = ""
    else:
        config["param"]["version"] = args.version
    if not args.ota:
        config["param"]["ota"] = os.path.join(chip_path, chipname, "ota")
    else:
        config["param"]["ota"] = args.ota

    if not args.pt or not os.path.exists(args.pt):
        config["input_path"]["pt_bin_input"] = os.path.join(chip_path, chipname,
                                                            "partition/partition_cfg_2M.toml")
    else:
        config["input_path"]["pt_bin_input"] = args.pt
    bflb_utils.printf("Partition table is " + config["input_path"]["pt_bin_input"])

    if chiptype == "bl808":
        config["check_box"]["boot2_download"] = True
        boot2_dir = find_boot2(os.path.join(chip_path, chipname, "builtin_imgs"),
                               "boot2_isp_release.bin")
        if boot2_dir:
            config["input_path"]["boot2_bin_input"] = boot2_dir
        if not args.xtal:
            config["param"]["chip_xtal"] = "None"
        else:
            config["param"]["chip_xtal"] = args.xtal
        if not args.dts or not os.path.exists(args.dts):
            config["input_path"]["dts_input"] = os.path.join(
                chip_path, chipname, "device_tree",
                gol.bl_factory_params_file_prefix + "IoTKitA_None.dts")
        else:
            config["input_path"]["dts_input"] = args.dts
    else:
        bflb_utils.printf("Chip type is not correct")
        return
    bflb_utils.printf("Device tree is " + config["input_path"]["dts_input"])

    if config["param"]["interface_type"].lower() == "jlink" and args.baudrate > 12000:
        config["param"]["speed_jlink"] = "12000"

    if args.build:
        act = "build"
    else:
        act = "download"

    obj_iot = BflbLinuxTool(chipname, chiptype)
    obj_iot.flasher_download_thread(chipname, chiptype, act, config)
    if act == "build":
        f_org = os.path.join(chip_path, args.chipname, "img_create_linux", "whole_flash_data.bin")
        f = "firmware.bin"
        try:
            shutil.copyfile(f_org, f)
        except Exception as error:
            pass


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
    parser = argparse.ArgumentParser(description='iot-tool')
    parser.add_argument('--chipname', required=True, help='chip name')
    parser.add_argument("--interface", dest="interface", default="uart", help="interface to use")
    parser.add_argument("--port", dest="port", default=port, help="serial port to use")
    parser.add_argument("--baudrate",
                        dest="baudrate",
                        default=115200,
                        type=int,
                        help="the speed at which to communicate")
    parser.add_argument("--xtal", dest="xtal", help="xtal type")
    parser.add_argument("--dts", dest="dts", help="device tree")
    parser.add_argument("--pt", dest="pt", help="partition table")
    parser.add_argument("--firmware", dest="firmware", required=True, help="image to write")
    parser.add_argument("--build", dest="build", action="store_true", help="build image")
    parser.add_argument("--erase", dest="erase", action="store_true", help="chip erase")
    parser.add_argument("--single", dest="single", action="store_true", help="single download")
    parser.add_argument("--addr", dest="addr", default="0", help="address to write")
    parser.add_argument('--config', dest="config", help='config file')
    parser.add_argument('--ota', dest="ota", help='ota dir')
    parser.add_argument('--version', dest="version", help='version')
    args = parser.parse_args()
    bflb_utils.printf("==================================================")
    bflb_utils.printf("Chip name is %s" % args.chipname)
    if not args.port:
        bflb_utils.printf("Serial port is not found")
    else:
        bflb_utils.printf("Serial port is " + str(port))
    bflb_utils.printf("Baudrate is " + str(args.baudrate))
    bflb_utils.printf("Firmware is " + args.firmware)
    bflb_utils.printf("==================================================")
    if args.config:
        parser.set_defaults(func=flasher_download_cmd)
    else:
        parser.set_defaults(func=iot_download_cmd)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    print(sys.argv)
    run()
