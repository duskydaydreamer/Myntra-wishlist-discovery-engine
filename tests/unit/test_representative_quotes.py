from backend.api.routers.dashboard import _representative_quote_score


def test_clear_issue_specific_quote_is_eligible():
    quote = (
        "Every time I order denim online, the length is too short. "
        "What size should I order for my height?"
    )
    assert _representative_quote_score("opp_001", quote, "play_store") is not None


def test_privacy_masked_quote_is_rejected():
    quote = "The [NAME] product was costly and the quality did not match the price at all."
    assert _representative_quote_score("opp_002", quote, "play_store") is None


def test_unrelated_quote_is_rejected():
    quote = "The app opened quickly and I liked the colors shown on the home screen today."
    assert _representative_quote_score("opp_003", quote, "play_store") is None


def test_positive_resolution_is_not_used_for_friction_opportunity():
    quote = (
        "I missed the return window, but support understood the situation "
        "and approved my refund request immediately."
    )
    assert _representative_quote_score("opp_003", quote, "play_store") is None


def test_hindi_quote_is_not_used_on_english_only_surface():
    quote = (
        "मैंने Myntra app से एक घड़ी ऑर्डर की थी जिसकी कीमत 4070 रुपये थी। "
        "लेकिन मुझे जो डिलीवरी मिली उसमें एक अलग ही प्रोडक्ट था।"
    )
    assert _representative_quote_score("opp_002", quote, "youtube") is None


def test_complete_hinglish_quote_is_eligible():
    quote = (
        "Maine product order kiya tha lekin quality bahut bekar thi, "
        "aur mujhe return request ke baad bhi refund nahi mila."
    )
    assert _representative_quote_score("opp_002", quote, "play_store") is not None
