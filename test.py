import win32api
import win32con
import time


def main():
    time.sleep(1)
    string = 'אבגדהוזחטיכלמנסעפצקרשתךםןףץ'
    print(len(string))
    for c in string:
        print(c, ord(c))


if __name__ == '__main__':
    main()
