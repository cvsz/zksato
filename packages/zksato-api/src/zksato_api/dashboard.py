"""Real-time dashboard API with WebSocket/SSE support for zksato."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from zksato_automation.agent_os.monitoring.dashboard import (
    OrchestrationMonitor,
    get_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Global monitor instance
_monitor: OrchestrationMonitor | None = None


def get_monitor_instance() -> OrchestrationMonitor:
    global _monitor
    if _monitor is None:
        _monitor = get_monitor()
    return _monitor


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.active_connections:
            return

        message_str = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as exc:
                logger.warning("Failed to send to WebSocket: %s", exc)
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            await self.disconnect(conn)


# Global connection manager
connection_manager = ConnectionManager()


# SSE Event Generator
async def event_generator() -> str:
    """Generate SSE events for real-time updates."""
    monitor = get_monitor_instance()
    while True:
        try:
            overview = monitor.get_overview()
            yield f"data: {json.dumps({'type': 'overview', 'data': overview})}\n\n"
        except Exception as exc:
            logger.error("SSE generation error: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
        await asyncio.sleep(2)  # Update every 2 seconds


# WebSocket Endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard updates."""
    await connection_manager.connect(websocket)
    try:
        monitor = get_monitor_instance()
        # Send initial state
        overview = monitor.get_overview()
        await websocket.send_text(json.dumps({"type": "initial", "data": overview}))

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                # Handle client messages (e.g., filter requests)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific events
                    pass
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.error("WebSocket error: %s", exc)
                break
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect(websocket)


# SSE Endpoint
@router.get("/sse")
async def sse_endpoint() -> StreamingResponse:
    """Server-Sent Events endpoint for real-time dashboard updates."""
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# REST Endpoints
class AgentStatusResponse(BaseModel):
    agent_id: str
    role: str
    status: str
    current_task_id: str | None
    provider: str | None
    model: str | None
    started_at: str | None
    last_activity: str
    tasks_completed: int
    tasks_failed: int
    last_error: str | None


class TaskStatusResponse(BaseModel):
    task_id: str
    plan_id: str
    title: str
    task_type: str
    state: str
    priority: int
    assigned_agent: str | None
    progress: float
    retry_count: int
    started_at: str | None


class ProviderStatusResponse(BaseModel):
    provider: str
    status: str
    latency_ms: float
    error_rate: float
    requests_per_minute: float
    available_models: list[str]
    rate_limit_remaining: int | None
    last_health_check: str


class QualityGateResponse(BaseModel):
    gate_name: str
    passed: bool
    details: str
    timestamp: str
    metrics: dict[str, Any]


class OverviewResponse(BaseModel):
    timestamp: str
    agents: dict[str, Any]
    tasks: dict[str, Any]
    plans: dict[str, Any]
    providers: dict[str, Any]
    quality_gates: dict[str, Any]


@router.get("/overview", response_model=OverviewResponse)
async def get_overview() -> OverviewResponse:
    """Get dashboard overview statistics."""
    monitor = get_monitor_instance()
    overview = monitor.get_overview()
    return OverviewResponse(**overview)


@router.get("/agents", response_model=list[AgentStatusResponse])
async def get_agents() -> list[AgentStatusResponse]:
    """Get all agents status."""
    monitor = get_monitor_instance()
    agents = monitor.list_agents()
    return [
        AgentStatusResponse(
            agent_id=a.agent_id,
            role=a.role,
            status=a.status,
            current_task_id=a.current_task_id,
            provider=a.provider,
            model=a.model,
            started_at=a.started_at.isoformat() if a.started_at else None,
            last_activity=a.last_activity.isoformat(),
            tasks_completed=a.tasks_completed,
            tasks_failed=a.tasks_failed,
            last_error=a.last_error,
        )
        for a in agents
    ]


@router.get("/tasks", response_model=list[TaskStatusResponse])
async def get_tasks(plan_id: str | None = None) -> list[TaskStatusResponse]:
    """Get all tasks, optionally filtered by plan."""
    monitor = get_monitor_instance()
    tasks = monitor.list_tasks(plan_id)
    return [
        TaskStatusResponse(
            task_id=str(t.task_id),
            plan_id=str(t.plan_id),
            title=t.title,
            task_type=t.task_type.value,
            state=t.state.value,
            priority=t.priority,
            assigned_agent=t.assigned_agent,
            progress=t.progress,
            retry_count=t.retry_count,
            started_at=t.started_at.isoformat() if t.started_at else None,
        )
        for t in tasks
    ]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskStatusResponse | dict[str, str]:
    """Get specific task details."""
    monitor = get_monitor_instance()
    task = monitor.get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return TaskStatusResponse(
        task_id=str(task.task_id),
        plan_id=str(task.plan_id),
        title=task.title,
        task_type=task.task_type.value,
        state=task.state.value,
        priority=task.priority,
        assigned_agent=task.assigned_agent,
        progress=task.progress,
        retry_count=task.retry_count,
        started_at=task.started_at.isoformat() if task.started_at else None,
    )


