"""ServiceNow ticket triage and routing workflow.

Uses LangGraph for stateful ticket categorization, priority assessment,
and intelligent routing to the appropriate support team.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, TypedDict

from langgraph.graph import END, StateGraph

if TYPE_CHECKING:
    from ..graph.engine import WorkflowEngine


class TicketPriority(str, Enum):
    CRITICAL = "critical"  # P1 — service down
    HIGH = "high"  # P2 — major feature broken
    MEDIUM = "medium"  # P3 — degraded functionality
    LOW = "low"  # P4 — minor issue or request


class TicketCategory(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    SECURITY = "security"
    ACCESS_REQUEST = "access_request"
    GENERAL = "general"


ROUTING_TABLE: dict[str, str] = {
    "infrastructure": "infra-ops",
    "application": "app-support",
    "security": "security-team",
    "access_request": "iam-team",
    "general": "help-desk",
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "infrastructure": ["server", "network", "dns", "load balancer", "database", "outage", "down"],
    "application": ["bug", "error", "crash", "slow", "timeout", "feature", "ui"],
    "security": ["breach", "vulnerability", "phishing", "malware", "unauthorized", "suspicious"],
    "access_request": ["access", "permission", "login", "password", "mfa", "account", "onboard"],
}


class TriageState(TypedDict, total=False):
    ticket_id: str
    title: str
    description: str
    reporter: str
    category: str
    priority: str
    assigned_team: str
    sla_hours: int
    knowledge_articles: list[str]
    status: str
    results: list[dict[str, Any]]


def categorize_ticket(state: TriageState) -> TriageState:
    """Categorize the ticket based on title and description keywords."""
    text = f"{state.get('title', '')} {state.get('description', '')}".lower()

    best_category = TicketCategory.GENERAL
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = TicketCategory(category)

    return {**state, "category": best_category.value}


def assess_priority(state: TriageState) -> TriageState:
    """Assess ticket priority based on keywords and category."""
    text = f"{state.get('title', '')} {state.get('description', '')}".lower()

    if any(word in text for word in ["down", "outage", "breach", "critical", "production"]):
        priority = TicketPriority.CRITICAL
    elif any(word in text for word in ["broken", "crash", "urgent", "security"]):
        priority = TicketPriority.HIGH
    elif any(word in text for word in ["slow", "degraded", "intermittent"]):
        priority = TicketPriority.MEDIUM
    else:
        priority = TicketPriority.LOW

    sla_hours = {
        TicketPriority.CRITICAL: 1,
        TicketPriority.HIGH: 4,
        TicketPriority.MEDIUM: 24,
        TicketPriority.LOW: 72,
    }[priority]

    return {**state, "priority": priority.value, "sla_hours": sla_hours}


def route_ticket(state: TriageState) -> TriageState:
    """Route the ticket to the appropriate team."""
    category = state.get("category", TicketCategory.GENERAL.value)
    assigned_team = ROUTING_TABLE.get(category, "help-desk")
    return {**state, "assigned_team": assigned_team, "status": "routed"}


def search_knowledge_base(state: TriageState) -> TriageState:
    """Search for relevant knowledge base articles (stub for ServiceNow KB integration)."""
    # In production, this calls the ServiceNow connector's search_knowledge_base action
    return {**state, "knowledge_articles": []}


def finalize(state: TriageState) -> TriageState:
    """Finalize triage and produce results."""
    return {
        **state,
        "status": "completed",
        "results": [{
            "ticket_id": state.get("ticket_id"),
            "category": state.get("category"),
            "priority": state.get("priority"),
            "assigned_team": state.get("assigned_team"),
            "sla_hours": state.get("sla_hours"),
            "knowledge_articles": state.get("knowledge_articles", []),
        }],
    }


def build_graph() -> StateGraph:
    graph = StateGraph(TriageState)

    graph.add_node("categorize", categorize_ticket)
    graph.add_node("prioritize", assess_priority)
    graph.add_node("search_kb", search_knowledge_base)
    graph.add_node("route", route_ticket)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("categorize")
    graph.add_edge("categorize", "prioritize")
    graph.add_edge("prioritize", "search_kb")
    graph.add_edge("search_kb", "route")
    graph.add_edge("route", "finalize")
    graph.add_edge("finalize", END)

    return graph


def register_ticket_triage(engine: WorkflowEngine) -> None:
    engine.register("ticket_triage", build_graph())
