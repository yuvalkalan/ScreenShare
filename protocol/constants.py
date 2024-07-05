import pyautogui


DATA_LENGTH = 4
PORT = 42069
KEY_SIZE = 2
NGROK_URL_ENDING = '.tcp.ngrok.io'


RESOLUTION = 720
SCREEN_SIZE = pyautogui.size()
RES_RATIO = 1 + 7/9

ENCODING_PARAMS = [1, 90]


def _next_key():
    i = 0
    while True:
        yield i
        i += 1


_n = _next_key()
C_QUIT = (next(_n)).to_bytes(KEY_SIZE, 'little')
C_SEND_SCREEN = (next(_n)).to_bytes(KEY_SIZE, 'little')

S_QUIT = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SET_MOUSE = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_LMOUSE_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_LMOUSE_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_RMOUSE_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_RMOUSE_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SCROLL_CLICK = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SCROLL_RELEASE = (next(_n)).to_bytes(KEY_SIZE, 'little')
S_SET_CHAR = (next(_n)).to_bytes(KEY_SIZE, 'little')
