# -*- coding: utf-8 -*-

import os
import sys
import socket
import threading

try:
    import bflb_path
except ImportError:
    from libs import bflb_path

import config as gol
from libs import bflb_utils
from libs import bflb_eflash_loader

gol.type_chip = "bl602"


def udp_socket_recv_server(udp_socket_server, recv_address):
    udp_socket_server.bind(recv_address)
    while True:
        recv_data, recv_addr = udp_socket_server.recvfrom(1024)
        bflb_utils.printf('\n')
        bflb_utils.printf('Recieve:[from IP:<%s>]' % recv_addr[0],
                          recv_data.decode('utf-8') + '\n',
                          end='')
        socket_send_thread = threading.Thread(target=udp_socket_send_server,
                                              args=(udp_socket_server, recv_addr, recv_data))

        socket_send_thread.start()


def udp_socket_send_server(udp_socket_server, send_address, recv_data):
    send_data = recv_data.decode('utf-8')
    eflash_loader_t = bflb_eflash_loader.BflbEflashLoader("bl602", "bl602")
    eflash_loader_t.efuse_flash_loader(send_data.split(" "), None, None)
    eflash_loader_t.object_status_clear()
    bflb_utils.printf('Connect to <%s> and send info successfully' % send_address[0])
    udp_socket_server.sendto(send_data.encode('utf-8'), send_address)


def main():
    udp_socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_address = ('', 8080)
    socket_recv_thread = threading.Thread(target=udp_socket_recv_server,
                                          args=(udp_socket_server, recv_address))
    socket_recv_thread.start()


if __name__ == '__main__':
    main()
