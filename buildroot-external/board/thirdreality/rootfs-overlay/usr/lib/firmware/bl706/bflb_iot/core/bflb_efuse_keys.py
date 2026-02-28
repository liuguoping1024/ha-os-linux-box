# -*- coding: utf-8 -*-

import os
import sys

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_eflash_loader
from libs import bflb_utils

gol.type_chip = "bl60x"


def run_efuse_key():
    bflb_utils.printf(sys.argv[1])
    if (len(sys.argv[1]) != 32):
        bflb_utils.printf("key len is not available")
        sys.exit()
    eflash_loader_t = bflb_eflash_loader.BflbEflashLoader("bl60x", "bl60x")
    eflash_loader_t.efuse_load_aes_key("flash_aes_key", [sys.argv[1], ""], verify=1, shakehand=1)


if __name__ == '__main__':
    run_efuse_key()
