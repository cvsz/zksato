from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentSkillDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]] | Callable[..., dict[str, Any]]


class AgentSkillHub:
    """Native Python Skill Hub providing structured capabilities for agents."""

    def __init__(self) -> None:
        self._skills: dict[str, AgentSkillDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        handler: Callable[..., Awaitable[dict[str, Any]]] | Callable[..., dict[str, Any]],
    ) -> None:
        self._skills[name] = AgentSkillDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            handler=handler,
        )

    def get_skill(self, name: str) -> AgentSkillDefinition | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters_schema,
            }
            for s in self._skills.values()
        ]

    async def execute_skill(self, name: str, **kwargs: Any) -> dict[str, Any]:
        skill = self._skills.get(name)
        if skill is None:
            return {"success": False, "error": f"Skill '{name}' not found"}
        try:
            if inspect.iscoroutinefunction(skill.handler):
                result = await skill.handler(**kwargs)
            else:
                result = skill.handler(**kwargs)
            return {"success": True, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
