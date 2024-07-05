from vidstream import ScreenShareClient
from threading import Thread


def main():
    client = ScreenShareClient('8.tcp.ngrok.io', 15140)
    client_thread = Thread(target=client.start_stream)
    client_thread.start()
    input()
    client.stop_stream()


if __name__ == '__main__':
    main()
