import datetime
import math
import os
import time
from typing import *
import pickle
import socket
import select
import threading

import cv2
import keyboard
import numpy as np
import win32api
import win32con
from pyngrok import ngrok
from .constants import *

import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class Log:
    def __init__(self):
        self._log = []
        self._log_index = 0

    def __iadd__(self, other):
        current_time = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S%f')
        log_str = f'{current_time} -> {other}'
        print(log_str)
        if len(self._log) >= MAX_LOG:
            self._log[self._log_index] = log_str
            self._log_index = (self._log_index + 1) % MAX_LOG
        else:
            self._log.append(log_str)
        return self


class ConnectionProtocol:
    def __init__(self):
        self._socket = None
        self._threads = []
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

    def _start_threads(self):
        for thread in self._threads:
            thread.start()

    def have_data(self):
        r, _, _ = select.select([self._socket], [], [], 0)
        return self._socket in r


class Server:
    def __init__(self):
        self._log = Log()
        self._tunnel = None
        i = 1
        while not self._tunnel:
            try:
                self._log += 'init ngrok...'
                self._tunnel = ngrok.connect(PORT, "tcp")
            except ngrok.PyngrokError:
                self._log += f'cannot start ngrok... retrying ({i})'
                i += 1
                time.sleep(1)
        self._log += 'successfully start ngrok!'
        url, port = self._tunnel.public_url.replace('tcp://', '').split(':')
        url_id = url.replace(NGROK_URL_ENDING, '')
        ngrok_ip = socket.gethostbyname(url)
        port = int(port)
        ngrok_code = encode_address((url_id, port))
        self._log += f"ngrok details: url='{url} (id={url_id})', ip='{ngrok_ip}', port={port}, code={ngrok_code}"
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('0.0.0.0', PORT))
        self._server_socket.listen()
        self._clients = []
        self._threads = [threading.Thread(target=self.create_connections)]
        self._start_threads()

    def accept(self):
        return self._server_socket.accept()

    def create_connections(self):
        while True:
            r, _, _ = select.select([self._server_socket], [], [], 0)
            if r:
                new_client = ServerConnection(self, self._log)
                self._clients.append(new_client)
            time.sleep(1)

    def _start_threads(self):
        for thread in self._threads:
            thread.start()


class MouseHandle:
    def __init__(self):
        self._pos = None
        self._last_pos = datetime.datetime.now()
        self._data = []

    @property
    def data(self) -> tuple:
        oldest_data = (None, None)
        if self._data:
            oldest_data = self._data.pop(0)
        return oldest_data

    def handle(self, event, x, y, *_):
        x, y = get_mouse((x, y))
        action, value = None, None
        if event == cv2.EVENT_MOUSEMOVE:
            self._pos = x, y
        elif event == cv2.EVENT_LBUTTONDOWN:
            action = C_LMOUSE_CLICK
            value = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            action = C_LMOUSE_RELEASE
            value = (x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            action = C_RMOUSE_CLICK
            value = (x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            action = C_RMOUSE_RELEASE
            value = (x, y)
        elif event == cv2.EVENT_MBUTTONDOWN:
            action = C_SCROLL_CLICK
            value = (x, y)
        elif event == cv2.EVENT_MBUTTONUP:
            action = C_SCROLL_RELEASE
            value = (x, y)
        if action:
            self._data.append((action, value))
        now_time = datetime.datetime.now()
        if (now_time - self._last_pos).total_seconds() >= MOUSE_MOVE_DELTA:
            self._data.append((C_SET_MOUSE, self._pos))
            self._last_pos = now_time


class ServerConnection(ConnectionProtocol):
    def __init__(self, server: Server, log):
        super(ServerConnection, self).__init__()
        self._last_frame = None
        self._log = log
        self._frame_timer = datetime.datetime.now()-datetime.timedelta(seconds=FRAMES_DELTA+1)
        self._socket, self._address = server.accept()
        self._set_encryption()
        self._threads = [threading.Thread(target=self._start_streaming)]
        self._start_threads()

    def _set_encryption(self):
        self._log += f'setting encryption with {self._address}...'
        self.send(S_SET_PUB_KEY, (self._public_key.n, self._public_key.e), PR_UNENCRYPTED)
        key, value = self.receive(PR_UNENCRYPTED)
        n, e = value
        self._other_public = rsa.PublicKey(n, e)
        self._key = os.urandom(32)
        self._iv = os.urandom(16)
        self._cipher = Cipher(algorithms.AES(self._key), modes.CBC(self._iv), backend=default_backend())
        self._encryptor = self._cipher.encryptor()
        self._decryptor = self._cipher.decryptor()
        self._got_password = False
        self.send(S_SET_AES_KEY, (self._key, self._iv), PR_RSA)
        self._log += f'successfully set encryption with {self._address}'

    def _create_and_send_frame(self, delay):
        now_time = datetime.datetime.now()
        if (now_time - self._frame_timer).total_seconds() >= FRAMES_DELTA+delay:
            self._frame_timer = now_time
            screen = pyautogui.screenshot()
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, resolution(COMPRESS_RESOLUTION), interpolation=cv2.INTER_AREA)
            _, frame = cv2.imencode('.jpg', frame, ENCODING_PARAMS)
            self._last_frame = frame
            self.send(S_SEND_SCREEN, self._last_frame)
            return True
        else:
            time.sleep(0.1)
            return False

    def _start_streaming(self):
        self._log += f'start streaming to {self._address}'
        on_fire = False
        delay = 0
        d_param = 1
        while True:
            if self.have_data():
                print(datetime.datetime.now())
                key, value = self.receive()
                try:
                    self._log += f'got new msg from {self._address}; key = {COMMANDS[key]}, value = {value}'
                except:
                    break
                if not self._got_password and key != C_SET_PASSWORD:
                    break
                if key == CONN_QUIT:
                    break
                elif key == C_SET_PASSWORD:
                    if value == 'pass':
                        self._got_password = True
                        self._log += f'correct password from {self._address}'
                    else:
                        self._log += f'incorrect password from {self._address}'
                        break
                elif key == C_SET_MOUSE:
                    win32api.SetCursorPos(value)
                elif key == C_LMOUSE_CLICK:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                elif key == C_LMOUSE_RELEASE:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                elif key == C_RMOUSE_CLICK:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                elif key == C_RMOUSE_RELEASE:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                elif key == C_SCROLL_CLICK:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, x, y, 0, 0)
                elif key == C_SCROLL_RELEASE:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, x, y, 0, 0)
                elif key == C_WRITE_STRING:
                    for char in value:
                        if type(char) == str:
                            keyboard.press_and_release(char)
                        else:
                            try:
                                keyboard.write(chr(char))
                            except ValueError:
                                self._log += f'oops... char: {char}'
                elif key == C_ON_FIRE:
                    on_fire = True
                    delay += 1 / d_param
                    d_param += 1
                elif key == C_NOT_ON_FIRE:
                    on_fire = False
            if self._got_password and not on_fire:
                send = self._create_and_send_frame(delay)
                if send:
                    delay = max(delay - 0.005/d_param, 0)
                    print(delay)
            time.sleep(0.1)
        self._log += f'stop streaming to {self._address}'


