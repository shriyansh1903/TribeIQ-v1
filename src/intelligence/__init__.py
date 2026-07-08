"""
===========================================================
TribeIQ Intelligence Layer
===========================================================

LLM-powered contextual intelligence for the hybrid
recommendation system.

Responsibilities:
1. Build structured recommendation context
2. Communicate with the configured LLM provider
3. Validate structured LLM responses
4. Rerank existing recommendation candidates
5. Preserve deterministic backend constraints

The intelligence layer never creates events and never
performs final recommendation selection.
===========================================================
"""

__version__ = "2.0.0"