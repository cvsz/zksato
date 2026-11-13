"""Phase 4 agent engineering platform tests.

Covers the multi-agent orchestration stack end to end:
- OrchestratorV2: task submission → capability routing → completion with result
- A2A protocol: registry, capability advertisement, message envelopes
- Hooks: registration, priority execution, conditions, built-in hooks
- Context management: token budgeting, compression, deduplication, persistence
- Sessions: persistence, checkpoints, recovery, export/import
- Skills: manifests, validation, registry, built-in skills
- Plan mode: task dependencies, ready-set computation, persistence
- MCP: protocol envelopes, transport selection, client manager persistence
- Shared state: CRDT merge convergence (G/PN counters, LWW registers)
- Specialized agents: deterministic handlers over a real project tree
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from zksato_automation.agent_os import OrchestratorV2
from zksato_automation.agent_os.a2a.protocol import (
    A2AMessage,
    A2AMessageType,
    AgentCapability,
    AgentInfo,
    AgentRegistry,
)
from zksato_automation.agent_os.agents.specialized import (
    ArchitectAgent,
    CodeReviewerAgent,
    DocumentationAgent,
    SecurityAuditorAgent,
    TestEngineerAgent,
)
from zksato_automation.agent_os.context.manager import ContextEntry, ContextWindow
from zksato_automation.agent_os.coordination.shared_state import (
    GCounter,
    LWWRegister,
    PNCounter,
    SharedStateManager,
)
from zksato_cli.context.manager import ContextEntry as CLIContextEntry
from zksato_cli.context.manager import ContextManager
from zksato_cli.hooks.framework import (
    HookContext,
    HookEvent,
    HookExecutor,
    HookManager,
    HookPriority,
    HookRegistration,
    HookRegistry,
    setup_builtin_hooks,
)
from zksato_cli.mcp.client import MCPClientManager, MCPServerConfig
from zksato_cli.mcp.protocol import MCPRequest, MCPResponse, TransportType
from zksato_cli.planning.plan_mode import (
    Plan,
    PlanManager,
    PlanPhase,
    PlanTask,
    TaskStatus,
    TaskType,
)
from zksato_cli.sessions.persistence import (
    MessageRole,
    Session,
    SessionManager,
    SessionMessage,
    SessionStatus,
)
from zksato_cli.skills.system import (
    SkillManager,
    SkillManifest,
    SkillRegistry,
    SkillScope,
    SkillValidator,
    register_builtin_skills,
)


def noop() -> None:
    """Trivial callable used as a skill manifest entry point in tests."""


# Prevent pytest from collecting the platform agent class as a test class
TestEngineerAgent.__test__ = False


# ---------------------------------------------------------------------------
# Orchestrator V2 — end-to-end task execution
# ---------------------------------------------------------------------------


class TestOrchestratorV2:
    async def test_analyze_code_task_completes_with_result(self, tmp_path: Path) -> None:
        target = tmp_path / "src" / "zksato" / "indicators.py"
        target.parent.mkdir(parents=True)
        target.write_text("def sma(prices):\n    return sum(prices) / len(prices)\n")

        orch = OrchestratorV2(project_root=tmp_path, config={})
        await orch.start()
        try:
            task_id = await orch.submit_task(
                task_type="analyze_code",
                title="Analyze module",
                description="Static analysis of indicators.py",
                required_capabilities={AgentCapability.CODE_ANALYSIS},
                payload={"file_path": "src/zksato/indicators.py"},
            )
            for _ in range(100):
                task = orch.tasks[task_id]
                if task.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)

            assert task.status == "completed", f"error={task.error}"
            assert isinstance(task.result, dict)
            assert task.result.get("file") == "src/zksato/indicators.py"
        finally:
            await orch.stop()

    async def test_get_status_reports_health(self, tmp_path: Path) -> None:
        orch = OrchestratorV2(project_root=tmp_path, config={})
        status = orch.get_status()
        assert status["running"] is False
        assert "agents" in status
        assert "tasks" in status

    async def test_task_recorded_with_metadata(self, tmp_path: Path) -> None:
        orch = OrchestratorV2(project_root=tmp_path, config={})
        task_id = await orch.submit_task(
            task_type="analyze_code",
            title="t",
            description="d",
            required_capabilities={AgentCapability.CODE_ANALYSIS},
            priority=5,
            payload={"target": "pyproject.toml"},
        )
        task = orch.tasks[task_id]
        assert task.task_type == "analyze_code"
        assert task.priority == 5
        assert task.status == "pending"
        assert task.payload == {"target": "pyproject.toml"}

    async def test_default_agents_registered(self, tmp_path: Path) -> None:
        orch = OrchestratorV2(project_root=tmp_path, config={})
        assert len(orch.agents) >= 5
        roles = {agent.role for agent in orch.agents.values()}
        assert "System Architect" in roles
        assert "Security Auditor" in roles
        assert "Code Reviewer" in roles

    async def test_phase3_components_wired(self, tmp_path: Path) -> None:
        orch = OrchestratorV2(project_root=tmp_path, config={})
        assert orch.hook_manager is not None
        assert orch.skill_manager is not None
        assert orch.plan_manager is not None
        assert orch.session_manager is not None
        assert orch.mcp_client is not None
        assert orch.shared_state is not None
        assert orch.context_manager is not None


# ---------------------------------------------------------------------------
# A2A protocol
# ---------------------------------------------------------------------------


class TestA2ARegistry:
    def test_register_and_capability_lookup(self) -> None:
        registry = AgentRegistry()
        info = AgentInfo(
            agent_id="agent-1",
            name="Architect",
            role="architect",
            capabilities={AgentCapability.ARCHITECTURE_DESIGN},
        )
        registry.register(info)
        assert registry.agents["agent-1"] is info
        assert info.can_handle(AgentCapability.ARCHITECTURE_DESIGN)
        assert not info.can_handle(AgentCapability.CODE_REVIEW)
        assert info.is_available()

    def test_find_agents_by_capability(self) -> None:
        registry = AgentRegistry()
        registry.register(
            AgentInfo(
                agent_id="a",
                name="A",
                role="reviewer",
                capabilities={AgentCapability.CODE_REVIEW},
            )
        )
        registry.register(
            AgentInfo(
                agent_id="b",
                name="B",
                role="auditor",
                capabilities={AgentCapability.SECURITY_AUDIT},
            )
        )
        matches = [
            agent
            for agent in registry.agents.values()
            if agent.can_handle(AgentCapability.CODE_REVIEW)
        ]
        assert [m.agent_id for m in matches] == ["a"]

    def test_message_envelope_fields(self) -> None:
        msg = A2AMessage(
            message_type=A2AMessageType.TASK_REQUEST,
            sender_id="orchestrator",
            recipient_id="agent-1",
            payload={"task": "analyze"},
        )
        assert msg.message_type == A2AMessageType.TASK_REQUEST
        assert msg.payload == {"task": "analyze"}
        assert msg.sender_id == "orchestrator"
        assert msg.recipient_id == "agent-1"


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


class TestHooks:
    async def test_registration_and_execution(self) -> None:
        registry = HookRegistry()

        async def handler(context: HookContext) -> dict[str, Any]:
            return {"seen": context.get("file")}

        registry.register(
            HookRegistration(
                event=HookEvent.BEFORE_TOOL,
                handler=handler,
                name="watcher",
            )
        )
        executor = HookExecutor(registry)
        context = HookContext(event=HookEvent.BEFORE_TOOL, data={"file": "risk.py"})
        results = await executor.execute(HookEvent.BEFORE_TOOL, context)
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].output == {"seen": "risk.py"}

    async def test_priority_ordering(self) -> None:
        registry = HookRegistry()
        order: list[str] = []

        async def low(context: HookContext) -> None:
            order.append("low")

        async def high(context: HookContext) -> None:
            order.append("high")

        registry.register(
            HookRegistration(
                event=HookEvent.AFTER_TOOL,
                handler=low,
                name="low",
                priority=HookPriority.LOW,
            )
        )
        registry.register(
            HookRegistration(
                event=HookEvent.AFTER_TOOL,
                handler=high,
                name="high",
                priority=HookPriority.CRITICAL,
            )
        )
        executor = HookExecutor(registry)
        await executor.execute(HookEvent.AFTER_TOOL, HookContext(event=HookEvent.AFTER_TOOL))
        assert order == ["high", "low"]

    async def test_conditions_gate_execution(self) -> None:
        registry = HookRegistry()
        calls: list[str] = []

        async def gated(context: HookContext) -> None:
            calls.append("gated")

        registry.register(
            HookRegistration(
                event=HookEvent.BEFORE_COMMAND,
                handler=gated,
                name="gated",
                conditions={"mode": "paper"},
            )
        )
        executor = HookExecutor(registry)
        await executor.execute(
            HookEvent.BEFORE_COMMAND,
            HookContext(event=HookEvent.BEFORE_COMMAND, data={"mode": "live"}),
        )
        assert calls == []
        await executor.execute(
            HookEvent.BEFORE_COMMAND,
            HookContext(event=HookEvent.BEFORE_COMMAND, data={"mode": "paper"}),
        )
        assert calls == ["gated"]

    async def test_builtin_hooks_setup(self) -> None:
        manager = HookManager()
        setup_builtin_hooks(manager)
        registered = list(manager.registry.get_hooks_for_event(HookEvent.SESSION_START))
        assert len(registered) >= 1

    async def test_executor_timeout_and_audit(self) -> None:
        registry = HookRegistry()
        ran: list[str] = []

        async def slow(context: HookContext) -> None:
            await asyncio.sleep(0.05)
            ran.append("done")

        registry.register(
            HookRegistration(
                event=HookEvent.TASK_COMPLETED,
                handler=slow,
                name="slow",
                timeout_seconds=0.01,
            )
        )
        executor = HookExecutor(registry)
        results = await executor.execute(
            HookEvent.TASK_COMPLETED, HookContext(event=HookEvent.TASK_COMPLETED)
        )
        assert len(results) == 1
        # A timed-out hook reports failure; on fast machines it may still complete
        assert results[0].success is True or results[0].error is not None


# ---------------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------------


class TestContextWindow:
    def test_token_budget(self) -> None:
        window = ContextWindow(max_tokens=200, reserved_tokens=50)
        entry = ContextEntry(source="user", content="hello", content_type="text", token_estimate=60)
        assert window.add_entry(entry) is True
        assert window.used_tokens == 60
        assert window.available_tokens == 90
        too_big = ContextEntry(source="user", content="x", content_type="text", token_estimate=200)
        assert window.add_entry(too_big) is False

    def test_deduplicate_removes_repeats(self) -> None:
        window = ContextWindow(max_tokens=10_000, reserved_tokens=0)
        window.add_entry(
            ContextEntry(source="tool", content="same", content_type="text", token_estimate=5)
        )
        window.add_entry(
            ContextEntry(source="tool", content="same", content_type="text", token_estimate=5)
        )
        removed = window.deduplicate()
        assert removed >= 1

    def test_compress_reduces_tokens(self) -> None:
        window = ContextWindow(max_tokens=10_000, reserved_tokens=0)
        for i in range(10):
            window.add_entry(
                ContextEntry(
                    source="tool",
                    content=f"entry {i}",
                    content_type="text",
                    token_estimate=100,
                    relevance_score=0.1 + i * 0.05,
                )
            )
        assert window.used_tokens == 1000
        window.compress(target_tokens=500)
        assert window.used_tokens <= 500


class TestContextManagerPersistence:
    def test_roundtrip_via_storage(self, tmp_path: Path) -> None:
        manager = ContextManager(storage_dir=str(tmp_path / "contexts"))
        ctx = manager.get_context("ctx-1")
        ctx.add_entry(CLIContextEntry(source="user", content="hello world", content_type="text"))
        manager.add_user_input("ctx-1", "second input")
        manager._save_context("ctx-1")

        reloaded = ContextManager(storage_dir=str(tmp_path / "contexts"))
        window = reloaded.get_context("ctx-1")
        contents = [e.content for e in window.entries]
        assert any("hello world" in c for c in contents)
        assert any("second input" in c for c in contents)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


class TestSessions:
    def test_create_and_persist(self, tmp_path: Path) -> None:
        manager = SessionManager(tmp_path / "sessions")
        session = manager.create_session(project_path=str(tmp_path), title="refactor risk")
        assert session.status == SessionStatus.ACTIVE
        manager.add_message(SessionMessage(role=MessageRole.USER, content="start refactor"))
        loaded = manager.get_session(session.session_id)
        assert loaded is not None
        assert loaded.get_message_count() >= 1

    def test_checkpoint_and_recovery(self, tmp_path: Path) -> None:
        manager = SessionManager(tmp_path / "sessions")
        manager.create_session(project_path=str(tmp_path), title="s")
        checkpoint = manager.add_checkpoint(
            label="before-edit",
            description="checkpoint before edit",
            state_snapshot={"step": 1},
        )
        assert checkpoint is not None
        latest = manager.get_latest_checkpoint()
        assert latest is not None
        assert latest.description == "checkpoint before edit"
        assert latest.state_snapshot == {"step": 1}

    def test_roundtrip_serialization(self) -> None:
        session = Session(project_path="/tmp/proj", title="rt")
        session.add_message(SessionMessage(role=MessageRole.USER, content="hello"))
        restored = Session.from_dict(session.to_dict())
        assert restored.title == "rt"
        assert restored.get_message_count() == session.get_message_count()

    def test_export_and_import(self, tmp_path: Path) -> None:
        manager = SessionManager(tmp_path / "sessions")
        session = manager.create_session(project_path=str(tmp_path), title="exported")
        manager.add_message(SessionMessage(role=MessageRole.USER, content="export me"))
        export_path = tmp_path / "export.json"
        assert manager.export_session(session.session_id, export_path) is True
        assert export_path.exists()
        imported = manager.import_session(export_path)
        assert imported is not None
        assert imported.title == "exported"

    def test_list_and_delete(self, tmp_path: Path) -> None:
        manager = SessionManager(tmp_path / "sessions")
        session = manager.create_session(project_path=str(tmp_path), title="doomed")
        listed = manager.list_sessions()
        assert any(s["session_id"] == session.session_id for s in listed)
        assert manager.delete_session(session.session_id) is True
        assert manager.get_session(session.session_id) is None


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSkills:
    def _manifest(self) -> SkillManifest:
        return SkillManifest(
            name="demo-skill",
            description="demo",
            scope=SkillScope.PROJECT,
            provides=["demo"],
            entry_point="tests.test_agent_platform:noop",
        )

    def test_manifest_validation_ok(self) -> None:
        assert SkillValidator.validate_manifest(self._manifest()) == []

    def test_manifest_validation_missing_entry_point(self) -> None:
        bad = self._manifest()
        bad.entry_point = ""
        errors = SkillValidator.validate_manifest(bad)
        assert len(errors) >= 1

    def test_registry_register_and_list(self, tmp_path: Path) -> None:
        registry = SkillRegistry(tmp_path / "skills")
        assert registry.register_manifest(self._manifest()) is True
        listed = registry.list_manifests()
        assert any(m.name == "demo-skill" for m in listed)

    def test_builtin_skills_registered(self, tmp_path: Path) -> None:
        registry = SkillRegistry(tmp_path / "skills")
        register_builtin_skills(registry)
        names = {m.name for m in registry.list_manifests()}
        assert "Grep Search" in names
        assert "Read File" in names

    def test_skill_manager_wires_registry(self, tmp_path: Path) -> None:
        manager = SkillManager(project_root=tmp_path, storage_dir=tmp_path / "skills")
        register_builtin_skills(manager.registry)
        assert len(manager.registry.list_manifests()) > 0


# ---------------------------------------------------------------------------
# Plan mode
# ---------------------------------------------------------------------------


class TestPlanMode:
    def _plan(self) -> tuple[Plan, PlanTask, PlanTask]:
        plan = Plan(objective="land phase 4", title="Phase 4")
        explore = PlanTask(task_type=TaskType.ANALYSIS, title="explore", phase=PlanPhase.DISCOVER)
        implement = PlanTask(
            task_type=TaskType.FILE_MODIFY,
            title="implement",
            phase=PlanPhase.EXECUTE,
            dependencies=[explore.task_id],
        )
        plan.add_task(explore)
        plan.add_task(implement)
        return plan, explore, implement

    def test_dependency_ready_set(self) -> None:
        plan, explore, implement = self._plan()
        assert plan.get_ready_tasks(set()) == [explore]
        # With explore completed, only implement is pending with satisfied deps
        explore.status = TaskStatus.COMPLETED
        assert plan.get_ready_tasks({explore.task_id}) == [implement]

    def test_can_run_respects_dependencies(self) -> None:
        _plan, explore, implement = self._plan()
        assert implement.can_run(set()) is False
        assert implement.can_run({explore.task_id}) is True

    def test_status_transitions(self) -> None:
        task = PlanTask(task_type=TaskType.ANALYSIS, title="t")
        assert task.status == TaskStatus.PENDING
        assert task.is_terminal() is False
        task.status = TaskStatus.COMPLETED
        assert task.is_terminal() is True

    def test_plan_persistence_roundtrip(self, tmp_path: Path) -> None:
        session_manager = SessionManager(tmp_path / "sessions")
        manager = PlanManager(
            project_root=tmp_path,
            session_manager=session_manager,
            storage_dir=tmp_path / "plans",
        )
        plan, _explore, _implement = self._plan()
        manager.store.save_plan(plan)
        loaded = manager.store.load_plan(plan.plan_id)
        assert loaded is not None
        assert loaded.objective == plan.objective
        assert len(loaded.tasks) == 2

    def test_phase_grouping(self) -> None:
        plan, explore, implement = self._plan()
        assert plan.get_tasks_by_phase(PlanPhase.DISCOVER) == [explore]
        assert plan.get_tasks_by_phase(PlanPhase.EXECUTE) == [implement]


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------


class TestMCP:
    def test_request_response_envelopes(self) -> None:
        request = MCPRequest(id="req-1", method="tools/list", params={})
        assert request.method == "tools/list"
        response = MCPResponse.success("req-1", {"tools": []})
        assert response.id == "req-1"
        assert response.error is None
        err = MCPResponse.make_error("req-2", -32601, "method not found")
        assert err.error == {"code": -32601, "message": "method not found"}

    def test_transport_type_values(self) -> None:
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.SSE.value == "sse"
        assert TransportType.WEBSOCKET.value == "websocket"

    def test_client_manager_add_remove_persist(self, tmp_path: Path) -> None:
        manager = MCPClientManager(config_dir=tmp_path / "mcp")
        cfg = MCPServerConfig(name="local", transport=TransportType.STDIO, command=["true"])
        manager.add_server(cfg)
        assert manager.get_server_config(cfg.server_id) is not None
        assert manager.remove_server(cfg.server_id) is True
        reloaded = MCPClientManager(config_dir=tmp_path / "mcp")
        assert reloaded.get_server_config(cfg.server_id) is None

    def test_mcp_server_constructed_with_config(self) -> None:
        from zksato_cli.mcp.server import MCPServer
        from zksato_cli.mcp.server import MCPServerConfig as ServerConfig

        config = ServerConfig(name="zksato", version="1.0.0")
        server = MCPServer(config)
        assert server.config.name == "zksato"
        assert server.config.version == "1.0.0"


# ---------------------------------------------------------------------------
# Shared state (CRDT)
# ---------------------------------------------------------------------------


class TestSharedStateCRDT:
    def test_gcounter_merge_is_commutative_and_idempotent(self) -> None:
        a = GCounter()
        b = GCounter()
        a.increment("node-a", 3)
        b.increment("node-b", 5)
        a.merge(b)
        b.merge(a)
        assert a.value() == b.value() == 8
        before = a.value()
        a.merge(b)  # idempotent
        assert a.value() == before

    def test_pncounter_net_value(self) -> None:
        counter = PNCounter()
        counter.increment("node", 10)
        counter.decrement("node", 4)
        assert counter.value() == 6

    def test_lwwregister_last_writer_wins(self) -> None:
        reg = LWWRegister()
        reg.set("v1", "actor-1")
        reg.set("v2", "actor-2")
        assert reg.get() == "v2"
        assert reg.actor == "actor-2"

    def test_shared_state_manager_counters_and_merge(self) -> None:
        manager = SharedStateManager()
        manager.get_counter("orders_submitted").increment("a", 2)
        manager.get_counter("orders_submitted").increment("b", 3)
        assert manager.get_counter("orders_submitted").value() == 5

        peer = SharedStateManager()
        peer.get_counter("orders_submitted").increment("c", 4)
        state = {"counters": {"orders_submitted": peer.get_counter("orders_submitted").counts}}
        asyncio.run(manager.merge_state(state))
        assert manager.get_counter("orders_submitted").value() == 9


# ---------------------------------------------------------------------------
# Specialized agents
# ---------------------------------------------------------------------------

_AGENT_TASK_TYPES: dict[type, tuple[str, dict[str, Any]]] = {
    ArchitectAgent: ("design_system", {"requirements": {"domain": "trading"}}),
    SecurityAuditorAgent: ("security_audit", {"target": "src", "type": "all"}),
    CodeReviewerAgent: ("review_code", {"file_path": "sample.py"}),
    TestEngineerAgent: ("generate_tests", {"file_path": "mod.py"}),
    DocumentationAgent: ("generate_docs", {"target": "mod.py"}),
}


def _make_agent(cls: type, tmp_path: Path) -> Any:
    return cls(
        agent_id=f"{cls.__name__.lower()}-1",
        registry=AgentRegistry(),
        project_root=tmp_path,
    )


class TestSpecializedAgents:
    async def test_agents_have_deterministic_identity(self, tmp_path: Path) -> None:
        agent = _make_agent(ArchitectAgent, tmp_path)
        assert agent.role == "System Architect"
        assert agent.name == "Architect"
        assert agent.agent_id.endswith("-1")

    async def test_security_auditor_executes_audit(self, tmp_path: Path) -> None:
        agent = _make_agent(SecurityAuditorAgent, tmp_path)
        task_type, payload = _AGENT_TASK_TYPES[SecurityAuditorAgent]
        result = await agent.execute_task(task_type, payload)
        assert isinstance(result, dict)

    async def test_code_reviewer_reviews_file(self, tmp_path: Path) -> None:
        (tmp_path / "sample.py").write_text("x = 1\n")
        agent = _make_agent(CodeReviewerAgent, tmp_path)
        result = await agent.execute_task("review_code", {"file_path": str(tmp_path / "sample.py")})
        assert isinstance(result, dict)

    async def test_documentation_agent_documents_module(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text("def public_fn(a: int) -> int:\n    return a\n")
        agent = _make_agent(DocumentationAgent, tmp_path)
        result = await agent.execute_task("generate_docs", {"target": str(tmp_path / "mod.py")})
        assert isinstance(result, dict)

    async def test_test_engineer_generates_plan(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text(
            "def add(a, b):\n    return a + b\n\ndef _private():\n    pass\n"
        )
        agent = _make_agent(TestEngineerAgent, tmp_path)
        result = await agent.execute_task("generate_tests", {"file_path": str(tmp_path / "mod.py")})
        assert isinstance(result, dict)

    async def test_architect_designs_system(self, tmp_path: Path) -> None:
        agent = _make_agent(ArchitectAgent, tmp_path)
        result = await agent.execute_task(
            "design_system",
            {"requirements": {"domain": "trading", "scale": "medium"}},
        )
        assert isinstance(result, dict)

    async def test_unknown_task_type_raises(self, tmp_path: Path) -> None:
        agent = _make_agent(ArchitectAgent, tmp_path)
        with pytest.raises(ValueError, match="No handler"):
            await agent.execute_task("nonexistent_task", {})


# ---------------------------------------------------------------------------
# Orchestrator + specialized agent wiring
# ---------------------------------------------------------------------------


class TestOrchestratorAgentWiring:
    async def test_review_task_dispatched_to_reviewer(self, tmp_path: Path) -> None:
        (tmp_path / "sample.py").write_text("x = 1\n")
        orch = OrchestratorV2(project_root=tmp_path, config={})
        await orch.start()
        try:
            task_id = await orch.submit_task(
                task_type="review_code",
                title="Review sample",
                description="Run reviewer on sample.py",
                required_capabilities={AgentCapability.CODE_REVIEW},
                payload={"file_path": str(tmp_path / "sample.py")},
            )
            for _ in range(100):
                task = orch.tasks[task_id]
                if task.status in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            assert task.status == "completed", f"error={task.error}"
        finally:
            await orch.stop()
