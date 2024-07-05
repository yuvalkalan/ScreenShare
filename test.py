K_P = 3
K_I = 5
K_D = 0


def main():
    number = 2
    target = 200
    counter = 1
    while True:
        error = target-number
        error *= K_P
        error *= K_I/counter
        # error *= K_D*counter
        number += error
        counter += 1
        print(error, number)


if __name__ == '__main__':
    main()