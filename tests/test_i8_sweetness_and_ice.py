"""Issue #8: each cup of a drink order can carry its own sweetness and ice.

Reproduce on main: send 「點 摩卡 半糖少冰、無糖去冰、微糖微冰」 and the bot answers
「數量請輸入 1 到 20 的數字」; send 「點 摩卡 2 半糖少冰」 and it adds two plain mochas,
silently dropping the spec; 「購物車」 and 「結帳」 can only show name and quantity.

Sweetness is one of 全糖、半糖、微糖、無糖 and ice one of 正常冰、少冰、微冰、去冰, written
together per cup (半糖少冰). Orders without a spec keep today's behaviour and wording.

The filer's sentences are kept below exactly as typed in the issue. They were typed with
half-width punctuation, including 「已加入 摩卡 × 3,目前合計 NT$XXX」 for the reply that
must stay unchanged and today reads 「，」. So ``expected()`` maps the filer's
half-width marks to the bot's full-width ones, and
``test_plain_orders_keep_todays_reply_word_for_word`` proves that mapping reproduces
today's reply exactly.
"""
import io

import pytest

from bot import cli
from bot.replies import HELP, Orders, reply_for
from tests.test_webhook import client_and_sent, post, text_event

THREE_CUPS = "已加入 摩卡 × 3(半糖少冰、無糖去冰、微糖微冰),目前合計 NT$XXX"
ONE_CUP = "已加入 摩卡 × 1(半糖少冰),目前合計 NT$XXX"
PLAIN_THREE = "已加入 摩卡 × 3,目前合計 NT$XXX"
BAD_SWEETNESS = "甜度請選:全糖、半糖、微糖、無糖"
BAD_ICE = "冰量請選:正常冰、少冰、微冰、去冰"
CART_ONE_CUP = "購物車:摩卡(半糖少冰) × 1,合計 NT$XXX"
HELP_LINE = "・點 品名 甜度冰量(例如:點 摩卡 半糖少冰)"
BAD_QUANTITY = "數量請輸入 1 到 20 的數字"

FULL_WIDTH = str.maketrans({",": "，", ":": "：", "(": "（", ")": "）"})
SWEETNESS = ["全糖", "半糖", "微糖", "無糖"]
ICE = ["正常冰", "少冰", "微冰", "去冰"]


def expected(sentence, total=None):
    if total is not None:
        sentence = sentence.replace("XXX", str(total))
    return sentence.translate(FULL_WIDTH)


def talk(orders, text, user="u1"):
    return reply_for(text, user, orders)[0]


def test_three_specs_add_three_cups_as_the_issue_asks():
    orders = Orders()
    assert talk(orders, "點 摩卡 半糖少冰、無糖去冰、微糖微冰") == expected(THREE_CUPS, 360)
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1、摩卡（微糖微冰） × 1，合計 NT$360"


def test_a_single_spec_is_one_cup():
    orders = Orders()
    assert talk(orders, "點 摩卡 半糖少冰") == expected(ONE_CUP, 120)
    assert talk(orders, "購物車") == expected(CART_ONE_CUP, 120)


@pytest.mark.parametrize("text", ["點 摩卡 3杯", "點 摩卡 3"])
def test_plain_orders_keep_todays_reply_word_for_word(text):
    orders = Orders()
    assert talk(orders, text) == expected(PLAIN_THREE, 360) == "已加入 摩卡 × 3，目前合計 NT$360"
    assert talk(orders, "購物車") == "購物車：摩卡 × 3，合計 NT$360"
    assert talk(Orders(), "點 摩卡") == "已加入 摩卡 × 1，目前合計 NT$120"


@pytest.mark.parametrize("sweetness", SWEETNESS)
@pytest.mark.parametrize("ice", ICE)
def test_every_sweetness_and_ice_pair_is_accepted(sweetness, ice):
    assert talk(Orders(), f"點 摩卡 {sweetness}{ice}") == f"已加入 摩卡 × 1（{sweetness}{ice}），目前合計 NT$120"


def test_full_sugar_normal_ice_uses_the_three_character_ice_word():
    orders = Orders()
    assert talk(orders, "點 摩卡 全糖正常冰") == "已加入 摩卡 × 1（全糖正常冰），目前合計 NT$120"
    assert talk(orders, "購物車") == "購物車：摩卡（全糖正常冰） × 1，合計 NT$120"


