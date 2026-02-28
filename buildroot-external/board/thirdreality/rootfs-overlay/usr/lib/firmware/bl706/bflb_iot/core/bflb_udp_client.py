# -*- coding: utf-8 -*-

import os
import sys
import time
import signal
import socket
import threading

try:
    import bflb_path
except ImportError:
    from libs import bflb_path
from libs import bflb_utils


def udp_socket_recv_client(udp_socket_client, recv_address):
    udp_socket_client.bind(recv_address)
    while True:
        recv_data, recv_addr = udp_socket_client.recvfrom(1024)
        bflb_utils.printf('Recieve:[from IP:%s>]' % recv_addr[0],
                          recv_data.decode('utf-8') + '\n',
                          end='')


def udp_socket_send_client(udp_socket_client, send_address):
    while True:
        time.sleep(0.1)
        send_data = input('Iuput:')
        if send_data == 'quit':
            udp_socket_client.close()
            bflb_utils.printf('Quit successfully')
            os.kill(os.getpid(), signal.SIGKILL)
        else:
            udp_socket_client.sendto(send_data.encode('utf-8'), send_address)


def main():
    udp_socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bflb_utils.printf('Enter quit exist program')
    # send_address is server address
    send_address = ('10.28.30.59', 8080)
    recv_address = ('', 8081)
    socket_send_thread = threading.Thread(target=udp_socket_send_client,
                                          args=(udp_socket_client, send_address))
    socket_recv_thread = threading.Thread(target=udp_socket_recv_client,
                                          args=(udp_socket_client, recv_address))
    socket_recv_thread.start()
    socket_send_thread.start()


if __name__ == '__main__':
    main()
