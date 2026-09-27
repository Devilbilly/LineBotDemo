"""Issue #1: a 「推薦」 command, and order quantities may end in 「杯」 or 「個」.

Reproduce on main: send 「推薦」 and the bot answers with the help text; send
「點 拿鐵 2杯」 and it answers 「數量請輸入 1 到 20 的數字」 instead of adding the item.
The reply sentences below are the owner's exact wording and are asserted verbatim.
"""
import io

import pytest

from bot import cli
from bot.replies import HELP, Orders, reply_for
from tests.test_webhook import client_and_sent, post, text_event

RECOMMEND = "今日推薦：摩卡，搭配重乳酪蛋糕只要 NT$199"
BAD_QUANTITY = "數量請輸入 1 到 20 的數字"


def talk(orders, text, user="u1"):
    return reply_for(text, user, orders)[0]


def test_recommend_replies_with_the_exact_sentence():
    assert talk(Orders(), "推薦") == RECOMMEND
    assert talk(Orders(), "  推薦 \n") == RECOMMEND


@pytest.mark.parametrize("text", ["推薦一下", "今日推薦", "推 薦"])
def test_recommend_only_answers_the_exact_command(text):
    assert talk(Orders(), text) == HELP


def test_recommend_leaves_the_cart_alone():
    orders = Orders()
    assert talk(orders, "推薦") == RECOMMEND
    assert talk(orders, "購物車") == "購物車是空的"
    talk(orders, "點 拿鐵 2")
    assert talk(orders, "推薦") == RECOMMEND
    assert talk(orders, "購物車") == "購物車：拿鐵 × 2，合計 NT$220"


def test_help_lists_recommend_next_to_the_existing_commands():
    lines = HELP.splitlines()
    assert "・推薦" in lines
    for command in ("・菜單", "・營業時間", "・購物車", "・清空", "・結帳"):
        assert command in lines


def test_quantity_with_a_cup_or_piece_unit_is_accepted():
    assert talk(Orders(), "點 拿鐵 2杯") == "已加入 拿鐵 × 2，目前合計 NT$220"
    assert talk(Orders(), "點 重乳酪蛋糕 1個") == "已加入 重乳酪蛋糕 × 1，目前合計 NT$95"


@pytest.mark.parametrize("text", ["點 拿鐵 2杯", "點 拿鐵 2個", "點 拿鐵 2"])
def test_a_unit_suffix_works_exactly_like_the_bare_number(text):
    orders = Orders()
    assert talk(orders, text) == talk(Orders(), "點 拿鐵 2")
    assert talk(orders, "購物車") == "購物車：拿鐵 × 2，合計 NT$220"


@pytest.mark.parametrize("text,reply", [
    ("點 摩卡 20杯", "已加入 摩卡 × 20，目前合計 NT$2400"),
    ("點 紅茶 1杯", "已加入 紅茶 × 1，目前合計 NT$60"),
    ("點 拿鐵 21杯", BAD_QUANTITY),
    ("點 拿鐵 0個", BAD_QUANTITY),
])
def test_the_one_to_twenty_range_still_applies_with_a_unit(text, reply):
    assert talk(Orders(), text) == reply


@pytest.mark.parametrize("quantity", ["杯", "個", "2杯杯", "杯2", "2份", "2片", "-1杯", "1.5杯", "²杯", "²"])
def test_malformed_quantities_are_refused_without_touching_the_cart(quantity):
    orders = Orders()
    assert talk(orders, f"點 拿鐵 {quantity}") == BAD_QUANTITY
    assert talk(orders, "購物車") == "購物車是空的"


def test_full_width_digits_keep_working_with_a_unit():
    assert talk(Orders(), "點 拿鐵 ２杯") == "已加入 拿鐵 × 2，目前合計 NT$220"


def test_mixed_units_accumulate_and_check_out():
    orders = Orders()
    talk(orders, "點 拿鐵 2杯")
    assert talk(orders, "點 拿鐵 1個") == "已加入 拿鐵 × 1，目前合計 NT$330"
    talk(orders, "點 重乳酪蛋糕 1個")
    assert talk(orders, "購物車") == "購物車：拿鐵 × 3、重乳酪蛋糕 × 1，合計 NT$425"
    assert talk(orders, "結帳") == "訂單成立：拿鐵 × 3、重乳酪蛋糕 × 1，合計 NT$425。請於 15 分鐘後到店取餐。"


def test_the_webhook_sends_both_new_replies():
    client, sent = client_and_sent()
    assert post(client, text_event("推薦")).status_code == 200
    assert post(client, text_event("點 拿鐵 2杯")).status_code == 200
    assert [texts for _, texts in sent] == [[RECOMMEND], ["已加入 拿鐵 × 2，目前合計 NT$220"]]


def test_the_local_cli_answers_both_new_messages(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("推薦\n點 拿鐵 2杯\n點 重乳酪蛋糕 1個\n"))
    cli.main()
    out = capsys.readouterr().out.splitlines()
    assert out[1:] == [RECOMMEND, "已加入 拿鐵 × 2，目前合計 NT$220", "已加入 重乳酪蛋糕 × 1，目前合計 NT$315"]
