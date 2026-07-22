from src.reports import signing


def test_valid_token_verifies():
    token, _ = signing.sign_report_id("RPT-0001")
    assert signing.verify_signed_token(token, "RPT-0001") is True


def test_token_rejected_for_wrong_report_id():
    token, _ = signing.sign_report_id("RPT-0001")
    assert signing.verify_signed_token(token, "RPT-0002") is False


def test_expired_token_rejected():
    token, _ = signing.sign_report_id("RPT-0001", ttl_seconds=-1)
    assert signing.verify_signed_token(token, "RPT-0001") is False


def test_tampered_token_rejected():
    token, _ = signing.sign_report_id("RPT-0001")
    payload_b64, sig_b64 = token.split(".", 1)
    tampered = payload_b64 + "x." + sig_b64
    assert signing.verify_signed_token(tampered, "RPT-0001") is False


def test_garbage_token_rejected():
    assert signing.verify_signed_token("not-a-token", "RPT-0001") is False
