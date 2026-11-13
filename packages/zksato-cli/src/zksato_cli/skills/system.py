"""Skill system for ZKSATO coding agent.

Provides reusable, versioned skills with:
- Skill manifests
- Skill validation
- Skill dependencies
- Skill versioning
- Project-level and user-level scopes
- Skill execution audit
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from zksato_cli.hooks.framework import HookEvent, HookManager

logger = logging.getLogger(__name__)


class SkillScope(str, Enum):
    """Skill scope."""

    USER = "user"
    PROJECT = "project"
    BUILTIN = "builtin"


class SkillStatus(str, Enum):
    """Skill status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ERROR = "error"


@dataclass
class SkillParameter:
    """Skill parameter definition."""

    name: str
    type: str  # string, integer, boolean, array, object
    description: str = ""
    required: bool = True
    default: Any = None
    enum: list[Any] | None = None
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None


@dataclass
class SkillDependency:
    """Skill dependency."""

    skill_id: str
    version: str | None = None  # None = any version
    required: bool = True


@dataclass
class SkillManifest:
    """Skill manifest - describes a skill's capabilities and requirements."""

    skill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"

    # Scope
    scope: SkillScope = SkillScope.PROJECT

    # Capabilities
    provides: list[str] = field(default_factory=list)  # Capabilities this skill provides
    requires: list[str] = field(default_factory=list)  # Capabilities this skill needs

    # Parameters
    parameters: list[SkillParameter] = field(default_factory=list)

    # Dependencies
    dependencies: list[SkillDependency] = field(default_factory=list)

    # Entry point
    entry_point: str = ""  # Module:function or command

    # Configuration
    config_schema: dict[str, Any] = field(default_factory=dict)
    default_config: dict[str, Any] = field(default_factory=dict)

    # Metadata
    tags: set[str] = field(default_factory=set)
    homepage: str = ""
    repository: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize manifest to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "scope": self.scope.value,
            "provides": self.provides,
            "requires": self.requires,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                    "minimum": p.minimum,
                    "maximum": p.maximum,
                    "pattern": p.pattern,
                }
                for p in self.parameters
            ],
            "dependencies": [
                {
                    "skill_id": d.skill_id,
                    "version": d.version,
                    "required": d.required,
                }
                for d in self.dependencies
            ],
            "entry_point": self.entry_point,
            "config_schema": self.config_schema,
            "default_config": self.default_config,
            "tags": list(self.tags),
            "homepage": self.homepage,
            "repository": self.repository,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillManifest:
        """Deserialize manifest from dictionary."""
        manifest = cls(
            skill_id=data["skill_id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            scope=SkillScope(data.get("scope", "project")),
            provides=data.get("provides", []),
            requires=data.get("requires", []),
            entry_point=data.get("entry_point", ""),
            config_schema=data.get("config_schema", {}),
            default_config=data.get("default_config", {}),
            tags=set(data.get("tags", [])),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
        )

        for p_data in data.get("parameters", []):
            manifest.parameters.append(
                SkillParameter(
                    name=p_data["name"],
                    type=p_data["type"],
                    description=p_data.get("description", ""),
                    required=p_data.get("required", True),
                    default=p_data.get("default"),
                    enum=p_data.get("enum"),
                    minimum=p_data.get("minimum"),
                    maximum=p_data.get("maximum"),
                    pattern=p_data.get("pattern"),
                )
            )

        for d_data in data.get("dependencies", []):
            manifest.dependencies.append(
                SkillDependency(
                    skill_id=d_data["skill_id"],
                    version=d_data.get("version"),
                    required=d_data.get("required", True),
                )
            )

        if data.get("created_at"):
            manifest.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            manifest.updated_at = datetime.fromisoformat(data["updated_at"])

        return manifest


@dataclass
class SkillInstance:
    """An instantiated skill with configuration."""

    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    manifest: SkillManifest | None = None
    manifest_id: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    status: SkillStatus = SkillStatus.INACTIVE
    scope: SkillScope = SkillScope.PROJECT
    project_path: Path = field(default_factory=Path)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used: datetime | None = None
    use_count: int = 0

    def validate_config(self) -> list[str]:
        """Validate configuration against schema."""
        errors = []
        # Simple validation - in production use jsonschema
        for param in self.manifest.parameters if self.manifest else []:
            # Only validate parameters that are in the instance config
            # Required parameters should be provided at execution time
            if param.name in self.config:
                value = self.config[param.name]
                if param.type == "integer" and not isinstance(value, int):
                    errors.append(f"Parameter {param.name} must be integer")
                elif param.type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Parameter {param.name} must be boolean")
                elif param.type == "array" and not isinstance(value, list):
                    errors.append(f"Parameter {param.name} must be array")
                if param.enum and value not in param.enum:
                    errors.append(f"Parameter {param.name} must be one of {param.enum}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "manifest_id": self.manifest_id,
            "config": self.config,
            "status": self.status.value,
            "scope": self.scope.value,
            "project_path": str(self.project_path),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], manifest: SkillManifest) -> SkillInstance:
        instance = cls(
            instance_id=data["instance_id"],
            manifest=manifest,
            manifest_id=data["manifest_id"],
            config=data.get("config", {}),
            status=SkillStatus(data.get("status", "inactive")),
            scope=SkillScope(data.get("scope", "project")),
            project_path=Path(data.get("project_path", ".")),
            use_count=data.get("use_count", 0),
        )
        if data.get("created_at"):
            instance.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            instance.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_used"):
            instance.last_used = datetime.fromisoformat(data["last_used"])
        return instance


