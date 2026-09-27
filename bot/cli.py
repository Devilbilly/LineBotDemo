import sys

from .replies import Orders, reply_for


def main():
    orders = Orders()
    print("小巷咖啡點餐小幫手（輸入訊息，Ctrl-D 結束）")
    for line in sys.stdin:
        for reply in reply_for(line, "local-user", orders):
            print(reply)


if __name__ == "__main__":
    main()
