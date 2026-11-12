"""Agent engine for zksato automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from zksato_api.llm_clients import (  # type: ignore[import-untyped]
    HydrogenThinkingLevel,
)

from zksato_automation.agent_os.session import AgentSession
from zksato_automation.agent_os.skills import (
    CancelOrderSkill,
    CodeAnalysisSkill,
    CodeGenerationSkill,
    GetPositionsSkill,
    GetQuoteSkill,
    PlaceOrderSkill,
    SkillContext,
    SkillRegistry,
    SkillResult,
    TestVerificationSkill,
)
from zksato_automation.agent_os.subaccount import Quotas, SubAccount


@dataclass
class AgentEngine:
    """Main agent engine that coordinates skills, sessions, and sub-accounts.

    Integrates with Gemini 4 Hydrogen LLM client for agentic workflows.
    Supports multi-model orchestration via ModelOrchestrator.
    """

    skill_registry: SkillRegistry
    subaccounts: dict[str, SubAccount] = field(default_factory=dict)
    sessions: dict[str, AgentSession] = field(default_factory=dict)
    llm_client: Any = None
    orchestrator: Any = None

    def __post_init__(self) -> None:
        """Register built-in skills after initialization."""
        self._register_builtin_skills()

    def _register_builtin_skills(self) -> None:
        """Register built-in trading and LLM skills."""
        # Trading skills (always available)
        self.skill_registry.register(GetQuoteSkill())
        self.skill_registry.register(PlaceOrderSkill())
        self.skill_registry.register(GetPositionsSkill())
        self.skill_registry.register(CancelOrderSkill())

        # LLM-powered skills (require LLM client)
        if self.llm_client is not None:
            self.skill_registry.register(CodeGenerationSkill(llm_client=self.llm_client))
            self.skill_registry.register(CodeAnalysisSkill(llm_client=self.llm_client))
            self.skill_registry.register(TestVerificationSkill(llm_client=self.llm_client))

    def register_llm_skill(
        self,
        skill_name: str,
        llm_client: Any,  # noqa: ANN401
    ) -> None:
        """Register an LLM-powered skill dynamically.

        Args:
            skill_name: Name of the skill (generate_code, analyze_code, verify_test).
            llm_client: Gemini 4 Hydrogen client instance.
        """
        if skill_name == "generate_code":
            self.skill_registry.register(CodeGenerationSkill(llm_client=llm_client))
        elif skill_name == "analyze_code":
            self.skill_registry.register(CodeAnalysisSkill(llm_client=llm_client))
        elif skill_name == "verify_test":
            self.skill_registry.register(TestVerificationSkill(llm_client=llm_client))
        else:
            raise ValueError(f"Unknown LLM skill: {skill_name}")

    def create_subaccount(
        self,
        account_id: str,
        parent_id: str,
        quotas: Any = None,  # noqa: ANN401
    ) -> SubAccount:
        """Create a new sub-account."""
        subaccount = SubAccount(
            account_id=account_id,
            parent_id=parent_id,
            quotas=quotas or Quotas(),
        )
        self.subaccounts[account_id] = subaccount
        return subaccount

    def get_subaccount(self, account_id: str) -> SubAccount | None:
        """Get a sub-account by ID."""
        return self.subaccounts.get(account_id)

    def create_session(self, session_id: str, subaccount_id: str) -> AgentSession:
        """Create a new agent session."""
        session = AgentSession(session_id=UUID(session_id), subaccount_id=subaccount_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> AgentSession | None:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    async def execute_skill(
        self,
        session_id: str,
        skill_name: str,
        params: dict[str, Any],
    ) -> SkillResult:
        """Execute a skill within a session."""
        session = self.sessions.get(session_id)
        if not session:
            return SkillResult(success=False, error="Session not found")

        subaccount = self.subaccounts.get(session.subaccount_id)
        if not subaccount:
            return SkillResult(success=False, error="Sub-account not found")

        skill = self.skill_registry.get(skill_name)
        if not skill:
            return SkillResult(success=False, error=f"Skill not found: {skill_name}")

        ctx = SkillContext(
            account_id=subaccount.account_id,
            subaccount_id=subaccount.account_id,
        )

        return await skill.execute(params, ctx)

    async def llm_reason(
        self,
        prompt: str,
        task_type: str = "general",
        thinking_level: str = "high",
        use_orchestrator: bool = True,
    ) -> dict[str, Any]:
        """Perform LLM-based reasoning using Gemini 4 Hydrogen.

        Routes through the orchestrator if available, which dynamically
        selects between Carbon (reasoning) and Hydrogen (execution) based
        on task complexity.

        Args:
            prompt: The reasoning prompt.
            task_type: Type of task for routing (code_generation, test_verification,
                       code_analysis, architecture, debugging, general).
            thinking_level: Hydrogen thinking level (low, medium, high, xhigh).
            use_orchestrator: Whether to use the model orchestrator.

        Returns:
            Dict with reasoning result, model used, and metadata.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a trading and risk analysis assistant. "
                    "Provide accurate, well-reasoned responses for financial "
                    "and trading-related queries."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        if use_orchestrator and self.orchestrator is not None:
            try:
                level = HydrogenThinkingLevel(thinking_level)
            except ValueError:
                level = HydrogenThinkingLevel.HIGH

            result = await self.orchestrator.execute(
                messages=messages,
                task_type=task_type,
                thinking_level=level,
            )
            return {
                "content": result.response.content,
                "model_used": result.model_used.value,
                "decision_reasoning": result.decision.reasoning,
                "fallback_used": result.fallback_used,
                "input_tokens": result.response.input_tokens,
                "output_tokens": result.response.output_tokens,
                "latency_seconds": result.response.latency_seconds,
            }

        if self.llm_client is not None:
            try:
                level = HydrogenThinkingLevel(thinking_level)
            except ValueError:
                level = HydrogenThinkingLevel.HIGH

            response = await self.llm_client.generate(
                messages=messages,
                thinking_level=level,
            )
            return {
                "content": response.content,
                "model_used": response.model,
                "decision_reasoning": "Direct Hydrogen call",
                "fallback_used": False,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_seconds": response.latency_seconds,
            }

        return {
            "content": "LLM client not configured. Set GEMINI_API_KEY.",
            "model_used": "none",
            "decision_reasoning": "No LLM client available",
            "fallback_used": False,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_seconds": 0.0,
        }

    def list_available_skills(self) -> list[dict[str, str]]:
        """List all registered skills."""
        return self.skill_registry.list_skills()
