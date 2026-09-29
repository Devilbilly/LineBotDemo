import re

from .menu import FOOD, ICE, MENU, OPENING_HOURS, PICKUP_MINUTES, SWEETNESS, price

HELP = (
    "您好！我是小巷咖啡點餐小幫手，可以輸入：\n"
    "・菜單\n"
    "・營業時間\n"
    "・推薦\n"
    "・點 品名 數量（例如：點 拿鐵 2）\n"
    "・點 品名 甜度冰量（例如：點 摩卡 半糖少冰）\n"
    "・購物車\n"
    "・清空\n"
    "・結帳"
)

RECOMMEND = "今日推薦：摩卡，搭配重乳酪蛋糕只要 NT$199"
BAD_QUANTITY = "數量請輸入 1 到 20 的數字"
BAD_SWEETNESS = "甜度請選：" + "、".join(SWEETNESS)
BAD_ICE = "冰量請選：" + "、".join(ICE)
CUSTOM = re.compile(r"[糖甜冰]")


class Orders:
    def __init__(self):
        self._carts = {}

    def cart(self, user_id):
        return self._carts.setdefault(user_id, {})

    def clear(self, user_id):
        self._carts.pop(user_id, None)


def _total(cart):
    return sum(MENU[name] * quantity for (name, _), quantity in cart.items())


def _lines(cart):
    return "、".join(f"{name}（{cup}） × {quantity}" if cup else f"{name} × {quantity}"
                    for (name, cup), quantity in cart.items())


def _menu_text():
    rows = [f"{name} {price(amount)}" for name, amount in MENU.items()]
    return "【菜單】\n" + "\n".join(rows)


def _cups(spec):
    rest = re.sub(r"[、，,]", "", spec)
    cups = []
    while rest:
        sweetness = next((s for s in SWEETNESS if rest.startswith(s)), "")
        if not sweetness:
            return BAD_SWEETNESS
        ice = next((i for i in ICE if rest[len(sweetness):].startswith(i)), "")
        if not ice:
            return BAD_ICE
        cups.append(sweetness + ice)
        rest = rest[len(sweetness + ice):]
    return cups


def _order(text, cart):
    parts = text.split()
    if len(parts) < 2:
        return "請告訴我要點什麼，例如：點 拿鐵 2"
    name, rest = parts[1], parts[2:]
    glued = re.fullmatch(r"(\D+)(\d+[杯個]?)", name)
    if name not in MENU and glued and glued.group(1) in MENU and CUSTOM.search("".join(rest)):
        name, rest = glued.group(1), [glued.group(2)] + rest
    if name not in MENU:
        return f"找不到「{name}」，輸入「菜單」看看有什麼"
    quantity = None
    if rest and not CUSTOM.search(rest[0]):
        match = re.fullmatch(r"(\d+)[杯個]?", rest[0])
        if not match or not 1 <= int(match.group(1)) <= 20:
            return BAD_QUANTITY
        quantity = int(match.group(1))
        rest = rest[1:]
    spec = "".join(rest)
    cups = [""]
    if CUSTOM.search(spec):
        if name in FOOD:
            return f"「{name}」不是飲料，不能指定甜度冰量"
        cups = _cups(spec)
        if isinstance(cups, str):
            return cups
    label = "、".join(cups)
    if quantity is None:
        quantity = len(cups)
        if quantity > 20:
            return BAD_QUANTITY
    elif len(cups) == 1:
        cups *= quantity
    elif len(cups) != quantity:
        return f"數量是 {quantity} 杯，但指定了 {len(cups)} 杯的甜度冰量，請讓兩者一致"
    for cup in cups:
        cart[(name, cup)] = cart.get((name, cup), 0) + 1
    detail = f"（{label}）" if label else ""
    return f"已加入 {name} × {quantity}{detail}，目前合計 {price(_total(cart))}"


def reply_for(text, user_id, orders):
    text = (text or "").strip()
    cart = orders.cart(user_id)
    if text == "菜單":
        return [_menu_text()]
    if text == "營業時間":
        return [f"營業時間：{OPENING_HOURS}"]
    if text == "推薦":
        return [RECOMMEND]
    if text.startswith("點"):
        return [_order(text, cart)]
    if text == "購物車":
        if not cart:
            return ["購物車是空的"]
        return [f"購物車：{_lines(cart)}，合計 {price(_total(cart))}"]
    if text == "清空":
        orders.clear(user_id)
        return ["購物車已清空"]
    if text == "結帳":
        if not cart:
            return ["購物車是空的，先點餐吧"]
        summary = f"訂單成立：{_lines(cart)}，合計 {price(_total(cart))}。請於 {PICKUP_MINUTES} 分鐘後到店取餐。"
        orders.clear(user_id)
        return [summary]
    return [HELP]
