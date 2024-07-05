import datetime
import pickle
import random
import select
import socket
import time
from io import BytesIO
from multiprocessing import Process, Queue
from multiprocessing.reduction import ForkingPickler


def forking_dumps(obj):
    buf = BytesIO()
    ForkingPickler(buf).dump(obj)
    return buf.getvalue()


def handle(q_receive: Queue, q_send: Queue):
    print('start!')
    for i in range(10):
        q_send.put(i)
        print(q_receive.get())
        time.sleep(random.random()*3)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('httpbin.org', 80))
    sock.send(b'GET /get\r\n')
    # first bytes read in parent
    print('first part:', sock.recv(20))
    q_send, q_receive = Queue(), Queue()
    q_send = q_receive
    proc = Process(target=handle, args=(q_send, q_receive))
    proc.start()
    print('start1!')
    handle(q_receive, q_send)
    proc.join()


if __name__ == '__main__':
    main()