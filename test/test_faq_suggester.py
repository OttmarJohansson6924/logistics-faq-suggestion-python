from src.faq_suggester import ExceptionCase, FaqRequest, ShipmentEvent, choose_faq


def test_open_exception_wins_over_the_retrieved_faq():
    request = FaqRequest(
        question="Where is this shipment?",
        event=ShipmentEvent("S-17", "delayed", "2026-10-24T08:00:00Z"),
        exception=ExceptionCase("S-17", "address_review", True),
    )
    candidates = [
        {"question": "Where is my shipment?", "answer": "Check the latest scan.", "score": 0.98},
        {"question": "How do I handle an open delivery exception?", "answer": "Assign the next action.", "score": 0.72},
    ]
    result = choose_faq(request, candidates)
    assert result is not None
    assert result.question == "How do I handle an open delivery exception?"
    assert result.answer == "Assign the next action."
