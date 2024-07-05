from protocol.classes import *


class Log:
    def __init__(self):
        self._log = []
        self._log_index = 0

    def __iadd__(self, other):
        current_time = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S.%f')
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
        self._create_ngrok_tunnel()
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('0.0.0.0', PORT))
        self._server_socket.listen()
        self._clients: Dict[socket.socket, ProcessManager] = {}
        self._frame = None

    def _create_ngrok_tunnel(self):
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

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        for client in self._clients.values():
            client.join()
        try:
            ngrok.disconnect(self._tunnel.public_url)
        except:
            pass

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, other):
        self._running = other

    def accept(self):
        return ServerConnection(self, self._log, self._server_socket)

    def have_data(self):
        r, _, _ = select.select([self._server_socket], [], [], 0)
        return self._server_socket in r


class ServerConnection(ConnectionProtocol):
    def __init__(self, server: Server, log, sock: socket.socket):
        super(ServerConnection, self).__init__()
        self._log = log
        self._server = server
        self._got_password = False
        self._socket, self._address = sock.accept()
        self._set_encryption()

    @property
    def _running(self):
        return self._server.running

    @property
    def address(self):
        return self._address

    @property
    def got_password(self):
        return self._got_password

    @got_password.setter
    def got_password(self, value):
        self._got_password = value

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
