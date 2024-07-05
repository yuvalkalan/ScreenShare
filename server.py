from vidstream import StreamingServer
from threading import Thread


def main():
    server = StreamingServer('127.0.0.1', 12345)
    server_thread = Thread(target=server.start_server)
    server_thread.start()
    input()
    server.stop_server()


if __name__ == '__main__':
    main()
