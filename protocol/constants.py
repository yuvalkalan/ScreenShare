import pyautogui

DATA_LENGTH = 4
PORT = 42069
KEY_SIZE = 2
ENC_KEY_SIZE = 1024
NGROK_URL_ENDING = '.tcp.ngrok.io'

PR_AES = 0
PR_RSA = 1
PR_UNENCRYPTED = 2

COMPRESS_RESOLUTION = 480
CLIENT_RESOLUTION = 720
SCREEN_SIZE = pyautogui.size()
RES_RATIO = 1 + 7/9
MOUSE_MOVE_DELTA = 0.5
FRAMES_DELTA = 0

ENCODING_PARAMS = [1, 90]

MAX_LOG = 100

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

C_SET_PUB_KEY = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SET_PASSWORD = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SET_MOUSE = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_LMOUSE_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_LMOUSE_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_RMOUSE_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_RMOUSE_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SCROLL_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SCROLL_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_WRITE_STRING = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_ON_FIRE = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_NOT_ON_FIRE = (next(_n)).to_bytes(KEY_SIZE, 'little')

COMMANDS = {
    CONN_QUIT: 'CONN_QUIT',
    S_SEND_SCREEN: 'S_SEND_SCREEN',
    S_SET_PUB_KEY: 'S_SET_PUB_KEY',
    S_SET_AES_KEY: 'S_SET_AES_KEY',
    C_SET_PUB_KEY: 'C_SET_PUB_KEY',
    C_SET_PASSWORD: 'C_SET_PASSWORD',
    C_SET_MOUSE: 'C_SET_MOUSE',
    C_LMOUSE_CLICK: 'C_LMOUSE_CLICK',
    C_LMOUSE_RELEASE: 'C_LMOUSE_RELEASE',
    C_RMOUSE_CLICK: 'C_RMOUSE_CLICK',
    C_RMOUSE_RELEASE: 'C_RMOUSE_RELEASE',
    C_SCROLL_CLICK: 'C_SCROLL_CLICK',
    C_SCROLL_RELEASE: 'C_SCROLL_RELEASE',
    C_WRITE_STRING: 'C_SET_CHAR',
    C_ON_FIRE: 'C_ON_FIRE',
    C_NOT_ON_FIRE: 'C_NOT_ON_FIRE'
}
