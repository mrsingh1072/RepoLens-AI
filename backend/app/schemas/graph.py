"""Pydantic schemas for graph query API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DependencyItem(BaseModel):
    id: str
    label: str
    name: str
    relationship: str
    depth: int
    file_path: str | None = None


class DependencyResponse(BaseModel):
    repo_id: str
    symbol: str | None = None
    dependencies: list[DependencyItem]


class CallChainNode(BaseModel):
    id: str
    name: str
    label: str
    file_path: str | None = None


class CallChainItem(BaseModel):
    depth: int
    path: list[CallChainNode]


class CallChainResponse(BaseModel):
    repo_id: str
    symbol: str | None = None
    chains: list[CallChainItem]


class ArchitectureLayerItem(BaseModel):
    layer: str
    file_count: int
    symbol_count: int
    sample_files: list[str] = Field(default_factory=list)


class ArchitectureResponse(BaseModel):
    repo_id: str
    layers: list[ArchitectureLayerItem]
    cross_layer_calls: list[dict[str, str | int]] = Field(default_factory=list)


class GraphStatsResponse(BaseModel):
    repo_id: str
    node_counts: dict[str, int]
