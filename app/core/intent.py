from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import re

from app.domain.enums import Language, TransactionType


PHONE_PATTERN = re.compile(r"(?:\+?880|0)?1[3-9]\d{8}")
AGENT_PATTERN = re.compile(r"AGENT[-\s]?\d+", re.IGNORECASE)
MERCHANT_PATTERN = re.compile(r"MERCHANT[-\s]?[A-Z0-9]+", re.IGNORECASE)
CURRENCY_AMOUNT_PATTERN = re.compile(r"(?<!\d)(\d{2,7})\s*(?:taka|tk|bdt|টাকা)", re.IGNORECASE)
PLAIN_AMOUNT_PATTERN = re.compile(r"(?<![\d+])(\d{2,6})(?!\d)")
EXPLICIT_12H_TIME = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)")
EXPLICIT_BANGLA_HOUR = re.compile(r"(\d{1,2})\s*টায়")


FRAUD_KEYWORDS = [
    "someone called",
    "received a call",
    "asked for my otp",
    "asked for my pin",
    "suspicious sms",
    "verify account",
    "told me to share",
    "otp",
    "pin",
    "password",
    "called me",
    "account will be blocked",
    "ওটিপি",
    "পিন",
    "পাসওয়ার্ড",
    "কল",
    "শেয়ার",
]

WRONG_TRANSFER_KEYWORDS = [
    "wrong number",
    "wrong person",
    "wrong recipient",
    "sent money to the wrong",
    "mistake",
    "ভুল",
]

PAYMENT_FAILED_KEYWORDS = [
    "failed",
    "balance was deducted",
    "deducted",
    "recharge",
    "payment failed",
    "পেমেন্ট ফেল",
]

DUPLICATE_KEYWORDS = [
    "deducted twice",
    "twice",
    "double",
    "duplicate",
    "charged twice",
    "দুইবার",
]

SETTLEMENT_KEYWORDS = [
    "settled",
    "settlement",
]

CASH_IN_KEYWORDS = [
    "cash in",
    "cash-in",
    "agent",
    "ক্যাশ ইন",
    "এজেন্ট",
]

REFUND_KEYWORDS = [
    "refund",
    "money back",
    "reverse it",
    "changed my mind",
    "রিফান্ড",
]

RELATIVE_TIME_KEYWORDS = {
    "today": 0,
    "yesterday": -1,
    "this morning": 0,
    "morning": 0,
    "tonight": 0,
    "আজ": 0,
    "আজ সকালে": 0,
    "গতকাল": -1,
    "সকালে": 0,
}

PART_OF_DAY_HOURS = {
    "morning": 9,
    "this morning": 9,
    "afternoon": 15,
    "evening": 18,
    "night": 21,
    "সকালে": 9,
    "বিকেল": 15,
    "রাতে": 21,
}


@dataclass
class ComplaintIntent:
    language: Language
    sanitized_complaint: str
    amount: float | None = None
    counterparty: str | None = None
    transaction_type_hint: TransactionType | None = None
    is_fraud_signal: bool = False
    wrong_transfer_intent: bool = False
    payment_failed_intent: bool = False
    duplicate_payment_intent: bool = False
    merchant_settlement_intent: bool = False
    agent_cash_in_intent: bool = False
    refund_intent: bool = False
    requested_clarification: bool = False
    complaint_time_utc: datetime | None = None
    complaint_date: date | None = None
    raw_keywords: list[str] = field(default_factory=list)


def _anchor_bst_date(transaction_timestamps: list[datetime]) -> date:
    if not transaction_timestamps:
        return datetime.utcnow().date()
    return max(transaction_timestamps).date()


def _extract_amount(text: str) -> float | None:
    amounts: list[int] = []
    for match in CURRENCY_AMOUNT_PATTERN.finditer(text):
        try:
            value = int(match.group(1))
        except ValueError:
            continue
        if value > 0:
            amounts.append(value)
    if amounts:
        return float(max(amounts))

    for match in PLAIN_AMOUNT_PATTERN.finditer(text):
        start = match.start(1)
        if start > 0 and text[start - 1] in {"-", "+"}:
            continue
        try:
            value = int(match.group(1))
        except ValueError:
            continue
        if 10 <= value <= 100000:
            amounts.append(value)
    if not amounts:
        return None
    return float(max(amounts))


def _extract_counterparty(text: str) -> str | None:
    for pattern in (PHONE_PATTERN, AGENT_PATTERN, MERCHANT_PATTERN):
        match = pattern.search(text)
        if match:
            value = match.group(0)
            if pattern is PHONE_PATTERN and not value.startswith("+880"):
                digits = re.sub(r"\D", "", value)
                if digits.startswith("0"):
                    digits = "88" + digits
                if digits.startswith("880"):
                    return "+" + digits
            return value.upper() if pattern is not PHONE_PATTERN else value
    return None


