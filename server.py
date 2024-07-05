import os
import pickle
import random
import socket
import select
import time

from PIL import Image, ImageGrab
import pyautogui
import io
import threading
import datetime
from constants import *
import pygame


class ShareData:
    def __init__(self):
        self._file = None

    @property
    def file(self):
        f = self._file
        self._file = None
        return f

    @file.setter
    def file(self, value):
        self._file = value

    @property
    def have_new_file(self):
        return self._file is not None


class Server:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(BIND_PARAM)
        self._send_to = None

    def length_of_message(self):
        try:
            data = int.from_bytes(self._socket.recvfrom(LENGTH_BUFFER)[0], 'little')
            if not data:
                return 0
            return data
        except (ConnectionError, socket.timeout):
            return 0

    def send_unencrypted(self, message, address=None):
        data = pickle.dumps(message)
        self._socket.sendto(len(data).to_bytes(LENGTH_BUFFER, 'little'), address)
        while len(data) > PACKET_LIMIT:
            self._socket.sendto(data[:PACKET_LIMIT], address)
            data = data[PACKET_LIMIT:]
        self._socket.sendto(data, address)

    def receive_unencrypted(self):
        try:
            length = self.length_of_message()
            message, addr = self._socket.recvfrom(length)
            delta = length - len(message)
            while delta:
                first_len = len(message)
                message += self._socket.recvfrom(delta)[0]
                delta = max(0, delta - (len(message) - first_len))
            if not message:
                raise ValueError
            return pickle.loads(message), addr
        except Exception as my_exception:
            return my_exception, None

    @property
    def have_data(self):
        try:
            r, _, _ = select.select([self._socket], [], [], 0)
        except ValueError:
            return False
        return r != []


def take_screenshot():
    my_file = io.BytesIO()
    pyautogui.screenshot().save(my_file, format='png')
    my_file.seek(0, 0)
    return my_file


def crop_image(image_file, box=None) -> Image.Image:
    crop = Image.open(image_file).crop(box)
    image_file.seek(0, 0)
    return crop


def show_image(img):
    Image.open(img).show()
    img.seek(0, 0)


def wait_until_new_frame(box=None):
    shot1 = crop_image(take_screenshot(), box)
    shot2 = crop_image(take_screenshot(), box)
    while shot1.tobytes() == shot2.tobytes():
        print('take shot')
        shot2 = crop_image(take_screenshot(), box)


# def create_screen_file(resolution=RESULOTION) -> io.BytesIO:
#     a = datetime.datetime.now()
#     screen_file = take_screenshot()
#     b = datetime.datetime.now()
#     cropped = crop_image(screen_file)
#     c = datetime.datetime.now()
#     resized = cropped.resize(get_resolution(resolution), Image.ANTIALIAS)
#     d = datetime.datetime.now()
#     new_file = io.BytesIO()
#     resized.save('temp.jpg')
#     e = datetime.datetime.now()
#     with open('temp.jpg', 'rb') as my_file:
#         new_file.write(my_file.read())
#     new_file.seek(0, 2)
#     os.remove('temp.jpg')
#     f = datetime.datetime.now()
#     print(f'1 - {b - a}, 2 - {c - b}, 3 - {d - c}, 4 - {e - d}, 5 - {f - e}')
#     return new_file

def create_screen_file():
    snapshot = ImageGrab.grab()
    resized = snapshot.resize(get_resolution(RESULOTION), Image.ANTIALIAS)
    new_file = io.BytesIO()
    resized.save('temp.jpg')
    with open('temp.jpg', 'rb') as my_file:
        new_file.write(my_file.read())
    new_file.seek(0, 2)
    os.remove('temp.jpg')
    return new_file


def send_screen(server, addr, img):
    img.seek(0, 0)
    server.send_unencrypted(img.read(), addr)


def create_file(shared_data: ShareData):
    clock = pygame.time.Clock()
    while True:
        a = datetime.datetime.now()
        shared_data.file = create_screen_file()
        clock.tick(FRAME_RATE)


def send_file(shared_data: ShareData):
    server = Server()
    i = 0
    while True:
        data, addr = server.receive_unencrypted()
        if data:
            f = shared_data.file
            if f is not None:
                print(f'sending {i}')
                i += 1
                send_screen(server, addr, f)
            else:
                server.send_unencrypted('error?', addr)


def main():
    # server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # server.bind(('127.0.0.1', 12345))
    # while True:
    #     data, addr = server.recvfrom(1024)
    #     print('got new req', data)
    #     send_screen(server, addr, img)
    #     print('sent!')
    shared_data = ShareData()
    threads = [threading.Thread(target=create_file, args=[shared_data]),
               threading.Thread(target=send_file, args=[shared_data])]
    for thread in threads:
        thread.start()


if __name__ == '__main__':
    main()
