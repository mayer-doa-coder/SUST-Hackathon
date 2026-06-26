from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.api.schemas import TransactionInput
from app.core.intent import ComplaintIntent
from app.domain.enums import CaseType, Department, EvidenceVerdict, Severity, TransactionStatus, TransactionType, UserType


@dataclass
class MatchCandidate:
    transaction: TransactionInput
    score: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class AnalysisFacts:
    relevant_transaction_id: str | None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    human_review_required: bool
    confidence: float | None
    reason_codes: list[str]
    matched_transaction: TransactionInput | None
    language: str


FINANCIAL_CASE_TYPES = {
    CaseType.WRONG_TRANSFER,
    CaseType.PAYMENT_FAILED,
    CaseType.DUPLICATE_PAYMENT,
    CaseType.MERCHANT_SETTLEMENT_DELAY,
    CaseType.AGENT_CASH_IN_ISSUE,
    CaseType.REFUND_REQUEST,
}


def _score_transaction(intent: ComplaintIntent, txn: TransactionInput) -> MatchCandidate:
    score = 0
    reasons: list[str] = []

    if intent.amount is not None:
        if txn.amount == intent.amount:
            score += 40
            reasons.append("amount_exact")
        elif intent.amount and abs(txn.amount - intent.amount) / intent.amount <= 0.05:
            score += 25
            reasons.append("amount_close")

    if intent.complaint_time_utc is not None:
        delta = abs(txn.timestamp - intent.complaint_time_utc)
        if delta <= timedelta(minutes=30):
            score += 30
            reasons.append("time_close")
        elif delta <= timedelta(hours=2):
            score += 20
            reasons.append("time_near")
        elif txn.timestamp.date() != intent.complaint_time_utc.date():
            score -= 10
            reasons.append("wrong_day")
    elif intent.complaint_date is not None:
        if txn.timestamp.date() == intent.complaint_date:
            score += 10
            reasons.append("date_match")
        else:
            score -= 10
            reasons.append("wrong_day")

    if intent.transaction_type_hint is not None and txn.type == intent.transaction_type_hint:
        score += 20
        reasons.append("type_match")

    if intent.counterparty and txn.counterparty and intent.counterparty.lower() == txn.counterparty.lower():
        score += 30
        reasons.append("counterparty_match")

    return MatchCandidate(transaction=txn, score=score, reasons=reasons)


def _find_duplicate_payment(transactions: list[TransactionInput]) -> tuple[TransactionInput | None, list[str]]:
    sorted_txns = sorted(transactions, key=lambda item: item.timestamp)
    for index in range(1, len(sorted_txns)):
        prev_txn = sorted_txns[index - 1]
        txn = sorted_txns[index]
        if (
            prev_txn.type == TransactionType.PAYMENT
            and txn.type == TransactionType.PAYMENT
            and prev_txn.amount == txn.amount
            and prev_txn.counterparty == txn.counterparty
            and prev_txn.status == TransactionStatus.COMPLETED
            and txn.status == TransactionStatus.COMPLETED
            and (txn.timestamp - prev_txn.timestamp) <= timedelta(seconds=60)
        ):
            return txn, ["duplicate_payment", "transaction_match"]
    return None, []


def _established_recipient(intent: ComplaintIntent, matched_transaction: TransactionInput, transactions: list[TransactionInput]) -> bool:
    if not intent.wrong_transfer_intent or not matched_transaction.counterparty:
        return False
    previous = [
        txn
        for txn in transactions
        if txn.timestamp < matched_transaction.timestamp
        and txn.counterparty == matched_transaction.counterparty
        and txn.type == TransactionType.TRANSFER
    ]
    return len(previous) >= 2


