from protocol.classes import *
MOUSE_CLICK_EVENTS = [cv2.EVENT_LBUTTONDOWN, cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONDOWN,
                      cv2.EVENT_RBUTTONUP, cv2.EVENT_MBUTTONDOWN, cv2.EVENT_MBUTTONUP]


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

    def handle(self, event, x, y, *args):
        print(event, x, y, args)
        x, y = get_mouse((x, y))
        action, value = None, (x, y)
        if event == cv2.EVENT_MOUSEMOVE:
            self._pos = x, y
        elif event in MOUSE_CLICK_EVENTS:
            action = event
        else:
            print(f'unknown event! {event}')
        if action:
            self._data.append((action, value))
        now_time = datetime.datetime.now()
        if (now_time - self._last_pos).total_seconds() >= MOUSE_MOVE_DELTA:
            self._data.append((cv2.EVENT_MOUSEMOVE, self._pos))
            self._last_pos = now_time


class Client(ConnectionProtocol):
    def __init__(self, code, password):
        super(Client, self).__init__()
        # self._server_ip, self._port = '127.0.0.1', PORT
        self._server_ip, self._port = decode_address(code)
        self._server_ip += NGROK_URL_ENDING
        self._password = password
        self._frame = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._window_name = str((self._server_ip, self._port))
        self._running = False

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, other):
        self._running = other

    @property
    def window_name(self):
        return self._window_name

    def start_listening(self):
        self._socket.connect((self._server_ip, self._port))
        self._set_encryption()
        self.send(C_SET_PASSWORD, self._password)
        self._running = True

    def stop_listening(self):
        self._running = False

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
