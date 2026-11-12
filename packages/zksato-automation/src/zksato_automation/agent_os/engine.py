"""Agent engine for zksato automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from zksato_automation.agent_os.skills import SkillRegistry, SkillContext, SkillResult
from zksato_automation.agent_os.subaccount import SubAccount
from zksato_automation.agent_os.session import AgentSession


@dataclass
class AgentEngine:
    """Main agent engine that coordinates skills, sessions, and sub-accounts."""
    
    skill_registry: SkillRegistry
    subaccounts: dict[str, SubAccount] = field(default_factory=dict)
    sessions: dict[str, AgentSession] = field(default_factory=dict)
    
    def create_subaccount(
        self,
        account_id: str,
        parent_id: str,
        quotas: Any = None,
    ) -> SubAccount:
        """Create a new sub-account."""
        from zksato_automation.agent_os.subaccount import Quotas
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
        session = AgentSession(session_id=session_id, subaccount_id=subaccount_id)
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