@router.get("/plans")
async def get_plans() -> list[dict[str, Any]]:
    """Get all plans."""
    monitor = get_monitor_instance()
    plans = monitor.list_plans()
    return [
        {
            "plan_id": str(p.plan_id),
            "objective": p.objective,
            "tasks_count": len(p.tasks),
            "completed_tasks": len(p.get_completed_tasks()),
            "has_failures": p.has_failures(),
            "is_complete": p.is_complete(),
        }
        for p in plans
    ]


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str) -> dict[str, Any] | dict[str, str]:
    """Get plan hierarchy and task details."""
    monitor = get_monitor_instance()
    hierarchy = monitor.get_task_hierarchy(plan_id)
    if not hierarchy:
        return {"error": "Plan not found"}
    return hierarchy


@router.get("/providers", response_model=list[ProviderStatusResponse])
async def get_providers() -> list[ProviderStatusResponse]:
    """Get all providers status."""
    monitor = get_monitor_instance()
    providers = monitor.list_providers()
    return [
        ProviderStatusResponse(
            provider=p.provider,
            status=p.status,
            latency_ms=p.latency_ms,
            error_rate=p.error_rate,
            requests_per_minute=p.requests_per_minute,
            available_models=p.available_models,
            rate_limit_remaining=p.rate_limit_remaining,
            last_health_check=p.last_health_check.isoformat(),
        )
        for p in providers
    ]


@router.get("/quality-gates", response_model=list[QualityGateResponse])
async def get_quality_gates(task_id: str | None = None) -> list[QualityGateResponse]:
    """Get quality gate results."""
    monitor = get_monitor_instance()
    gates = monitor.get_quality_gates(task_id)
    return [
        QualityGateResponse(
            gate_name=g.gate_name,
            passed=g.passed,
            details=g.details,
            timestamp=g.timestamp.isoformat(),
            metrics=g.metrics,
        )
        for g in gates
    ]


@router.post("/broadcast")
async def broadcast_update(data: dict[str, Any]) -> dict[str, str]:
    """Broadcast an update to all connected WebSocket clients."""
    await connection_manager.broadcast(data)
    return {"status": "broadcast sent"}


# Background task to periodically broadcast updates
async def periodic_broadcast() -> None:
    """Periodically broadcast overview updates to connected clients."""
    while True:
        try:
            monitor = get_monitor_instance()
            overview = monitor.get_overview()
            await connection_manager.broadcast(
                {
                    "type": "overview",
                    "data": overview,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:
            logger.error("Periodic broadcast error: %s", exc)
        await asyncio.sleep(5)  # Broadcast every 5 seconds


# Task to start periodic broadcast
_periodic_task: asyncio.Task | None = None


async def start_periodic_broadcast() -> None:
    """Start the periodic broadcast task."""
    global _periodic_task
    if _periodic_task is None or _periodic_task.done():
        _periodic_task = asyncio.create_task(periodic_broadcast())


async def stop_periodic_broadcast() -> None:
    """Stop the periodic broadcast task."""
    global _periodic_task
    if _periodic_task and not _periodic_task.done():
        _periodic_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _periodic_task


@dataclass
class DashboardService:
    """Provides dashboard data for backward compatibility."""

    def get_snapshot(self) -> dict[str, Any]:
        """Get current dashboard snapshot."""
        monitor = get_monitor_instance()
        return monitor.get_overview()

    def get_portfolio_widget(self) -> dict[str, Any]:
        """Get portfolio widget data."""
        return {"equity": 0, "pnl": 0, "positions": []}

    def get_orders_widget(self) -> dict[str, Any]:
        """Get orders widget data."""
        return {"open": 0, "filled": 0, "rejected": 0}

    def get_risk_widget(self) -> dict[str, Any]:
        """Get risk widget data."""
        return {"utilization": 0, "limits": {}}
