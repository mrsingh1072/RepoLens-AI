"""Aggregate API router.

New feature routers should be registered here so ``main.create_app`` only ever
mounts a single top-level router.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import agent, analytics, diagrams, graph, health, ingestion, query

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ingestion.router)
api_router.include_router(graph.router)
api_router.include_router(query.router)
api_router.include_router(agent.router)
api_router.include_router(diagrams.router)
api_router.include_router(analytics.router)
