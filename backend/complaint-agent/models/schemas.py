"""
Pydantic models — shared across all agents in the complaint pipeline.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    agent: str = Field(description="Target agent name, e.g. 'fraud_detection'")
    task:  str = Field(description="Natural-language task description for that agent")
    result: Optional[str] = Field(default=None, description="Filled in after execution")


class OrchestratorReturn(BaseModel):
    main_problem: str          = Field(description="Core problem extracted from the complaint")
    tasks:        List[AgentTask] = Field(description="Tasks delegated to sub-agents")


class ResumeReturn(BaseModel):
    resume:  str  = Field(description="Human-readable synthesis of all agent results")
    solved:  bool = Field(description="True if the complaint is fully resolved")


class FollowUpReturn(BaseModel):
    follow_up_note: str = Field(description="Action taken or scheduled for follow-up")


class ComplaintRecord(BaseModel):
    id:             Optional[str]       = Field(default=None, alias="_id")
    customer_id:    str
    customer_name:  str
    complaint:      str                
    main_problem:   Optional[str]       = None
    tasks:          List[AgentTask]     = []
    resume:         Optional[str]       = None
    solved:         bool                = False
    followed_up:    bool                = False
    follow_up_note: Optional[str]       = None
    created_at:     Optional[datetime]  = None
    updated_at:     Optional[datetime]  = None

    class Config:
        populate_by_name = True


class ComplaintState(BaseModel):
    """Travels through every node in the LangGraph."""
    customer_id:   Optional[str]            = None
    customer_name: Optional[str]            = None
    complaint:     Optional[str]            = None
    user_prompt:   Optional[str]            = None

    complaint_id:  Optional[str]            = None  
    main_problem:  Optional[str]            = None
    tasks:         List[AgentTask]          = []
    resume:        Optional[str]            = None
    solved:        bool                     = False
    followed_up:   bool                     = False
    follow_up_note: Optional[str]           = None
    iteration:     int                      = 0
    max_iterations: int                     = 10
    user_context:  Optional[dict]           = None
    client_message: Optional[str]           = None
    suggested_booking_slots: List[dict[str, Any]] = []
    google_access_token: Optional[str]      = None