@pytest.mark.parametrize("text,reply", [
    ("點 摩卡 超甜少冰", BAD_SWEETNESS),
    ("點 摩卡 半糖超冰", BAD_ICE),
    ("點 摩卡 少冰半糖", BAD_SWEETNESS),
    ("點 摩卡 去冰", BAD_SWEETNESS),
    ("點 摩卡 超甜", BAD_SWEETNESS),
    ("點 摩卡 半糖", BAD_ICE),
    ("點 摩卡 半糖少冰、無糖", BAD_ICE),
    ("點 摩卡 半糖少冰、超甜去冰", BAD_SWEETNESS),
    ("點 摩卡 半糖少冰 2", BAD_SWEETNESS),
    ("點 摩卡 2 半糖", BAD_ICE),
])
def test_an_unknown_sweetness_or_ice_is_named_and_the_cart_is_unchanged(text, reply):
    orders = Orders()
    talk(orders, "點 拿鐵 2")
    assert talk(orders, text) == expected(reply)
    assert talk(orders, "購物車") == "購物車：拿鐵 × 2，合計 NT$220"


def test_different_specs_stay_separate_and_equal_specs_add_up():
    orders = Orders()
    talk(orders, "點 摩卡 半糖少冰")
    assert talk(orders, "點 摩卡 無糖去冰") == "已加入 摩卡 × 1（無糖去冰），目前合計 NT$240"
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1，合計 NT$240"
    talk(orders, "點 摩卡 半糖少冰")
    talk(orders, "點 摩卡")
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 2、摩卡（無糖去冰） × 1、摩卡 × 1，合計 NT$480"


def test_checkout_lists_every_cups_sweetness_and_ice():
    orders = Orders()
    talk(orders, "點 摩卡 半糖少冰、無糖去冰、微糖微冰")
    talk(orders, "點 拿鐵 1杯")
    assert talk(orders, "結帳") == (
        "訂單成立：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1、摩卡（微糖微冰） × 1、拿鐵 × 1，"
        "合計 NT$470。請於 15 分鐘後到店取餐。")
    assert talk(orders, "購物車") == "購物車是空的"


def test_a_quantity_with_one_spec_applies_it_to_every_cup():
    orders = Orders()
    assert talk(orders, "點 摩卡 2 半糖少冰") == "已加入 摩卡 × 2（半糖少冰），目前合計 NT$240"
    assert talk(orders, "點 摩卡 2杯 無糖去冰") == "已加入 摩卡 × 2（無糖去冰），目前合計 NT$480"
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 2、摩卡（無糖去冰） × 2，合計 NT$480"


def test_a_quantity_matching_the_number_of_specs_gives_one_spec_per_cup():
    orders = Orders()
    assert talk(orders, "點 摩卡 3 半糖少冰、無糖去冰、微糖微冰") == expected(THREE_CUPS, 360)
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1、摩卡（微糖微冰） × 1，合計 NT$360"


def test_a_quantity_that_disagrees_with_the_specs_is_refused():
    orders = Orders()
    assert talk(orders, "點 摩卡 2 半糖少冰、無糖去冰、微糖微冰") == "數量是 2 杯，但指定了 3 杯的甜度冰量，請讓兩者一致"
    assert talk(orders, "購物車") == "購物車是空的"


@pytest.mark.parametrize("text,reply", [
    ("點 摩卡 20 半糖少冰", "已加入 摩卡 × 20（半糖少冰），目前合計 NT$2400"),
    ("點 摩卡 " + "半糖少冰" * 20, "已加入 摩卡 × 20（" + "、".join(["半糖少冰"] * 20) + "），目前合計 NT$2400"),
    ("點 摩卡 21 半糖少冰", BAD_QUANTITY),
    ("點 摩卡 0杯 半糖少冰", BAD_QUANTITY),
    ("點 摩卡 " + "半糖少冰" * 21, BAD_QUANTITY),
    ("點 摩卡 ² 半糖少冰", BAD_QUANTITY),
    ("點 摩卡 -1 半糖少冰", BAD_QUANTITY),
])
def test_the_one_to_twenty_range_still_applies_with_a_spec(text, reply):
    orders = Orders()
    assert talk(orders, text) == reply
    if reply == BAD_QUANTITY:
        assert talk(orders, "購物車") == "購物車是空的"


def test_full_width_digits_work_with_a_spec():
    assert talk(Orders(), "點 摩卡 ２ 半糖少冰") == "已加入 摩卡 × 2（半糖少冰），目前合計 NT$240"