@dataclass
class SkillExecution:
    """Record of a skill execution."""

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instance_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    success: bool = False
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class SkillValidator:
    """Validates skill manifests and configurations."""

    @staticmethod
    def validate_manifest(manifest: SkillManifest) -> list[str]:
        """Validate a skill manifest."""
        errors = []

        if not manifest.name:
            errors.append("Skill name is required")
        if not manifest.version:
            errors.append("Skill version is required")
        if not manifest.description:
            errors.append("Skill description is required")
        if not manifest.entry_point:
            errors.append("Entry point is required")

        # Validate version format (semver)
        try:
            parts = manifest.version.split(".")
            if len(parts) != 3:
                errors.append("Version must be semver (major.minor.patch)")
            else:
                for part in parts:
                    int(part)
        except ValueError:
            errors.append("Version must be numeric semver")

        # Validate parameters
        param_names = set()
        for param in manifest.parameters:
            if param.name in param_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)

        # Validate dependencies
        errors.extend(
            "Dependency skill_id is required" for dep in manifest.dependencies if not dep.skill_id
        )

        return errors

    @staticmethod
    def validate_config(manifest: SkillManifest, config: dict[str, Any]) -> list[str]:
        """Validate skill configuration."""
        errors = []

        for param in manifest.parameters:
            if param.required and param.name not in config:
                errors.append(f"Missing required parameter: {param.name}")

            if param.name in config:
                value = config[param.name]
                if param.type == "integer" and not isinstance(value, int):
                    errors.append(f"Parameter {param.name} must be integer")
                elif param.type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Parameter {param.name} must be boolean")
                elif param.type == "array" and not isinstance(value, list):
                    errors.append(f"Parameter {param.name} must be array")
                elif param.type == "object" and not isinstance(value, dict):
                    errors.append(f"Parameter {param.name} must be object")
                if param.enum and value not in param.enum:
                    errors.append(f"Parameter {param.name} must be one of {param.enum}")
                if (
                    param.minimum is not None
                    and isinstance(value, (int, float))
                    and value < param.minimum
                ):
                    errors.append(f"Parameter {param.name} must be >= {param.minimum}")
                if (
                    param.maximum is not None
                    and isinstance(value, (int, float))
                    and value > param.maximum
                ):
                    errors.append(f"Parameter {param.name} must be <= {param.maximum}")
                if param.pattern and isinstance(value, str):
                    import re

                    if not re.match(param.pattern, value):
                        errors.append(f"Parameter {param.name} does not match pattern")

        return errors