class Client(ConnectionProtocol):
    def __init__(self):
        super(Client, self).__init__()
        # self._server_ip, self._port = '127.0.0.1', PORT
        self._server_ip, self._port = decode_address(input('enter server code: '))
        self._password = input('enter password: ')
        self._frame = None
        self._new_frame = False
        self._avg_frame_rate = 0
        self._server_ip += NGROK_URL_ENDING
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._server_ip, self._port))
        self._set_encryption()
        self._window_name = str((self._server_ip, self._port))
        self._mouse_handle = MouseHandle()
        self._threads = [threading.Thread(target=self._start_listening), threading.Thread(target=self._show_screen)]
        self._start_threads()

    def _set_encryption(self):
        print('setting encryption...')
        key, value = self.receive(PR_UNENCRYPTED)
        n, e = value
        self._other_public = rsa.PublicKey(n, e)
        self.send(C_SET_PUB_KEY, (self._public_key.n, self._public_key.e), PR_UNENCRYPTED)
        key, value = self.receive(PR_RSA)
        self._key, self._iv = value
        self._cipher = Cipher(algorithms.AES(self._key), modes.CBC(self._iv), backend=default_backend())
        self._encryptor = self._cipher.encryptor()
        self._decryptor = self._cipher.decryptor()
        print('successfully set encryption')

    def _show_screen(self):
        while True:
            if self._new_frame:
                frame = cv2.imdecode(self._frame, cv2.IMREAD_COLOR)
                frame = cv2.resize(frame, resolution(CLIENT_RESOLUTION), interpolation=cv2.INTER_AREA)
                cv2.imshow(self._window_name, frame)
                cv2.setMouseCallback(self._window_name, self._mouse_handle.handle)
                str_lst = []
                new_char = cv2.waitKeyEx(1)
                while new_char != -1:
                    if new_char in CTRL_KEYS and keyboard.is_pressed('ctrl'):
                        str_lst.append(CTRL_KEYS[new_char])
                    elif new_char in HEB_KEYS:
                        str_lst.append(HEB_KEYS[new_char])
                    elif new_char in ARROW_KEYS:
                        str_lst.append(ARROW_KEYS[new_char])
                    elif new_char in SPECIAL_KEYS:
                        str_lst.append(SPECIAL_KEYS[new_char])
                    else:
                        str_lst.append(new_char)
                    new_char = cv2.waitKeyEx(1)
                if str_lst:
                    self.send(C_WRITE_STRING, str_lst)
                self._new_frame = False
            else:
                time.sleep(0.1)

    def _start_listening(self):
        MAX_FIRING = 4
        self.send(C_SET_PASSWORD, self._password)
        last_data_time = datetime.datetime.now()
        current_time = datetime.datetime.now()
        firing = 0
        on_fire = False
        while True:
            if self.have_data():
                if (current_time-last_data_time).total_seconds() == 0:
                    firing += 1
                    if firing == MAX_FIRING and not on_fire:
                        on_fire = True
                        self.send(C_ON_FIRE)
                        print('set to on fire!')
                    print(firing)
                last_data_time = current_time
                key, value = self.receive()
                if key == CONN_QUIT:
                    print('breaking')
                    break
                elif key == S_SEND_SCREEN:
                    self._frame = value
                    self._new_frame = True
            else:
                firing = 0
                if on_fire:
                    on_fire = False
                    self.send(C_NOT_ON_FIRE)
                    print('set to not on fire!')
                current_time = datetime.datetime.now()
                time.sleep(0.1)
            key, value = self._mouse_handle.data
            while key:
                self.send(key, value)
                key, value = self._mouse_handle.data
        cv2.destroyAllWindows()


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
