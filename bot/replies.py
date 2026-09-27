from .menu import MENU, OPENING_HOURS, PICKUP_MINUTES, price

HELP = (
    "您好！我是小巷咖啡點餐小幫手，可以輸入：\n"
    "・菜單\n"
    "・營業時間\n"
    "・點 品名 數量（例如：點 拿鐵 2）\n"
    "・購物車\n"
    "・清空\n"
    "・結帳"
)


class Orders:
    def __init__(self):
        self._carts = {}

    def cart(self, user_id):
        return self._carts.setdefault(user_id, {})

    def clear(self, user_id):
        self._carts.pop(user_id, None)


def _total(cart):
    return sum(MENU[name] * quantity for name, quantity in cart.items())


def _lines(cart):
    return "、".join(f"{name} × {quantity}" for name, quantity in cart.items())


def _menu_text():
    rows = [f"{name} {price(amount)}" for name, amount in MENU.items()]
    return "【菜單】\n" + "\n".join(rows)


def _order(text, cart):
    parts = text.split()
    if len(parts) < 2:
        return "請告訴我要點什麼，例如：點 拿鐵 2"
    name = parts[1]
    if name not in MENU:
        return f"找不到「{name}」，輸入「菜單」看看有什麼"
    quantity = 1
    if len(parts) >= 3:
        if not parts[2].isdigit() or not 1 <= int(parts[2]) <= 20:
            return "數量請輸入 1 到 20 的數字"
        quantity = int(parts[2])
    cart[name] = cart.get(name, 0) + quantity
    return f"已加入 {name} × {quantity}，目前合計 {price(_total(cart))}"


def reply_for(text, user_id, orders):
    text = (text or "").strip()
    cart = orders.cart(user_id)
    if text == "菜單":
        return [_menu_text()]
    if text == "營業時間":
        return [f"營業時間：{OPENING_HOURS}"]
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