def test_the_message_in_the_issue_with_the_count_glued_to_the_name():
    orders = Orders()
    assert talk(orders, "點 摩卡3 半糖少冰、無糖去冰、微糖微冰") == expected(THREE_CUPS, 360)
    assert talk(orders, "點 摩卡3") == "找不到「摩卡3」，輸入「菜單」看看有什麼"
    assert talk(orders, "點 摩卡3 謝謝") == "找不到「摩卡3」，輸入「菜單」看看有什麼"
    assert talk(orders, "購物車") == "購物車：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1、摩卡（微糖微冰） × 1，合計 NT$360"


@pytest.mark.parametrize("spec", [
    "半糖少冰,無糖去冰", "半糖少冰，無糖去冰", "半糖少冰 無糖去冰", "半糖少冰無糖去冰", "半糖 少冰、無糖 去冰",
])
def test_cups_may_be_separated_by_commas_or_spaces(spec):
    assert talk(Orders(), f"點 摩卡 {spec}") == "已加入 摩卡 × 2（半糖少冰、無糖去冰），目前合計 NT$240"


@pytest.mark.parametrize("text,reply", [
    ("點 拿鐵 abc", BAD_QUANTITY),
    ("點 拿鐵 2份", BAD_QUANTITY),
    ("點 拿鐵 杯", BAD_QUANTITY),
    ("點 拿鐵 2 謝謝", "已加入 拿鐵 × 2，目前合計 NT$220"),
    ("點 拿鐵2", "找不到「拿鐵2」，輸入「菜單」看看有什麼"),
    ("點 重乳酪蛋糕 1個", "已加入 重乳酪蛋糕 × 1，目前合計 NT$95"),
])
def test_orders_without_sweetness_or_ice_behave_as_before(text, reply):
    assert talk(Orders(), text) == reply


def test_a_cake_cannot_take_sweetness_or_ice():
    orders = Orders()
    assert talk(orders, "點 重乳酪蛋糕 半糖少冰") == "「重乳酪蛋糕」不是飲料，不能指定甜度冰量"
    assert talk(orders, "點 重乳酪蛋糕 2 超甜") == "「重乳酪蛋糕」不是飲料，不能指定甜度冰量"
    assert talk(orders, "購物車") == "購物車是空的"


def test_help_explains_the_spec_and_other_replies_are_unchanged():
    lines = HELP.splitlines()
    assert expected(HELP_LINE) in lines
    assert lines.index(expected(HELP_LINE)) == lines.index("・點 品名 數量（例如：點 拿鐵 2）") + 1
    for command in ("・菜單", "・營業時間", "・推薦", "・購物車", "・清空", "・結帳"):
        assert command in lines
    orders = Orders()
    assert talk(orders, "說明") == HELP
    assert talk(orders, "菜單").splitlines()[4] == "摩卡 NT$120"
    assert talk(orders, "推薦") == "今日推薦：摩卡，搭配重乳酪蛋糕只要 NT$199"
    assert talk(orders, "營業時間") == "營業時間：每天 08:00–18:00"
    talk(orders, "點 摩卡 半糖少冰")
    assert talk(orders, "清空") == "購物車已清空"
    assert talk(orders, "購物車") == "購物車是空的"


def test_specs_stay_in_the_users_own_cart():
    orders = Orders()
    talk(orders, "點 摩卡 半糖少冰", user="alice")
    talk(orders, "點 摩卡 無糖去冰", user="bob")
    assert talk(orders, "購物車", user="alice") == "購物車：摩卡（半糖少冰） × 1，合計 NT$120"
    assert talk(orders, "購物車", user="bob") == "購物車：摩卡（無糖去冰） × 1，合計 NT$120"


def test_the_webhook_and_the_local_cli_send_the_new_replies(monkeypatch, capsys):
    client, sent = client_and_sent()
    assert post(client, text_event("點 摩卡 半糖少冰")).status_code == 200
    assert post(client, text_event("購物車")).status_code == 200
    assert [texts for _, texts in sent] == [[expected(ONE_CUP, 120)], [expected(CART_ONE_CUP, 120)]]
    monkeypatch.setattr("sys.stdin", io.StringIO("點 摩卡 半糖少冰、無糖去冰、微糖微冰\n結帳\n"))
    cli.main()
    assert capsys.readouterr().out.splitlines()[1:] == [
        expected(THREE_CUPS, 360),
        "訂單成立：摩卡（半糖少冰） × 1、摩卡（無糖去冰） × 1、摩卡（微糖微冰） × 1，合計 NT$360。請於 15 分鐘後到店取餐。",
    ]