class SkillRegistry:
    """Registry for managing skills."""

    def __init__(self, storage_dir: Path | str = ".zksato/skills") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._manifests: dict[str, SkillManifest] = {}
        self._instances: dict[str, SkillInstance] = {}
        self._index_file = self.storage_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        index_file = self.storage_dir / "index.json"
        if index_file.exists():
            try:
                with index_file.open("r") as f:
                    data = json.load(f)
                    for m_data in data.get("manifests", []):
                        manifest = SkillManifest.from_dict(m_data)
                        self._manifests[manifest.skill_id] = manifest
                    for i_data in data.get("instances", []):
                        manifest = self._manifests.get(i_data["manifest_id"])
                        if manifest:
                            instance = SkillInstance.from_dict(i_data, manifest)
                            self._instances[instance.instance_id] = instance
            except Exception as exc:
                logger.warning("Failed to load skill index: %s", exc)

    def _save_index(self) -> None:
        index_file = self.storage_dir / "index.json"
        try:
            data = {
                "manifests": [m.to_dict() for m in self._manifests.values()],
                "instances": [i.to_dict() for i in self._instances.values()],
            }
            with index_file.open("w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to save skill index: %s", exc)

    def register_manifest(self, manifest: SkillManifest) -> bool:
        """Register a skill manifest."""
        errors = SkillValidator.validate_manifest(manifest)
        if errors:
            logger.error("Manifest validation failed: %s", errors)
            return False

        self._manifests[manifest.skill_id] = manifest
        self._save_index()
        logger.info("Registered skill manifest: %s v%s", manifest.name, manifest.version)
        return True

    def unregister_manifest(self, skill_id: str) -> bool:
        if skill_id in self._manifests:
            del self._manifests[skill_id]
            self._save_index()
            return True
        return False

    def get_manifest(self, skill_id: str) -> SkillManifest | None:
        return self._manifests.get(skill_id)

    def list_manifests(self, scope: SkillScope | None = None) -> list[SkillManifest]:
        manifests = list(self._manifests.values())
        if scope:
            manifests = [m for m in manifests if m.scope == scope]
        return manifests

    def create_instance(
        self,
        manifest_id: str,
        config: dict[str, Any] | None = None,
        scope: SkillScope = SkillScope.PROJECT,
        project_path: Path | None = None,
    ) -> SkillInstance | None:
        """Create a skill instance."""
        manifest = self._manifests.get(manifest_id)
        if not manifest:
            logger.error("Manifest not found: %s", manifest_id)
            return None

        # Validate instance config (optional/default params only, not required execution params)
        # Create a temporary instance to validate config
        temp_instance = SkillInstance(
            manifest=manifest, manifest_id=manifest_id, config=config or {}
        )
        errors = temp_instance.validate_config()
        if errors:
            logger.error("Config validation failed: %s", errors)
            return None

        # Merge user config with manifest defaults
        merged_config = {**manifest.default_config, **(config or {})}

        instance = SkillInstance(
            manifest=manifest,
            manifest_id=manifest_id,
            config=merged_config,
            scope=scope,
            project_path=project_path or Path(),
            status=SkillStatus.ACTIVE,
        )

        self._instances[instance.instance_id] = instance
        self._save_index()
        return instance

    def get_instance(self, instance_id: str) -> SkillInstance | None:
        return self._instances.get(instance_id)

    def list_instances(
        self, scope: SkillScope | None = None, status: SkillStatus | None = None
    ) -> list[SkillInstance]:
        instances = list(self._instances.values())
        if scope:
            instances = [i for i in instances if i.scope == scope]
        if status:
            instances = [i for i in instances if i.status == status]
        return instances


