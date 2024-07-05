from server import *


def main():
    server = Server()
    server.start_streaming()
    while server.running:
        time.sleep(0.1)
    server.stop_streaming()
