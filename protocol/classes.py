import math
from typing import *
import pickle
import select
from multiprocessing import Process, Queue
from .constants import *
import rsa
import datetime
import os
import time
import socket
from threading import Thread
import cv2
import keyboard
import numpy as np
import win32api
import win32con
from pyngrok import ngrok

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class ConnectionProtocol:
    def __init__(self):
        self._socket = None
        self._public_key, self._private_key = rsa.newkeys(ENC_KEY_SIZE)
        self._other_public = None
        self._key = None
        self._iv = None
        self._cipher = None
        self._encryptor = None
        self._decryptor = None

    def _get_length_of_msg(self):
        try:
            received = self._socket.recv(DATA_LENGTH)
            if received == b'':
                return 0
            return int.from_bytes(received, 'little')
        except Exception as e:
            print(f'cant get length! {e}')
            return 0

    def send(self, key, value=None, protocol=PR_AES):
        try:
            data = key + pickle.dumps(value)
            if protocol == PR_RSA:
                data = rsa.encrypt(data, self._other_public)
            elif protocol == PR_AES:
                to_add = len(self._iv) - len(data) % len(self._iv) - 1
                data = to_add.to_bytes(1, 'little') + b'\x00' * to_add + data
                data = self._encryptor.update(data) + self._encryptor.finalize()
                self._encryptor = self._cipher.encryptor()
            elif protocol == PR_UNENCRYPTED:
                pass
            else:
                raise ValueError
            length = len(data).to_bytes(DATA_LENGTH, 'little')
            self._socket.sendall(length + data)
        except Exception as e:
            print(f'cant send! {e}')

    def receive(self, protocol=PR_AES):
        try:
            length = self._get_length_of_msg()
            if length == 0:
                return CONN_QUIT, None
            data = self._socket.recv(length)
            while len(data) < length:
                data += self._socket.recv(length - len(data))
            if protocol == PR_RSA:
                data = rsa.decrypt(data, self._private_key)
            elif protocol == PR_AES:
                data = self._decryptor.update(data) + self._decryptor.finalize()
                to_remove = data[0]
                data = data[to_remove + 1:]
                self._decryptor = self._cipher.decryptor()
            elif protocol == PR_UNENCRYPTED:
                pass
            else:
                raise ValueError
            key, value = data[:KEY_SIZE], data[KEY_SIZE:length]
            value = pickle.loads(value)
            return key, value
        except Exception as e:
            print(f'cant receive! {e}')
            return CONN_QUIT, None

    def have_data(self):
        r, _, _ = select.select([self._socket], [], [], 0)
        return self._socket in r


class BaseProcess:
    def __init__(self, q_receive: Queue, q_send: Queue):
        self._q_receive = q_receive
        self._q_send = q_send

    def have_data(self):
        return not self._q_receive.empty()

    def receive(self):
        try:
            return self._q_receive.get()
        except Exception as e:
            print(f'cant receive from process! {e}')
            return CONN_QUIT, None

    def send(self, key, value=None):
        try:
            self._q_send.put((key, value))
        except Exception as e:
            print(f'cant send! {e}')

    def get(self, key, value=None):
        self.send(key, value)
        key, value = self.receive()
        return value


class ProcessManager(BaseProcess):
    def __init__(self, target):
        super(ProcessManager, self).__init__(Queue(), Queue())
        self._process = Process(target=target, args=(self._q_send, self._q_receive))

    def start(self):
        self._process.start()

    def join(self):
        self._process.join()


class ProcessHandle(BaseProcess):
    def __init__(self, q_receive: Queue, q_send: Queue):
        super(ProcessHandle, self).__init__(q_receive, q_send)
        self._q_receive = q_receive
        self._q_send = q_send


def resolution(res):
    return int(res * RES_RATIO), res


def get_mouse(pos):
    x, y = pos
    w, h = SCREEN_SIZE
    mouse_ratio = h / CLIENT_RESOLUTION
    return int(mouse_ratio * x), int(mouse_ratio * y)


def to_heb(char):
    return char + 1264


def encode_address(address: Tuple[str, int]) -> str:
    """
    address --> code
    :param address: כתובת רשת (אי-די ופורט)
    :return: קוד אי-די ופורט בבסיס 36
    """
    def encode_id(ngrok_id):
        id_decimal = sum([ord(ngrok_id[i]) * (256 ** (len(ngrok_id) - i - 1)) for i in range(len(ngrok_id))])
        # הפיכת המספר הדצימלי למספר בבסיס 36
        code = ''
        while id_decimal != 0:
            code = chr(id_decimal % 36 + (ord('0') if id_decimal % 36 < 10 else ord('a') - 10)) + code
            id_decimal //= 36
        return code

    def encode_port(port):
        code = ''
        while port != 0:
            code = chr(port % 36 + (ord('0') if port % 36 < 10 else ord('a') - 10)) + code
            port //= 36
        return code

    # הפיכת קוד האי-פי למספר דצימלי
    server_id, server_port = address
    server_id = encode_id(server_id)
    server_port = encode_port(server_port)
    return f'{server_id}:{server_port}'


def decode_address(code: str) -> Tuple[str, int]:
    """
    decoding address (code --> address)
    :param code: קוד השרת בבסיס 36
    :return: כתובת אי-פי של השרת
    """

    def char_value(char: str) -> int:
        """
        ממיר תו מבסיס 36 למספר דצימלי
        convert char --> base36(char)
        :param char: תו להמיר
        :return: ערך מספרי של התו לפי בסיס 36
        """
        char = char.lower()
        return ord(char) - (ord('0') if ord('0') <= ord(char) <= ord('9') else ord('a') - 10)

    def decode_ip(id_code: str) -> str:
        number = sum([char_value(id_code[i]) * (36 ** (len(id_code) - i - 1)) for i in range(len(id_code))])
        # ממיר מבסיס 10 אל מחרוזת
        number_bytes = number.to_bytes(math.ceil(number.bit_length()/8), 'big', signed=False)
        return ''.join([chr(item) for item in number_bytes])

    def decode_port(port_code: str) -> int:
        return sum([char_value(port_code[i]) * (36 ** (len(port_code) - i - 1)) for i in range(len(port_code))])

    server_id, server_port = code.split(':')
    return decode_ip(server_id), decode_port(server_port)