def _classify_case(intent: ComplaintIntent, matched_transaction: TransactionInput | None) -> CaseType:
    if intent.is_fraud_signal:
        return CaseType.PHISHING
    if intent.duplicate_payment_intent:
        return CaseType.DUPLICATE_PAYMENT
    if intent.wrong_transfer_intent:
        return CaseType.WRONG_TRANSFER
    if intent.transaction_type_hint == TransactionType.TRANSFER and "didn't get" in intent.sanitized_complaint.lower():
        return CaseType.WRONG_TRANSFER
    if intent.payment_failed_intent or (matched_transaction and matched_transaction.status == TransactionStatus.FAILED):
        return CaseType.PAYMENT_FAILED
    if intent.merchant_settlement_intent or (matched_transaction and matched_transaction.type == TransactionType.SETTLEMENT):
        return CaseType.MERCHANT_SETTLEMENT_DELAY
    if intent.agent_cash_in_intent or (matched_transaction and matched_transaction.type == TransactionType.CASH_IN):
        return CaseType.AGENT_CASH_IN_ISSUE
    if intent.refund_intent:
        return CaseType.REFUND_REQUEST
    return CaseType.OTHER


def _assign_severity(case_type: CaseType, verdict: EvidenceVerdict) -> Severity:
    if case_type == CaseType.PHISHING:
        return Severity.CRITICAL
    if case_type == CaseType.WRONG_TRANSFER:
        return Severity.HIGH if verdict == EvidenceVerdict.CONSISTENT else Severity.MEDIUM
    if case_type == CaseType.PAYMENT_FAILED:
        return Severity.HIGH
    if case_type == CaseType.DUPLICATE_PAYMENT:
        return Severity.HIGH
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return Severity.MEDIUM
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return Severity.HIGH
    if case_type == CaseType.REFUND_REQUEST and verdict == EvidenceVerdict.CONSISTENT:
        return Severity.LOW
    return Severity.LOW


def _route_department(case_type: CaseType, user_type: UserType, matched_transaction: TransactionInput | None) -> Department:
    if case_type == CaseType.PHISHING:
        return Department.FRAUD_RISK
    if case_type == CaseType.WRONG_TRANSFER:
        return Department.DISPUTE_RESOLUTION
    if case_type == CaseType.REFUND_REQUEST and user_type == UserType.CUSTOMER:
        return Department.CUSTOMER_SUPPORT
    if case_type in {CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT}:
        return Department.PAYMENTS_OPS
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY or user_type == UserType.MERCHANT:
        return Department.MERCHANT_OPERATIONS
    if case_type == CaseType.AGENT_CASH_IN_ISSUE or user_type == UserType.AGENT:
        return Department.AGENT_OPERATIONS
    if matched_transaction and matched_transaction.type == TransactionType.SETTLEMENT and user_type == UserType.MERCHANT:
        return Department.MERCHANT_OPERATIONS
    return Department.CUSTOMER_SUPPORT


def _requires_human_review(
    case_type: CaseType,
    verdict: EvidenceVerdict,
    matched_transaction: TransactionInput | None,
    ambiguous_match: bool,
) -> bool:
    if case_type in {CaseType.PHISHING, CaseType.DUPLICATE_PAYMENT}:
        return True
    if case_type == CaseType.WRONG_TRANSFER and verdict != EvidenceVerdict.INSUFFICIENT_DATA:
        return True
    if verdict == EvidenceVerdict.INCONSISTENT:
        return True
    if ambiguous_match and case_type not in {CaseType.OTHER, CaseType.WRONG_TRANSFER}:
        return True
    if matched_transaction is not None:
        pending_review_types = FINANCIAL_CASE_TYPES - {CaseType.MERCHANT_SETTLEMENT_DELAY}
        if matched_transaction.status == TransactionStatus.PENDING and case_type in pending_review_types:
            return True
        if matched_transaction.amount >= 10000 and case_type not in {CaseType.MERCHANT_SETTLEMENT_DELAY, CaseType.REFUND_REQUEST}:
            return True
    if verdict == EvidenceVerdict.INSUFFICIENT_DATA and case_type in FINANCIAL_CASE_TYPES and case_type not in {CaseType.OTHER, CaseType.WRONG_TRANSFER}:
        return True
    return False


def _compute_confidence(
    top_score: int,
    verdict: EvidenceVerdict,
    is_fraud_signal: bool,
    language: str,
) -> float:
    confidence = top_score / 100.0
    if verdict == EvidenceVerdict.CONSISTENT:
        confidence += 0.2
    if verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        confidence -= 0.1
    if is_fraud_signal:
        confidence += 0.1
    if language == "mixed":
        confidence -= 0.05
    return max(0.0, min(1.0, round(confidence, 2)))


