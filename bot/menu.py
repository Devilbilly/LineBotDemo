MENU = {
    "美式咖啡": 80,
    "拿鐵": 110,
    "卡布奇諾": 110,
    "摩卡": 120,
    "紅茶": 60,
    "重乳酪蛋糕": 95,
}

FOOD = {"重乳酪蛋糕"}
SWEETNESS = ("全糖", "半糖", "微糖", "無糖")
ICE = ("正常冰", "少冰", "微冰", "去冰")

OPENING_HOURS = "每天 08:00–18:00"
PICKUP_MINUTES = 15


def price(amount):
    return f"NT${amount}"
