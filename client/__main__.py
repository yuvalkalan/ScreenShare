from client import *


def show_screen(q_receive: Queue, q_send: Queue):
    process_handle = ProcessHandle(q_receive, q_send)
    print(f'create screen process')
    first_time = True
    running = True
    new_frame = False
    frame = None
    mouse_handle = MouseHandle()
    _, window_name = process_handle.receive()
    while (first_time or cv2.getWindowProperty(window_name, 0) >= 0) and running:
        if process_handle.have_data():
            key, value = process_handle.receive()
            if key == CONN_QUIT:
                running = False
                continue
            elif key == C_PS_SET_SCREEN:
                frame = value
                new_frame = True
        if new_frame:
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, resolution(CLIENT_RESOLUTION), interpolation=cv2.INTER_AREA)
            first_time = False
            new_frame = False
        if not first_time:
            cv2.imshow(window_name, frame)
            cv2.setMouseCallback(window_name, mouse_handle.handle)
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
                process_handle.send(C_PC_WRITE_STRING, str_lst)
        action, value = mouse_handle.data
        while action is not None:
            process_handle.send(C_PC_MOUSE_EVENT, (action, value))
            action, value = mouse_handle.data
    process_handle.send(CONN_QUIT)


class Avg:
    def __init__(self):
        self._numbers = []
        self._index = 0

    def __iadd__(self, other):
        if len(self._numbers) < MAX_FRAME_BUFFER:
            self._numbers.append(other)
        else:
            self._numbers[self._index] = other
            self._index = (self._index + 1) % MAX_FRAME_BUFFER
        return self

    def value(self):
        if not self._numbers:
            return 0
        return round(sum(self._numbers) / len(self._numbers), 3)


def main():
    code = input('enter server code: ')
    password = input('enter password: ')
    screen_process = ProcessManager(target=show_screen)
    screen_process.start()
    client = Client(code, password)
    client.start_listening()
    screen_process.send(C_PS_SET_WIN_NAME, client.window_name)
    last_loop = 0
    avg = Avg()
    last_rate = 0
    timer = datetime.datetime.now()
    while client.running:
        if client.have_data():
            k, v = client.receive()
            if k == CONN_QUIT:
                client.stop_listening()
                continue
            elif k == S_SEND_SCREEN:
                current = datetime.datetime.now()
                avg += (current - timer).total_seconds()
                timer = current
                screen_process.send(C_PS_SET_SCREEN, v)
                last_loop += 1
                if last_loop == MAX_FRAME_BUFFER:
                    new_rate = avg.value()
                    if last_rate < new_rate:
                        last_rate = new_rate
                        client.send(C_CHANGE_RATE, new_rate)
                    last_loop = 0
        else:
            last_loop -= 1
            if last_loop == -MAX_FRAME_BUFFER:
                new_rate = avg.value()/2
                if last_rate > new_rate:
                    last_rate = new_rate
                    client.send(C_CHANGE_RATE, new_rate)
                last_loop = 0
        if screen_process.have_data():
            key, value = screen_process.receive()
            if key == CONN_QUIT:
                client.running = False
                continue
            elif key == C_PC_WRITE_STRING:
                client.send(C_WRITE_STRING, value)
            elif key == C_PC_MOUSE_EVENT:
                client.send(C_MOUSE_EVENT, value)
    screen_process.send(CONN_QUIT)
    screen_process.join()