def _extract_complaint_time(text: str, transaction_timestamps: list[datetime]) -> datetime | None:
    anchor_date = _anchor_bst_date(transaction_timestamps)
    bst_date = anchor_date
    tzinfo = transaction_timestamps[0].tzinfo if transaction_timestamps else None
    lower_text = text.lower()

    if "usually happens" in lower_text:
        return None

    for phrase, offset_days in RELATIVE_TIME_KEYWORDS.items():
        if phrase in lower_text:
            bst_date = anchor_date + timedelta(days=offset_days)
            break

    explicit_hour: int | None = None
    explicit_minute = 0

    explicit_match = EXPLICIT_12H_TIME.search(lower_text)
    if explicit_match:
        hour = int(explicit_match.group(1)) % 12
        minute = int(explicit_match.group(2) or 0)
        meridiem = explicit_match.group(3)
        if meridiem == "pm":
            hour += 12
        explicit_hour = hour
        explicit_minute = minute

    bangla_match = EXPLICIT_BANGLA_HOUR.search(lower_text)
    if bangla_match and explicit_hour is None:
        explicit_hour = int(bangla_match.group(1))
        explicit_minute = 0

    if explicit_hour is None:
        for phrase, hour in PART_OF_DAY_HOURS.items():
            if phrase in lower_text:
                explicit_hour = hour
                break

    if explicit_hour is None:
        return None

    return datetime.combine(bst_date, time(explicit_hour, explicit_minute), tzinfo=tzinfo)


def _extract_complaint_date(text: str, transaction_timestamps: list[datetime]) -> date | None:
    anchor_date = _anchor_bst_date(transaction_timestamps)
    lower_text = text.lower()
    for phrase, offset_days in RELATIVE_TIME_KEYWORDS.items():
        if phrase in lower_text:
            return anchor_date + timedelta(days=offset_days)
    return None


def extract_intent(
    complaint: str,
    language: Language,
    transaction_timestamps: list[datetime],
) -> ComplaintIntent:
    lower_text = complaint.lower()
    matched_keywords: list[str] = []

    def any_keyword(keywords: list[str]) -> bool:
        found = [keyword for keyword in keywords if keyword in lower_text]
        matched_keywords.extend(found)
        return bool(found)

    wrong_transfer_intent = any_keyword(WRONG_TRANSFER_KEYWORDS)
    payment_failed_intent = any_keyword(PAYMENT_FAILED_KEYWORDS)
    duplicate_payment_intent = any_keyword(DUPLICATE_KEYWORDS)
    merchant_settlement_intent = any_keyword(SETTLEMENT_KEYWORDS)
    agent_cash_in_intent = any_keyword(CASH_IN_KEYWORDS)
    refund_intent = any_keyword(REFUND_KEYWORDS)
    is_fraud_signal = any_keyword(FRAUD_KEYWORDS)

    transaction_type_hint = None
    if wrong_transfer_intent:
        transaction_type_hint = TransactionType.TRANSFER
    elif duplicate_payment_intent or payment_failed_intent or refund_intent:
        transaction_type_hint = TransactionType.PAYMENT
    elif merchant_settlement_intent:
        transaction_type_hint = TransactionType.SETTLEMENT
    elif agent_cash_in_intent:
        transaction_type_hint = TransactionType.CASH_IN
    elif "sent " in lower_text or " পাঠ" in lower_text:
        transaction_type_hint = TransactionType.TRANSFER

    requested_clarification = len(complaint.split()) <= 6 or "something is wrong" in lower_text

    return ComplaintIntent(
        language=language,
        sanitized_complaint=complaint,
        amount=_extract_amount(complaint),
        counterparty=_extract_counterparty(complaint),
        transaction_type_hint=transaction_type_hint,
        is_fraud_signal=is_fraud_signal,
        wrong_transfer_intent=wrong_transfer_intent,
        payment_failed_intent=payment_failed_intent,
        duplicate_payment_intent=duplicate_payment_intent,
        merchant_settlement_intent=merchant_settlement_intent,
        agent_cash_in_intent=agent_cash_in_intent,
        refund_intent=refund_intent,
        requested_clarification=requested_clarification,
        complaint_time_utc=_extract_complaint_time(complaint, transaction_timestamps),
        complaint_date=_extract_complaint_date(complaint, transaction_timestamps),
        raw_keywords=matched_keywords,
    )
