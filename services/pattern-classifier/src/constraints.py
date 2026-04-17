"""Architectural constraints for the pattern classifier.

This module is the single source of truth for the hard limits that the classifier must honour.
These are **architectural**, not configurable — changing any value here changes the product's
compliance posture and must go through a works-council / DPIA review.

See:
    Business Plan v4.5 §11A.5 — Employee monitoring law, product response #2.
    docs/adr/008-hdbscan-pattern-classifier.md — ADR behind MIN_EMPLOYEE_AGGREGATION.
"""

from __future__ import annotations

# ----------------------------------------------------------------------------
# MIN_EMPLOYEE_AGGREGATION
# ----------------------------------------------------------------------------
# A pattern that has been observed in fewer than this many distinct employees
# MUST NOT be surfaced as a workflow candidate or proposal. This prevents the
# Watch layer from becoming individual-performance surveillance and is a
# non-negotiable compliance promise to DACH works councils.
#
# Do NOT wire this to an environment variable. Do NOT read it from tenant config.
# Do NOT add a "bypass for admin users" flag. If you need to change it, change it
# here, in the ADR, and in the Betriebsvereinbarung/instemmingsverzoek templates
# at the same time.
MIN_EMPLOYEE_AGGREGATION: int = 3


# ----------------------------------------------------------------------------
# MIN_OBSERVATION_WINDOW_DAYS
# ----------------------------------------------------------------------------
# The classifier refuses to emit candidates until it has this many days of
# observation. Shorter windows produce false positives (one-off sequences
# classified as repetitive) that waste review time and erode trust.
MIN_OBSERVATION_WINDOW_DAYS: int = 14


# ----------------------------------------------------------------------------
# MIN_PATTERN_RECURRENCE
# ----------------------------------------------------------------------------
# Sliding-window sequence extraction default. A candidate must recur at least
# this many times across the observation window to be considered.
MIN_PATTERN_RECURRENCE: int = 5


class AggregationGateViolation(Exception):
    """Raised when the min-employee aggregation gate is violated.

    Fail loud. Do not swallow this exception at call-sites. It indicates that something has tried
    to emit a candidate that would expose individual-employee behaviour — that is a compliance
    incident, not a programming error to route around.
    """
