from bot.replies import HELP, Orders, reply_for


def talk(orders, text, user="u1"):
    return reply_for(text, user, orders)[0]


def test_menu_lists_every_item_with_its_price():
    menu = talk(Orders(), "菜單")
    assert menu.startswith("【菜單】")
    assert "拿鐵 NT$110" in menu and "重乳酪蛋糕 NT$95" in menu
    assert len(menu.splitlines()) == 7


def test_opening_hours():
    assert talk(Orders(), "營業時間") == "營業時間：每天 08:00–18:00"


def test_ordering_adds_items_and_reports_the_total():
    orders = Orders()
    assert talk(orders, "點 拿鐵 2") == "已加入 拿鐵 × 2，目前合計 NT$220"
    assert talk(orders, "點 重乳酪蛋糕") == "已加入 重乳酪蛋糕 × 1，目前合計 NT$315"
    assert talk(orders, "購物車") == "購物車：拿鐵 × 2、重乳酪蛋糕 × 1，合計 NT$315"


def test_unknown_item_and_bad_quantity_are_explained():
    orders = Orders()
    assert talk(orders, "點 珍珠奶茶") == "找不到「珍珠奶茶」，輸入「菜單」看看有什麼"
    assert talk(orders, "點 拿鐵 0") == "數量請輸入 1 到 20 的數字"
    assert talk(orders, "點 拿鐵 abc") == "數量請輸入 1 到 20 的數字"
    assert talk(orders, "點") == "請告訴我要點什麼，例如：點 拿鐵 2"
    assert talk(orders, "購物車") == "購物車是空的"


def test_checkout_summarizes_and_empties_the_cart():
    orders = Orders()
    assert talk(orders, "結帳") == "購物車是空的，先點餐吧"
    talk(orders, "點 美式咖啡")
    assert talk(orders, "結帳") == "訂單成立：美式咖啡 × 1，合計 NT$80。請於 15 分鐘後到店取餐。"
    assert talk(orders, "購物車") == "購物車是空的"


def test_carts_are_per_user_and_can_be_cleared():
    orders = Orders()
    talk(orders, "點 摩卡", user="alice")
    assert talk(orders, "購物車", user="bob") == "購物車是空的"
    assert talk(orders, "清空", user="alice") == "購物車已清空"
    assert talk(orders, "購物車", user="alice") == "購物車是空的"


def test_anything_else_gets_the_help_text():
    assert talk(Orders(), "你好") == HELP
