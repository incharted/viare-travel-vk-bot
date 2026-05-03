from services.anti_fraud import InMemoryAntiFraud


def test_inspect_text_detects_many_links():
    reason = InMemoryAntiFraud.inspect_text(
        "https://a.example https://b.example www.c.example"
    )
    assert reason == "many_links"


def test_inspect_text_detects_repeated_symbols():
    assert InMemoryAntiFraud.inspect_text("aaaaaaaaaaaa") == "repeated_symbols"


def test_register_same_message_detects_repeated_spam():
    anti_fraud = InMemoryAntiFraud()

    reason = None
    for _ in range(5):
        reason = anti_fraud.register_same_message(123, "same text")

    assert reason == "repeated_same_message"
