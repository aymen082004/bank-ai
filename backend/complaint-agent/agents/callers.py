"""
Agent Callers — thin wrappers around your friends' pre-built internal agents.

Each function:
  - receives a task string
  - calls the appropriate internal agent
  - returns a plain string result

Replace the placeholder bodies with the real import / HTTP / gRPC call
your team has agreed on.
"""

from __future__ import annotations

def _call_agent(agent_name: str, task: str) -> str:
    """
    Generic dispatcher.  Replace this with the real integration layer
    (e.g. internal REST call, shared function import, message queue, etc.)
    """

    return (
        f"[{agent_name}] Task received: '{task}'. "
        f"(Replace this stub with the real agent call.)"
    )


def call_reception_agent(task: str) -> str:
    """
    Reception Profile Agent
    Capabilities: customer Q&A, account opening, balance verification,
                  account statement generation.
    """
    return _call_agent("ReceptionProfileAgent", task)


def call_credit_agent(task: str) -> str:
    """
    Credit Profile Agent (Finance, Legal, Mortgage)
    Capabilities: credit file analysis, credit scoring,
                  acceptance / rejection decision.
    """
    return _call_agent("CreditProfileAgent", task)


def call_commercial_agent(task: str) -> str:
    """
    Commercial Profile Agent
    Capabilities: customer profile analysis, needs identification,
                  product recommendation (credit, bank card, …).
    """
    return _call_agent("CommercialProfileAgent", task)


def call_signature_checks_agent(task: str) -> str:
    """
    Signature & Checks Agent
    Capabilities: signature verification, check verification.
    """
    return _call_agent("SignatureChecksAgent", task)


def call_fraud_detection_agent(task: str) -> str:
    """
    Fraud Detection Agent
    Capabilities: transaction flow analysis,
                  classification — Non-fraud / Fraud / Suspicion.
    """
    return _call_agent("FraudDetectionAgent", task)


def call_analysis_reporting_agent(task: str) -> str:
    """
    Analysis & Reporting Agent
    Capabilities: agency activity analysis, dashboard creation,
                  KPI tracking (clients, withdrawals, loans…).
    """
    return _call_agent("AnalysisReportingAgent", task)


def call_recovery_agent(task: str) -> str:
    """
    Recovery Agent
    Capabilities: unpaid loan monitoring, customer follow-up,
                  risk-level procedure application.
    """
    return _call_agent("RecoveryAgent", task)


AGENT_REGISTRY: dict[str, callable] = {
    "reception":          call_reception_agent,
    "credit":             call_credit_agent,
    "commercial":         call_commercial_agent,
    "signature_checks":   call_signature_checks_agent,
    "fraud_detection":    call_fraud_detection_agent,
    "analysis_reporting": call_analysis_reporting_agent,
    "recovery":           call_recovery_agent,
}


def dispatch(agent_name: str, task: str) -> str:
    """
    Route a task to the right agent caller.
    Falls back gracefully if the agent name is unknown.
    """
    caller = AGENT_REGISTRY.get(agent_name.lower().replace(" ", "_"))
    if caller:
        return caller(task)
    return f"[Unknown agent '{agent_name}'] Task: '{task}' — no handler registered."