class SkillExecutor:
    """Executes skills with hooks and audit logging."""

    def __init__(
        self,
        registry: SkillRegistry,
        hook_manager: HookManager | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.registry = registry
        self.hook_manager = hook_manager
        self.project_root = Path(project_root) if project_root else Path()

    async def execute(
        self,
        instance_id: str,
        parameters: dict[str, Any],
        session_id: str | None = None,
    ) -> SkillExecution:
        """Execute a skill."""
        instance = self.registry.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.status != SkillStatus.ACTIVE:
            raise ValueError(f"Instance not active: {instance.status.value}")

        execution = SkillExecution(
            instance_id=instance_id,
            parameters=parameters,
        )

        datetime.now(UTC)

        # Emit before hook
        if self.hook_manager:
            await self.hook_manager.emit_simple(
                HookEvent.BEFORE_TOOL,
                session_id=session_id,
                data={
                    "skill_instance_id": instance_id,
                    "skill_name": instance.manifest.name if instance.manifest else "unknown",
                    "parameters": parameters,
                },
            )

        try:
            # Merge parameters with instance config
            merged_params = {**instance.config, **parameters}

            # Validate parameters
            if instance.manifest:
                errors = SkillValidator.validate_config(instance.manifest, merged_params)
                if errors:
                    raise ValueError(f"Parameter validation failed: {errors}")

            # Execute skill
            output = await self._execute_skill(instance, merged_params)

            execution.success = True
            execution.output = output

        except Exception as exc:
            execution.error = str(exc)
            logger.error("Skill execution failed: %s", exc)

        finally:
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = (
                datetime.now(UTC) - execution.started_at
            ).total_seconds() * 1000

            # Update instance stats
            instance.last_used = datetime.now(UTC)
            instance.use_count += 1
            instance.updated_at = datetime.now(UTC)

            # Emit after hook
            if self.hook_manager:
                await self.hook_manager.emit_simple(
                    HookEvent.AFTER_TOOL,
                    session_id=session_id,
                    data={
                        "skill_instance_id": execution.instance_id,
                        "success": execution.success,
                        "error": execution.error,
                    },
                )

        return execution

    async def _execute_skill(self, instance: SkillInstance, parameters: dict[str, Any]) -> Any:
        """Execute the actual skill logic."""
        if not instance.manifest or not instance.manifest.entry_point:
            raise ValueError("No entry point defined for skill")

        # For now, support command-based entry points
        entry = instance.manifest.entry_point

        if entry.startswith("cmd:"):
            # Command execution
            cmd = entry[4:].format(**parameters)
            import shlex
            import subprocess

            cmd_list = shlex.split(cmd)
            proc = subprocess.run(
                cmd_list,
                shell=False,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=parameters.get("timeout", 60),
            )
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }

        elif entry.startswith("py:"):
            # Python function
            module_path, func_name = entry[3:].split(":", 1)
            import importlib

            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            if asyncio.iscoroutinefunction(func):
                return await func(**parameters)
            else:
                return func(**parameters)

        else:
            raise ValueError(f"Unsupported entry point format: {entry}")


