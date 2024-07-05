RES_RATIO = 1 + 7/9
BIND_PARAM = ('127.0.0.1', 12345)
LEN_DATA_SPLITTER = '-'
LENGTH_BUFFER = 4
RESULOTION = 720
FRAME_RATE = 5
PACKET_LIMIT = 2**15


def get_resolution(res):
    return int(res * RES_RATIO), res
