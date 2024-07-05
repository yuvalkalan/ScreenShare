import pyautogui

DATA_LENGTH = 4
PORT = 42069
KEY_SIZE = 2
ENC_KEY_SIZE = 1024
NGROK_URL_ENDING = '.tcp.eu.ngrok.io'

PR_AES = 0
PR_RSA = 1
PR_UNENCRYPTED = 2

COMPRESS_RESOLUTION = 480
CLIENT_RESOLUTION = 720
SCREEN_SIZE = pyautogui.size()
RES_RATIO = 1 + 7/9
MOUSE_MOVE_DELTA = 0.5

ENCODING_PARAMS = [1, 90]
IMAGE_TYPE = '.jpg'

MAX_LOG = 100
MAX_FRAME_BUFFER = 5

CTRL_KEYS = {i+1: f'ctrl+{chr(ord("a")+i)}' for i in range(ord('z')-ord('a')+1)}
SPECIAL_CTRL_KEYS = {127: 'ctrl+backspace', 2490368: 'ctrl+up', 2621440: 'ctrl+down', 2555904: 'ctrl+right',
                     2424832: 'ctrl+left', 3014656: 'ctrl+del', 7536640: 'ctrl+f4'}
for _ctrl_key in SPECIAL_CTRL_KEYS:
    CTRL_KEYS[_ctrl_key] = SPECIAL_CTRL_KEYS[_ctrl_key]
HEB_KEYS = {224+i: ord('א')+i for i in range(ord('ת') - ord('א') + 1)}
SPECIAL_KEYS = {8: 'backspace', 9: 'tab', 13: 'enter', 27: 'esc', 3014656: 'del'}
ARROW_KEYS = {2490368: 'up', 2621440: 'down', 2555904: 'right', 2424832: 'left'}


def _next_key():
    i = 0
    while True:
        yield i
        i += 1


_n = _next_key()

CONN_QUIT = (next(_n)).to_bytes(KEY_SIZE, 'little')

S_SET_PUB_KEY = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SET_AES_KEY = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SEND_SCREEN = (next(_n)).to_bytes(KEY_SIZE, 'little')

S_PS_GIVE_SCREEN = (next(_n)).to_bytes(KEY_SIZE, 'little')

S_PC_SET_SCREEN = (next(_n)).to_bytes(KEY_SIZE, 'little')

C_SET_PUB_KEY = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SET_PASSWORD = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_MOUSE_EVENT = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_WRITE_STRING = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_CHANGE_RATE = (next(_n)).to_bytes(KEY_SIZE, 'little')

C_PC_WRITE_STRING = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_PC_MOUSE_EVENT = (next(_n)).to_bytes(KEY_SIZE, 'little')

C_PS_SET_SOCKET = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_PS_SET_WIN_NAME = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_PS_SET_SCREEN = (next(_n)).to_bytes(KEY_SIZE, 'little')

COMMANDS = {
    CONN_QUIT: 'CONN_QUIT',
    S_SEND_SCREEN: 'S_SEND_SCREEN',
    S_SET_PUB_KEY: 'S_SET_PUB_KEY',
    S_SET_AES_KEY: 'S_SET_AES_KEY',
    C_SET_PUB_KEY: 'C_SET_PUB_KEY',
    C_SET_PASSWORD: 'C_SET_PASSWORD',
    C_MOUSE_EVENT: 'C_MOUSE_EVENT',
    C_WRITE_STRING: 'C_SET_CHAR',
    C_CHANGE_RATE: 'C_CHANGE_RATE',
    S_PS_GIVE_SCREEN: 'S_PS_GIVE_SCREEN',
    S_PC_SET_SCREEN: 'S_PC_SET_SCREEN',
    C_PC_WRITE_STRING: 'C_PC_WRITE_STRING',
    C_PC_MOUSE_EVENT: 'C_PC_MOUSE_EVENT',
    C_PS_SET_SOCKET: 'C_PS_SET_SOCKET',
    C_PS_SET_WIN_NAME: 'C_PS_SET_WIN_NAME',
    C_PS_SET_SCREEN: 'C_PS_SET_SCREEN'
}