class SkillManager:
    """High-level skill management."""

    def __init__(
        self,
        project_root: Path,
        storage_dir: Path | str = ".zksato/skills",
        hook_manager: HookManager | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.registry = SkillRegistry(storage_dir)
        self.executor = SkillExecutor(self.registry, project_root=self.project_root)
        self.hook_manager = hook_manager

    def load_skill_from_file(self, file_path: Path) -> SkillManifest | None:
        """Load a skill manifest from a file."""
        try:
            with file_path.open("r") as f:
                if file_path.suffix == ".json":
                    data = json.load(f)
                elif file_path.suffix in (".yaml", ".yml"):
                    import yaml

                    data = yaml.safe_load(f)
                else:
                    logger.error("Unsupported file format: %s", file_path.suffix)
                    return None

            manifest = SkillManifest.from_dict(data)
            return manifest
        except Exception as exc:
            logger.error("Failed to load skill from %s: %s", file_path, exc)
            return None

    def install_skill(
        self,
        file_path: Path,
        scope: SkillScope = SkillScope.PROJECT,
    ) -> bool:
        """Install a skill from a manifest file."""
        manifest = self.load_skill_from_file(file_path)
        if not manifest:
            return False

        manifest.scope = scope
        return self.registry.register_manifest(manifest)

    def uninstall_skill(self, skill_id: str) -> bool:
        return self.registry.unregister_manifest(skill_id)

    def list_skills(self, scope: SkillScope | None = None) -> list[SkillManifest]:
        return self.registry.list_manifests(scope)

    def get_skill(self, skill_id: str) -> SkillManifest | None:
        return self.registry.get_manifest(skill_id)

    def create_instance(
        self,
        skill_id: str,
        config: dict[str, Any] | None = None,
        scope: SkillScope = SkillScope.PROJECT,
    ) -> SkillInstance | None:
        return self.registry.create_instance(
            skill_id, config, SkillScope.PROJECT, self.project_root
        )

    def get_instance(self, instance_id: str) -> SkillInstance | None:
        return self.registry.get_instance(instance_id)

    def list_instances(self, scope: SkillScope | None = None) -> list[SkillInstance]:
        return self.registry.list_instances(scope)

    async def execute(
        self,
        instance_id: str,
        parameters: dict[str, Any],
        session_id: str | None = None,
    ) -> SkillExecution:
        return await self.executor.execute(instance_id, parameters, session_id)

    def validate_manifest(self, manifest: SkillManifest) -> list[str]:
        return SkillValidator.validate_manifest(manifest)

    def validate_config(self, skill_id: str, config: dict[str, Any]) -> list[str]:
        manifest = self.registry.get_manifest(skill_id)
        if not manifest:
            return ["Manifest not found"]
        return SkillValidator.validate_config(manifest, config)


# Built-in skills
BUILTIN_SKILLS = [
    SkillManifest(
        skill_id="builtin.grep",
        name="Grep Search",
        version="1.0.0",
        description="Search code using ripgrep",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["search", "grep"],
        entry_point="cmd:rg {pattern} {path}",
        parameters=[
            SkillParameter(
                name="pattern", type="string", description="Search pattern", required=True
            ),
            SkillParameter(
                name="path",
                type="string",
                description="Path to search",
                required=False,
                default=".",
            ),
            SkillParameter(
                name="glob", type="string", description="File glob pattern", required=False
            ),
        ],
        default_config={"path": "."},
        tags={"search", "builtin"},
    ),
    SkillManifest(
        skill_id="builtin.read_file",
        name="Read File",
        version="1.0.0",
        description="Read a file with syntax highlighting",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["file_read"],
        entry_point="py:zksato_cli.editing.search:read_file_tool",
        parameters=[
            SkillParameter(name="path", type="string", description="File path", required=True),
            SkillParameter(name="start", type="integer", description="Start line", required=False),
            SkillParameter(name="end", type="integer", description="End line", required=False),
        ],
        tags={"file", "builtin"},
    ),
    SkillManifest(
        skill_id="builtin.write_file",
        name="Write File",
        version="1.0.0",
        description="Write content to a file",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["file_write"],
        entry_point="py:zksato_cli.editing.search:write_file_tool",
        parameters=[
            SkillParameter(name="path", type="string", description="File path", required=True),
            SkillParameter(
                name="content", type="string", description="Content to write", required=True
            ),
        ],
        tags={"file", "builtin"},
    ),
    SkillManifest(
        skill_id="builtin.run_command",
        name="Run Command",
        version="1.0.0",
        description="Execute a shell command",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["command"],
        entry_point="cmd:{command}",
        parameters=[
            SkillParameter(
                name="command", type="string", description="Command to run", required=True
            ),
            SkillParameter(
                name="cwd",
                type="string",
                description="Working directory",
                required=False,
                default=".",
            ),
            SkillParameter(
                name="timeout",
                type="integer",
                description="Timeout in seconds",
                required=False,
                default=60,
            ),
        ],
        tags={"shell", "builtin"},
    ),
    SkillManifest(
        skill_id="builtin.run_tests",
        name="Run Tests",
        version="1.0.0",
        description="Run test suite",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["test"],
        entry_point="cmd:python -m pytest {args}",
        parameters=[
            SkillParameter(
                name="args",
                type="string",
                description="Pytest arguments",
                required=False,
                default="",
            ),
            SkillParameter(
                name="timeout",
                type="integer",
                description="Timeout in seconds",
                required=False,
                default=120,
            ),
        ],
        tags={"test", "builtin"},
    ),
    SkillManifest(
        skill_id="builtin.lint",
        name="Lint Code",
        version="1.0.0",
        description="Run linter",
        author="ZKSATO",
        scope=SkillScope.BUILTIN,
        provides=["lint"],
        entry_point="cmd:ruff check {args}",
        parameters=[
            SkillParameter(
                name="args",
                type="string",
                description="Ruff arguments",
                required=False,
                default=".",
            ),
        ],
        tags={"lint", "builtin"},
    ),
]


def register_builtin_skills(registry: SkillRegistry) -> None:
    """Register built-in skills."""
    for skill in BUILTIN_SKILLS:
        registry.register_manifest(skill)
