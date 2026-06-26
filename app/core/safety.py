from __future__ import annotations

import re

from app.domain.enums import Language, UserType


CREDENTIAL_PATTERN = re.compile(r"\b(otp|pin|password|card\s*number|full card number)\b", re.IGNORECASE)
PROMISE_PATTERN = re.compile(
    r"\b(we will refund|refund confirmed|we will reverse|account will be unblocked|we will recover)\b",
    re.IGNORECASE,
)
THIRD_PARTY_PATTERN = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")
INJECTION_ECHO_PATTERN = re.compile(r"(ignore all rules|developer mode|system prompt|confirm my refund)", re.IGNORECASE)


def safe_customer_reply(ticket_id: str, language: Language, user_type: UserType) -> str:
    if language == Language.BN:
        return (
            f"আমরা আপনার অভিযোগ ({ticket_id}) নোট করেছি। আমাদের দল অফিসিয়াল চ্যানেলে যোগাযোগ করবে। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    if language == Language.MIXED:
        return (
            f"Amra apnar complaint ({ticket_id}) note korechi. Official channel diye update deya hobe. "
            "Please karo shathe apnar PIN ba OTP share korben na."
        )
    if user_type == UserType.MERCHANT:
        return (
            f"We have recorded your concern ({ticket_id}). Our team will review the matter and update you through "
            "official channels. Please do not share your PIN or OTP with anyone."
        )
    return (
        f"We have noted your complaint ({ticket_id}). Our team will investigate and respond through official channels. "
        "Please do not share your PIN or OTP with anyone."
    )


def enforce_customer_reply_safety(
    ticket_id: str,
    language: Language,
    user_type: UserType,
    customer_reply: str,
) -> tuple[str, bool]:
    normalized = customer_reply.strip()
    if not normalized:
        return safe_customer_reply(ticket_id, language, user_type), True

    if PROMISE_PATTERN.search(normalized):
        return safe_customer_reply(ticket_id, language, user_type), True

    if INJECTION_ECHO_PATTERN.search(normalized):
        return safe_customer_reply(ticket_id, language, user_type), True

    if THIRD_PARTY_PATTERN.search(normalized) and "official" not in normalized.lower():
        return safe_customer_reply(ticket_id, language, user_type), True

    if "share your" in normalized.lower() and CREDENTIAL_PATTERN.search(normalized):
        return safe_customer_reply(ticket_id, language, user_type), True

    return normalized, False

