from typing import TypedDict, Optional, List

class AgentState(TypedDict):
    # UI Inputs
    # client_id: str
    customer_id: Optional[str]
    type_credit: str
    amount: float
    repayment_period: int

    # Gathered Database Data (Supervisor Tools)
    credit_history: Optional[str]
    client_info: Optional[str]
    accounts_info: dict
    bank_params: Optional[str]
    details: dict
    
    # Processed and Validated Data
    structured_request: dict
    validation_warnings: list
    finance_data: dict

    # Agent Reports
    finance_report: Optional[str]
    documents_report: Optional[str]
    risk_report: Optional[str]

    # Final Output
    final_decision: Optional[str]