def investigate(
    intent: ComplaintIntent,
    transactions: list[TransactionInput],
    user_type: UserType,
) -> AnalysisFacts:
    duplicate_txn, duplicate_reasons = _find_duplicate_payment(transactions)
    if duplicate_txn is not None and intent.duplicate_payment_intent:
        verdict = EvidenceVerdict.CONSISTENT
        case_type = CaseType.DUPLICATE_PAYMENT
        severity = _assign_severity(case_type, verdict)
        department = _route_department(case_type, user_type, duplicate_txn)
        human_review_required = _requires_human_review(case_type, verdict, duplicate_txn, False)
        return AnalysisFacts(
            relevant_transaction_id=duplicate_txn.transaction_id,
            evidence_verdict=verdict,
            case_type=case_type,
            severity=severity,
            department=department,
            human_review_required=human_review_required,
            confidence=_compute_confidence(95, verdict, intent.is_fraud_signal, intent.language.value),
            reason_codes=duplicate_reasons + ["biller_verification_required"],
            matched_transaction=duplicate_txn,
            language=intent.language.value,
        )

    candidates = sorted(
        (_score_transaction(intent, txn) for txn in transactions),
        key=lambda candidate: candidate.score,
        reverse=True,
    )
    above_fifty = [candidate for candidate in candidates if candidate.score >= 50]
    top_candidate = candidates[0] if candidates else None

    ambiguous_match = len(above_fifty) >= 2
    no_reasonable_match = top_candidate is None or top_candidate.score < 30
    clear_match = top_candidate is not None and top_candidate.score >= 60 and not ambiguous_match
    if len(transactions) == 1 and top_candidate is not None and top_candidate.score >= 50 and not ambiguous_match:
        clear_match = True

    matched_transaction = top_candidate.transaction if clear_match else None
    case_type = _classify_case(intent, matched_transaction)
    verdict = EvidenceVerdict.INSUFFICIENT_DATA
    reason_codes: list[str] = []

    if case_type == CaseType.PHISHING:
        severity = _assign_severity(case_type, verdict)
        department = _route_department(case_type, user_type, matched_transaction)
        return AnalysisFacts(
            relevant_transaction_id=None,
            evidence_verdict=EvidenceVerdict.INSUFFICIENT_DATA,
            case_type=case_type,
            severity=severity,
            department=department,
            human_review_required=True,
            confidence=_compute_confidence(85, EvidenceVerdict.INSUFFICIENT_DATA, True, intent.language.value),
            reason_codes=["phishing", "critical_escalation"],
            matched_transaction=None,
            language=intent.language.value,
        )

    if clear_match and matched_transaction is not None:
        if _established_recipient(intent, matched_transaction, transactions):
            verdict = EvidenceVerdict.INCONSISTENT
            reason_codes.extend(["established_recipient_pattern", "evidence_inconsistent"])
        else:
            verdict = EvidenceVerdict.CONSISTENT
            reason_codes.extend(top_candidate.reasons)
    else:
        verdict = EvidenceVerdict.INSUFFICIENT_DATA
        if ambiguous_match:
            reason_codes.append("ambiguous_match")
        elif no_reasonable_match:
            reason_codes.append("no_transaction_match")
        else:
            reason_codes.append("needs_clarification")

    severity = _assign_severity(case_type, verdict)
    department = _route_department(case_type, user_type, matched_transaction)
    human_review_required = _requires_human_review(case_type, verdict, matched_transaction, ambiguous_match)

    if case_type == CaseType.OTHER and verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        human_review_required = False
        reason_codes.append("needs_clarification")
    if case_type == CaseType.REFUND_REQUEST and verdict == EvidenceVerdict.CONSISTENT:
        human_review_required = False

    if matched_transaction is not None:
        reason_codes.insert(0, "transaction_match")

    return AnalysisFacts(
        relevant_transaction_id=matched_transaction.transaction_id if matched_transaction else None,
        evidence_verdict=verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        human_review_required=human_review_required,
        confidence=_compute_confidence(top_candidate.score if top_candidate else 0, verdict, intent.is_fraud_signal, intent.language.value),
        reason_codes=list(dict.fromkeys(reason_codes)),
        matched_transaction=matched_transaction,
        language=intent.language.value,
    )
