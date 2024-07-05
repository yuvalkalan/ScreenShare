from client import *


def main():
    client = Client(input('enter server code: '), input('enter password: '))
    client.start_listening()
    while client.running:
        time.sleep(0.1)
    client.stop_listening()
