import os
import socket
import select
import time
import pygame
import pickle
from PIL import Image

from constants import *


class Client:
    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._send_to = BIND_PARAM

    def length_of_message(self):
        try:
            data = int.from_bytes(self._socket.recvfrom(LENGTH_BUFFER)[0], 'little')
            if not data:
                return 0
            return data
        except (ConnectionError, socket.timeout):
            return 0

    def send_unencrypted(self, message):
        data = pickle.dumps(message)
        self._socket.sendto(len(data).to_bytes(LENGTH_BUFFER, 'little'), self._send_to)
        while len(data) > PACKET_LIMIT:
            self._socket.sendto(data[:PACKET_LIMIT], self._send_to)
            data = data[PACKET_LIMIT:]
        self._socket.sendto(data, self._send_to)

    def receive_unencrypted(self):
        try:
            length = self.length_of_message()
            message, _ = self._socket.recvfrom(length)
            delta = length - len(message)
            while delta:
                first_len = len(message)
                message += self._socket.recvfrom(delta)[0]
                delta = max(0, delta - (len(message) - first_len))
            if not message:
                raise ValueError
            return pickle.loads(message)
        except Exception as my_exception:
            return my_exception

    @property
    def have_data(self):
        try:
            r, _, _ = select.select([self._socket], [], [], 0)
        except ValueError:
            return False
        return r != []


def init() -> pygame.Surface:
    """
    מאתחל את המסך
    :return: אובייקט המסך
    """
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode(get_resolution(RESULOTION))
    pygame.display.set_caption('screen sharing')
    return screen


def main():
    client = Client()
    screen = init()
    finish = False
    clock = pygame.time.Clock()
    last_image = None
    client.send_unencrypted('nothing...')
    while not finish:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                finish = True
        if client.have_data:
            try:
                with open('clienttemp.jpg', 'wb') as my_file:
                    data = client.receive_unencrypted()
                    my_file.write(data)
                last_image = pygame.image.load('clienttemp.jpg')
                os.remove('clienttemp.jpg')
                #client.send_unencrypted('nothing...')
                screen.fill((0, 0, 0))
                screen.blit(last_image, (0, 0))
                pygame.display.flip()
            except Exception as e:
                print(e)
            client.send_unencrypted('nothing...')
        clock.tick(30)


if __name__ == '__main__':
    main()
