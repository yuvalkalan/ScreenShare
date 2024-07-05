from protocol.classes import *


class Client(ConnectionProtocol):
    def __init__(self, code, password):
        super(Client, self).__init__()
        # self._server_ip, self._port = '127.0.0.1', PORT
        self._server_ip, self._port = decode_address(code)
        self._password = password
        self._frame = None
        self._new_frame = False
        self._avg_frame_rate = 0
        self._server_ip += NGROK_URL_ENDING
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._window_name = str((self._server_ip, self._port))
        self._mouse_handle = MouseHandle()
        self._threads = [threading.Thread(target=self._start_listening), threading.Thread(target=self._show_screen)]
        self._running = False

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, other):
        self._running = other

    def start_listening(self):
        self._socket.connect((self._server_ip, self._port))
        self._set_encryption()
        self._running = True
        self._start_threads()

    def stop_listening(self):
        self._running = False
        for thread in self._threads:
            thread.join()

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
        first_time = True
        while (cv2.getWindowProperty(self._window_name, 0) >= 0 or first_time) and self._running:
            if self._new_frame:
                frame = cv2.imdecode(self._frame, cv2.IMREAD_COLOR)
                frame = cv2.resize(frame, resolution(CLIENT_RESOLUTION), interpolation=cv2.INTER_AREA)
                cv2.imshow(self._window_name, frame)
                first_time = False
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
        self._running = False

    def _start_listening(self):
        self.send(C_SET_PASSWORD, self._password)
        frame_counter = 0
        while self._running:
            if self.have_data():
                key, value = self.receive()
                if key == CONN_QUIT:
                    self._running = False
                    continue
                elif key == S_SEND_SCREEN:
                    self._frame = value
                    self._new_frame = True
                    frame_counter += 1
                    if frame_counter == FRAME_CHECK:
                        self.send(C_GOT_FRAMES)
                        frame_counter = 0
            else:
                print(datetime.datetime.now())
                # time.sleep(0.1)
            key, value = self._mouse_handle.data
            while key:
                self.send(key, value)
                key, value = self._mouse_handle.data
        cv2.destroyAllWindows()
