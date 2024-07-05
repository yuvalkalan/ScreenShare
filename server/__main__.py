from server import *


def take_screenshot(q_receive, q_send):
    process_handle = ProcessHandle(q_receive, q_send)
    print(f'create screen process')
    running = True
    while running:
        screen = pyautogui.screenshot()
        frame = np.array(screen)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, resolution(COMPRESS_RESOLUTION), interpolation=cv2.INTER_AREA)
        _, frame = cv2.imencode(IMAGE_TYPE, frame, ENCODING_PARAMS)
        if process_handle.have_data():
            key, value = process_handle.receive()
            if key == CONN_QUIT:
                running = False
                continue
            if key == S_PS_GIVE_SCREEN:
                process_handle.send(S_PC_SET_SCREEN, frame)


def main():
    screenshot_process = ProcessManager(target=take_screenshot)
    screenshot_process.start()
    server = Server()
    server.start()
    # while not server .have_data():
    #     time.sleep(1)
    client = server.accept()
    rate = 0
    timer = datetime.datetime.now()
    while server.running:
        if client.have_data():
            key, value = client.receive()
            try:
                print(f'got new msg from {client.address}; key = {COMMANDS[key]}, value = {value}')
            except ValueError:
                break
            if not client.got_password and key != C_SET_PASSWORD:
                break
            if key == CONN_QUIT:
                server.running = False
                screenshot_process.send(CONN_QUIT)
                break
            elif key == C_SET_PASSWORD:
                if value == 'pass':
                    client.got_password = True
                    print(f'correct password from {client.address}')
                else:
                    print(f'incorrect password from {client.address}')
                    break
            elif key == C_MOUSE_EVENT:
                action, value = value
                if action == cv2.EVENT_MOUSEMOVE:
                    win32api.SetCursorPos(value)
                elif action == cv2.EVENT_LBUTTONDOWN:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
                elif action == cv2.EVENT_LBUTTONUP:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
                elif action == cv2.EVENT_RBUTTONDOWN:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
                elif action == cv2.EVENT_RBUTTONUP:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
                elif action == cv2.EVENT_MBUTTONDOWN:
                    x, y = value
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, x, y, 0, 0)
                elif action == cv2.EVENT_MBUTTONUP:
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
                            pass
            elif key == C_CHANGE_RATE:
                rate = value
        current = datetime.datetime.now()
        if client.got_password and (current-timer).total_seconds() > rate:
            timer = current
            client.send(S_SEND_SCREEN, screenshot_process.get(S_PS_GIVE_SCREEN))
    server.stop()
    screenshot_process.join()
