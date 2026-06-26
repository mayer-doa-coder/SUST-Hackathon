from __future__ import annotations

from app.core.reasoning import AnalysisFacts
from app.domain.enums import CaseType, EvidenceVerdict, Language, UserType


def build_template_summary(
    ticket_id: str,
    complaint: str,
    facts: AnalysisFacts,
    user_type: UserType,
) -> tuple[str, str, str]:
    txn_id = facts.relevant_transaction_id or "no confirmed transaction"
    verdict = facts.evidence_verdict.value.replace("_", " ")

    if facts.case_type == CaseType.PHISHING:
        summary = "Customer reports a likely phishing or social engineering attempt and has raised a credential-safety concern."
        next_action = "Escalate to fraud_risk immediately, confirm official safety guidance, and log the reported contact details if available."
    elif facts.case_type == CaseType.WRONG_TRANSFER:
        summary = f"Customer likely refers to transaction {txn_id}. Evidence verdict is {verdict} for a wrong-transfer complaint."
        if facts.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
            next_action = "Request the recipient number or clearer transaction details before initiating a dispute."
        else:
            next_action = f"Review transaction {txn_id} and follow the wrong-transfer dispute workflow."
    elif facts.case_type == CaseType.PAYMENT_FAILED:
        summary = f"Customer reports a failed payment linked to {txn_id}. Evidence verdict is {verdict}."
        next_action = f"Investigate transaction {txn_id} and confirm whether any eligible reversal should proceed through official operations."
    elif facts.case_type == CaseType.DUPLICATE_PAYMENT:
        summary = f"Customer may have been charged twice, with {txn_id} identified as the likely duplicate transaction."
        next_action = f"Verify duplicate payment evidence for {txn_id} and confirm biller-side receipt before any reversal workflow."
    elif facts.case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        summary = f"Merchant settlement issue linked to {txn_id}. Evidence verdict is {verdict}."
        next_action = "Route to merchant operations to verify batch status and communicate the expected update window."
    elif facts.case_type == CaseType.AGENT_CASH_IN_ISSUE:
        summary = f"Customer reports a cash-in issue linked to {txn_id}. Evidence verdict is {verdict}."
        next_action = f"Check the agent-side and platform-side status of {txn_id} and follow the standard cash-in investigation flow."
    elif facts.case_type == CaseType.REFUND_REQUEST:
        summary = f"Customer is requesting a refund related to {txn_id}. Evidence verdict is {verdict}."
        next_action = "Explain that refund eligibility depends on policy and guide the customer through the correct support path without promising the outcome."
    else:
        summary = "Customer complaint is too vague to confirm a specific transaction or case path from the provided evidence."
        next_action = "Ask the customer for the transaction ID, amount, and approximate time so the case can be investigated accurately."

    if facts.language == Language.BN.value:
        reply = _customer_reply_bn(ticket_id, facts, user_type)
    elif facts.language == Language.MIXED.value:
        reply = _customer_reply_mixed(ticket_id, facts, user_type)
    else:
        reply = _customer_reply_en(ticket_id, facts, user_type)

    return summary, next_action, reply


def _customer_reply_en(ticket_id: str, facts: AnalysisFacts, user_type: UserType) -> str:
    if facts.case_type == CaseType.PHISHING:
        return (
            "Thank you for contacting us before sharing any information. We never ask for your PIN, OTP, or password. "
            "Our fraud team has been alerted and will continue the review through official channels."
        )
    if facts.case_type == CaseType.OTHER and facts.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        return (
            "Thank you for reaching out. To help you faster, please share the transaction ID, the amount involved, "
            "and a short description of what went wrong. Please do not share your PIN or OTP with anyone."
        )
    if facts.case_type == CaseType.WRONG_TRANSFER and facts.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        return (
            "Thank you for reaching out. We could not confirm the exact transaction yet. Please share the recipient number "
            "or transaction ID so we can investigate through the correct dispute process. Please do not share your PIN or OTP with anyone."
        )
    if user_type == UserType.MERCHANT:
        return (
            f"We have recorded your concern regarding {facts.relevant_transaction_id or ticket_id}. "
            "Our team will review the matter and update you through official channels."
        )
    if facts.case_type in {CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT}:
        return (
            f"We have noted the issue related to {facts.relevant_transaction_id or ticket_id}. "
            "Our payments team will review the case, and any eligible amount will be processed through official channels. "
            "Please do not share your PIN or OTP with anyone."
        )
    return (
        f"We have noted your concern regarding {facts.relevant_transaction_id or ticket_id}. "
        "Our team will review the case and update you through official support channels. "
        "Please do not share your PIN or OTP with anyone."
    )


def _customer_reply_bn(ticket_id: str, facts: AnalysisFacts, _: UserType) -> str:
    if facts.case_type == CaseType.OTHER and facts.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        return (
            "ধন্যবাদ যোগাযোগ করার জন্য। দ্রুত সহায়তার জন্য অনুগ্রহ করে লেনদেন আইডি, টাকার পরিমাণ এবং কী সমস্যা হয়েছে তা সংক্ষেপে জানান। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    return (
        f"আপনার বিষয়টি {facts.relevant_transaction_id or ticket_id} সম্পর্কিত হিসেবে নোট করা হয়েছে। "
        "আমাদের দল অফিসিয়াল চ্যানেলে এটি যাচাই করে আপনাকে জানাবে। "
        "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
    )


def _customer_reply_mixed(ticket_id: str, facts: AnalysisFacts, _: UserType) -> str:
    if facts.case_type == CaseType.OTHER and facts.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        return (
            "Dhonnobad jogajog korar jonno. Fast help er jonno transaction ID, amount, ar ki problem hoyeche seta ektu bolben. "
            "Please apnar PIN ba OTP karo shathe share korben na."
        )
    return (
        f"Apnar concern {facts.relevant_transaction_id or ticket_id} niye amra note korechi. "
        "Official channel diye update deya hobe. Please apnar PIN ba OTP karo shathe share korben na."
    )

