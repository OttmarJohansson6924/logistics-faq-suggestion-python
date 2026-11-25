from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.faq_suggester import ExceptionCase, FaqRequest, ShipmentEvent, choose_faq


request = FaqRequest(
    question="What should I do next?",
    event=ShipmentEvent("S-17", "exception", "2026-10-24T08:00:00Z"),
    exception=ExceptionCase("S-17", "address_review", True),
)
result = choose_faq(request, [])
print(result)
