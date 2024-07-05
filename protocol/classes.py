import math
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


class ConnectionProtocol:
    def __init__(self):
        self._socket = None
        self._threads = []

    def send(self, key, value):
        try:
            value = pickle.dumps(value)
            data = key + value
            length = len(data).to_bytes(DATA_LENGTH, 'little')
            self._socket.sendall(length + data)
        except Exception as e:
            print(f'cant send! {e}')

    def _get_length_of_msg(self):
        try:
            received = self._socket.recv(DATA_LENGTH)
            if received == b'':
                return 0
            return int.from_bytes(received, 'little')
        except Exception as e:
            print(f'cant get length! {e}')
            return 0

    def receive(self):
        try:
            length = self._get_length_of_msg()
            if length == 0:
                return S_QUIT, None
            data = self._socket.recv(length)
            while len(data) < length:
                data += self._socket.recv(length-len(data))
            key, value = data[:KEY_SIZE], data[KEY_SIZE:length]
            value = pickle.loads(value)
            return key, value
        except Exception as e:
            print(f'cant receive! {e}')
            return S_QUIT, None

    def _start_threads(self):
        for thread in self._threads:
            thread.start()

    def have_data(self):
        r, _, _ = select.select([self._socket], [], [], 0)
        return self._socket in r


class Server:
    def __init__(self):
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
                new_client = ServerConnection(self)
                print('new client!')
                self._clients.append(new_client)

    def _start_threads(self):
        for thread in self._threads:
            thread.start()


class MouseHandle:
    def __init__(self):
        self._action = None
        self._value = None

    @property
    def data(self):
        action = self._action
        value = self._value
        if action:
            self._action = None
            self._value = None
        return action, value

    def handle(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self._action = S_SET_MOUSE
            self._value = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self._action = S_LMOUSE_CLICK
            self._value = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self._action = S_LMOUSE_RELEASE
            self._value = (x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            self._action = S_RMOUSE_CLICK
            self._value = (x, y)
        elif event == cv2.EVENT_RBUTTONUP:
            self._action = S_RMOUSE_RELEASE
            self._value = (x, y)
        elif event == cv2.EVENT_MBUTTONDOWN:
            self._action = S_SCROLL_CLICK
            self._value = (x, y)
        elif event == cv2.EVENT_MBUTTONUP:
            self._action = S_SCROLL_RELEASE
            self._value = (x, y)


class ServerConnection(ConnectionProtocol):
    def __init__(self, server: Server):
        super(ServerConnection, self).__init__()
        self._socket, self._address = server.accept()
        self._window_name = str(self._address)
        self._mouse_handle = MouseHandle()
        self._threads = [threading.Thread(target=self._start_listening)]
        self._start_threads()

    def _show_screen(self, value):
        frame = cv2.imdecode(value, cv2.IMREAD_COLOR)
        cv2.imshow(self._window_name, frame)
        cv2.setMouseCallback(self._window_name, self._mouse_handle.handle)
        new_char = cv2.waitKey(1)
        if new_char > 0:
            if 224 <= new_char <= 250:
                new_char = to_heb(new_char)
            self.send(S_SET_CHAR, new_char)

    def _start_listening(self):
        while True:
            if self.have_data():
                key, value = self.receive()
                if key == C_QUIT:
                    print('breaking')
                    break
                elif key == C_SEND_SCREEN:
                    self._show_screen(value)
            key, value = self._mouse_handle.data
            if key:
                self.send(key, value)
        cv2.destroyAllWindows()


class Client(ConnectionProtocol):
    def __init__(self, ip, port):
        super(Client, self).__init__()
        self._server_ip, self._port = ip, port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._server_ip, self._port))
        self._threads = [threading.Thread(target=self._start_streaming)]
        self._start_threads()

    @staticmethod
    def _create_frame():
        screen = pyautogui.screenshot()
        frame = np.array(screen)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, resolution(RESOLUTION), interpolation=cv2.INTER_AREA)
        _, frame = cv2.imencode('.jpg', frame, ENCODING_PARAMS)
        return frame

    def _start_streaming(self):
        while True:
            if self.have_data():
                key, value = self.receive()
                if key == S_QUIT:
                    break
                elif key == S_SET_MOUSE:
                    win32api.SetCursorPos(get_mouse(value))
                elif key == S_LMOUSE_CLICK:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                elif key == S_LMOUSE_RELEASE:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                elif key == S_RMOUSE_CLICK:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                elif key == S_RMOUSE_RELEASE:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                elif key == S_SCROLL_CLICK:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, x, y, 0, 0)
                elif key == S_SCROLL_RELEASE:
                    x, y = get_mouse(value)
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, x, y, 0, 0)
                elif key == S_SET_CHAR:
                    print(value, chr(value))
                    keyboard.write(chr(value))
            frame = self._create_frame()
            self.send(C_SEND_SCREEN, frame)


def resolution(res):
    return int(res * RES_RATIO), res


def get_mouse(pos):
    x, y = pos
    w, h = SCREEN_SIZE
    mouse_ratio = h / RESOLUTION
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
