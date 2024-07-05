from protocol.classes import *


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


class Server:
    def __init__(self):
        self._log = Log()
        self._running = False
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
        self._clients: List[ServerConnection] = []
        self._threads: List[threading.Thread] = [threading.Thread(target=self.create_connections)]

    def start_streaming(self):
        self._running = True
        self._start_threads()

    def stop_streaming(self):
        self._running = False
        for thread in self._threads:
            thread.join()
        for client in self._clients:
            client.join()

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, other):
        self._running = other

    def accept(self):
        return self._server_socket.accept()

    def create_connections(self):
        while self._running:
            r, _, _ = select.select([self._server_socket], [], [], 0)
            if r:
                new_client = ServerConnection(self, self._log)
                self._clients.append(new_client)
            time.sleep(1)
        self._server_socket.close()

    def _start_threads(self):
        for thread in self._threads:
            thread.start()


class ServerConnection(ConnectionProtocol):
    def __init__(self, server: Server, log):
        super(ServerConnection, self).__init__()
        self._last_frame = None
        self._log = log
        self._server = server
        self._frame_timer = datetime.datetime.now()-datetime.timedelta(seconds=FRAMES_DELTA+1)
        self._socket, self._address = server.accept()
        self._set_encryption()
        self._threads = [threading.Thread(target=self._start_streaming)]
        self._start_threads()

    @property
    def _running(self):
        return self._server.running

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
        while self._running:
            if self.have_data():
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
            time.sleep(0.1)
        self._log += f'stop streaming to {self._address}'
        self._socket.close()

    def join(self):
        for thread in self._threads:
            thread.join()
