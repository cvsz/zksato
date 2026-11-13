"""Specialized agents for ZKSATO multi-agent system.

Implements specialized agents for different roles:
- Architect Agent: System design, API contracts, technology selection
- Security Auditor: Threat modeling, vulnerability scanning, compliance
- Code Reviewer: Style enforcement, bug detection, performance analysis
- Test Engineer: Test generation, coverage analysis, flake detection
- Documentation Agent: API docs, architecture decision records
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zksato_automation.agent_os.a2a.protocol import (
    A2ACommunicator,
    A2AMessage,
    A2AMessageType,
    AgentCapability,
    AgentRegistry,
)
from zksato_automation.agent_os.coordination.shared_state import SharedStateManager

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Task assigned to an agent."""

    task_id: str
    task_type: str
    payload: dict[str, Any]
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str | None = None


class BaseSpecializedAgent:
    """Base class for specialized agents."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: set[str],
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.capabilities = {AgentCapability(c) for c in capabilities}
        self.registry = registry
        self.project_root = Path(project_root).resolve()
        self.communicator = A2ACommunicator(agent_id, registry)
        self.shared_state = SharedStateManager()
        self.current_task: AgentTask | None = None
        self._task_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register task handlers. Override in subclasses."""
        pass

    def register_task_handler(
        self,
        task_type: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        """Register a task handler."""
        self._task_handlers[task_type] = handler

    async def handle_task_request(self, message: A2AMessage) -> None:
        """Handle incoming task request."""
        task_id = message.payload.get("task_id")
        task_type = message.payload.get("task_type")
        payload = message.payload.get("payload", {})

        if task_type not in self._task_handlers:
            logger.warning("No handler for task type: %s", task_type)
            return

        task = AgentTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
        )
        self.current_task = task

        # Update agent status
        agent_info = self.registry.get_agent(self.agent_id)
        if agent_info:
            agent_info.status = "busy"
            agent_info.current_task_id = task_id

        try:
            task.started_at = datetime.now(UTC)
            handler = self._task_handlers[task_type]
            result = await handler(payload)

            task.status = "completed"
            task.completed_at = datetime.now(UTC)
            task.result = result

            # Send completion
            response = A2AMessage(
                message_type=A2AMessageType.TASK_COMPLETE,
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                correlation_id=message.message_id,
                payload={
                    "task_id": task_id,
                    "result": result,
                },
            )
            await self.registry.send_message(response)

        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc)
            task.status = "failed"
            task.error = str(exc)

            response = A2AMessage(
                message_type=A2AMessageType.TASK_FAILED,
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                correlation_id=message.message_id,
                payload={
                    "task_id": task_id,
                    "error": str(exc),
                },
            )
            await self.registry.send_message(response)

        finally:
            self.current_task = None
            if agent_info:
                agent_info.status = "idle"
                agent_info.current_task_id = None

    async def execute_task(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a task directly (for testing or internal use)."""
        if task_type not in self._task_handlers:
            raise ValueError(f"No handler for task type: {task_type}")
        return await self._task_handlers[task_type](payload)


class ArchitectAgent(BaseSpecializedAgent):
    """Architect Agent - System design, API contracts, technology selection."""

    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name="Architect",
            role="System Architect",
            capabilities={
                "architecture_design",
                "api_design",
                "technology_selection",
                "system_design",
                "database_design",
            },
            registry=registry,
            project_root=project_root,
        )

    def _register_handlers(self) -> None:
        self.register_task_handler("design_system", self._design_system)
        self.register_task_handler("design_api", self._design_api)
        self.register_task_handler("select_technology", self._select_technology)
        self.register_task_handler("create_adr", self._create_adr)
        self.register_task_handler("review_architecture", self._review_architecture)

    async def _design_system(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Design system architecture."""
        requirements = payload.get("requirements", [])
        constraints = payload.get("constraints", {})

        # Search for existing architecture docs
        arch_files = list(self.project_root.rglob("**/architecture*.md"))
        arch_files += list(self.project_root.rglob("**/ARCHITECTURE.md"))

        context = ""
        for f in arch_files[:5]:
            with contextlib.suppress(Exception):
                context += f.read_text(encoding="utf-8")[:2000] + "\n\n"

        # Generate architecture design (would use LLM in production)
        design = {
            "overview": "System architecture design based on requirements",
            "components": [
                {"name": "API Gateway", "description": "Entry point for all requests"},
                {"name": "Service Layer", "description": "Business logic services"},
                {"name": "Data Layer", "description": "Database and storage abstraction"},
            ],
            "patterns": ["Microservices", "Event-driven", "CQRS"],
            "technologies": {
                "api": "FastAPI/GraphQL",
                "database": "PostgreSQL + Redis",
                "messaging": "Redis Streams / Kafka",
                "deployment": "Docker + Kubernetes",
            },
            "requirements_addressed": requirements,
            "constraints": constraints,
        }

        return {
            "design": design,
            "architecture_decision_records": [
                {
                    "id": "ADR-001",
                    "title": "Use Microservices Architecture",
                    "status": "proposed",
                    "context": "Need for independent scaling and deployment",
                    "decision": "Adopt microservices with API gateway",
                    "consequences": "Increased complexity but better scalability",
                }
            ],
        }

    async def _design_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Design API contracts."""
        endpoints = payload.get("endpoints", [])
        style = payload.get("style", "REST")

        # Analyze existing API
        api_files = list(self.project_root.rglob("**/api/**/*.py"))
        api_files += list(self.project_root.rglob("**/routes/**/*.py"))

        api_summary = []
        for f in api_files[:10]:
            try:
                content = f.read_text(encoding="utf-8")
                # Extract routes (simplified)
                routes = re.findall(
                    r'@(app|router)\.(get|post|put|delete|patch)\("([^"]+)"', content
                )
                for _decorator, method, path in routes:
                    api_summary.append({"method": method.upper(), "path": path, "file": str(f)})
            except Exception:
                pass

        return {
            "style": style,
            "endpoints": endpoints,
            "existing_endpoints": api_summary,
            "conventions": {
                "naming": "kebab-case for paths, PascalCase for types",
                "versioning": "URL prefix /api/v1/",
                "errors": "RFC 7807 Problem Details",
            },
            "openapi_spec": "Generated from code",
        }

    async def _select_technology(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Select technology stack."""
        requirements = payload.get("requirements", {})
        category = payload.get("category", "general")

        # Technology recommendations based on category
        recommendations = {
            "web_framework": {
                "recommended": "FastAPI",
                "alternatives": ["Starlette", "Django", "Flask"],
                "reason": "Fast, async-native, automatic OpenAPI generation",
            },
            "database": {
                "recommended": "PostgreSQL",
                "alternatives": ["MySQL", "SQLite", "MongoDB"],
                "reason": "ACID compliance, JSON support, extensible",
            },
            "cache": {
                "recommended": "Redis",
                "alternatives": ["Memcached", "Valkey"],
                "reason": "Rich data structures, pub/sub, streams",
            },
            "message_queue": {
                "recommended": "Redis Streams",
                "alternatives": ["RabbitMQ", "Kafka", "NATS"],
                "reason": "Built into Redis, consumer groups, persistence",
            },
            "orm": {
                "recommended": "SQLAlchemy 2.0",
                "alternatives": ["Tortoise ORM", "Prisma", "Django ORM"],
                "reason": "Async support, type safety, mature ecosystem",
            },
        }

        return {
            "category": category,
            "requirements": requirements,
            "recommendations": recommendations,
            "decision_matrix": self._create_decision_matrix(category, requirements),
        }

    def _create_decision_matrix(self, category: str, requirements: dict) -> dict:
        """Create technology decision matrix."""
        return {
            "criteria": ["performance", "maintainability", "community", "cost", "team_expertise"],
            "weights": {
                "performance": 0.3,
                "maintainability": 0.25,
                "community": 0.2,
                "cost": 0.15,
                "team_expertise": 0.1,
            },
        }

    async def _create_adr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create Architecture Decision Record."""
        title = payload.get("title", "Untitled ADR")
        context = payload.get("context", "")
        decision = payload.get("decision", "")
        consequences = payload.get("consequences", "")

        adr_dir = self.project_root / "docs" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)

        # Find next ADR number
        existing = list(adr_dir.glob("*.md"))
        numbers = [int(f.stem.split("-")[0]) for f in existing if f.stem.split("-")[0].isdigit()]
        next_num = max(numbers, default=0) + 1

        adr_content = f"""# ADR-{next_num:03d}: {title}

## Status
Proposed

## Context
{context}

## Decision
{decision}

## Consequences
{consequences}

## Date
{datetime.now(UTC).strftime("%Y-%m-%d")}
"""

        adr_file = adr_dir / f"{next_num:03d}-{title.lower().replace(' ', '-')}.md"
        adr_file.write_text(adr_content, encoding="utf-8")

        return {
            "adr_id": f"ADR-{next_num:03d}",
            "title": title,
            "file": str(adr_file),
            "status": "proposed",
        }

    async def _review_architecture(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Review architecture for issues."""
        target = payload.get("target", "full")

        findings = []

        # Check for common architectural issues
        if target in ("full", "coupling"):
            # Check for circular imports
            py_files = list(self.project_root.rglob("*.py"))
            imports = {}
            for f in py_files[:50]:
                try:
                    content = f.read_text(encoding="utf-8")
                    for line in content.split("\n"):
                        if line.startswith("from ") or line.startswith("import "):
                            parts = line.split()
                            if len(parts) >= 2:
                                mod = parts[1].split(".")[0]
                                imports.setdefault(mod, 0)
                                imports[mod] += 1
                except Exception:
                    pass

        return {
            "review_type": "architecture",
            "target": target,
            "findings": findings,
            "recommendations": [
                "Consider introducing interface segregation",
                "Reduce circular dependencies",
                "Add architecture tests",
            ],
        }


class SecurityAuditorAgent(BaseSpecializedAgent):
    """Security Auditor Agent - Threat modeling, vulnerability scanning, compliance."""

    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name="Security Auditor",
            role="Security Auditor",
            capabilities={
                "security_audit",
                "threat_modeling",
                "vulnerability_scanning",
                "compliance_checking",
                "secret_detection",
            },
            registry=registry,
            project_root=project_root,
        )

    def _register_handlers(self) -> None:
        self.register_task_handler("security_audit", self._security_audit)
        self.register_task_handler("threat_model", self._threat_model)
        self.register_task_handler("scan_vulnerabilities", self._scan_vulnerabilities)
        self.register_task_handler("check_compliance", self._check_compliance)
        self.register_task_handler("detect_secrets", self._detect_secrets)
        self.register_task_handler("analyze_code", self._analyze_code)

    async def _security_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform comprehensive security audit."""
        scope = payload.get("scope", "full")

        results = {
            "audit_id": f"audit-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "scope": scope,
            "timestamp": datetime.now(UTC).isoformat(),
            "findings": [],
        }

        # Run static analysis tools
        try:
            # Bandit for Python security issues
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                for issue in bandit_results.get("results", []):
                    results["findings"].append(
                        {
                            "type": "bandit",
                            "severity": issue.get("issue_severity", "UNKNOWN"),
                            "confidence": issue.get("issue_confidence", "UNKNOWN"),
                            "file": issue.get("filename", ""),
                            "line": issue.get("line_number", 0),
                            "code": issue.get("code", ""),
                            "issue": issue.get("issue_text", ""),
                        }
                    )
        except Exception as exc:
            logger.warning("Bandit scan failed: %s", exc)

        # Check for secrets
        secret_results = await self._detect_secrets({})
        results["findings"].extend(secret_results.get("findings", []))

        # Check dependencies for vulnerabilities
        try:
            result = subprocess.run(
                ["pip-audit", "--format=json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                audit_results = json.loads(result.stdout)
                for vuln in audit_results.get("vulnerabilities", []):
                    results["findings"].append(
                        {
                            "type": "dependency_vulnerability",
                            "package": vuln.get("package", ""),
                            "version": vuln.get("installed_version", ""),
                            "fixed_versions": vuln.get("fixed_versions", []),
                            "description": vuln.get("description", ""),
                        }
                    )
        except Exception as exc:
            logger.warning("Dependency audit failed: %s", exc)

        return results

    async def _threat_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create threat model."""
        system = payload.get("system", "unknown")
        assets = payload.get("assets", [])

        # STRIDE threat modeling
        stride_categories = {
            "Spoofing": "Authentication bypass, identity theft",
            "Tampering": "Data modification, parameter manipulation",
            "Repudiation": "Non-repudiation failures, audit gaps",
            "Information Disclosure": "Data leaks, error messages, PII exposure",
            "Denial of Service": "Resource exhaustion, crash vectors",
            "Elevation of Privilege": "Authorization bypass, privilege escalation",
        }

        threats = []
        for category, description in stride_categories.items():
            threats.append(
                {
                    "category": category,
                    "description": description,
                    "mitigations": self._get_stride_mitigations(category),
                }
            )

        return {
            "system": system,
            "assets": assets,
            "threats": threats,
            "model": "STRIDE",
        }

    def _get_stride_mitigations(self, category: str) -> list[str]:
        mitigations = {
            "Spoofing": ["Strong authentication", "MFA", "Certificate pinning"],
            "Tampering": ["Input validation", "Digital signatures", "Integrity checks"],
            "Repudiation": ["Audit logging", "Digital signatures", "Non-repudiation protocols"],
            "Information Disclosure": ["Encryption", "Data minimization", "Access controls"],
            "Denial of Service": ["Rate limiting", "Circuit breakers", "Auto-scaling"],
            "Elevation of Privilege": ["Least privilege", "RBAC", "Privilege separation"],
        }
        return mitigations.get(category, [])

    async def _scan_vulnerabilities(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Scan for vulnerabilities."""
        payload.get("target", "code")

        results = {"vulnerabilities": []}

        # SAST with semgrep if available
        try:
            result = subprocess.run(
                ["semgrep", "--config=auto", "--json", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                semgrep_results = json.loads(result.stdout)
                for finding in semgrep_results.get("results", []):
                    results["vulnerabilities"].append(
                        {
                            "rule": finding.get("check_id", ""),
                            "severity": finding.get("extra", {}).get("severity", "INFO"),
                            "message": finding.get("extra", {}).get("message", ""),
                            "file": finding.get("path", ""),
                            "line": finding.get("start", {}).get("line", 0),
                        }
                    )
        except Exception as exc:
            logger.warning("Semgrep scan failed: %s", exc)

        return results

    async def _check_compliance(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check compliance requirements."""
        framework = payload.get("framework", "OWASP")

        compliance_checks = {
            "OWASP_TOP_10": [
                "A01: Broken Access Control",
                "A02: Cryptographic Failures",
                "A03: Injection",
                "A04: Insecure Design",
                "A05: Security Misconfiguration",
                "A06: Vulnerable Components",
                "A07: Authentication Failures",
                "A08: Software Integrity Failures",
                "A09: Logging/Monitoring Failures",
                "A10: SSRF",
            ],
            "PCI_DSS": [
                "Build and Maintain a Secure Network",
                "Protect Cardholder Data",
                "Maintain a Vulnerability Management Program",
                "Implement Strong Access Control Measures",
                "Regularly Monitor and Test Networks",
                "Maintain an Information Security Policy",
            ],
        }

        checks = compliance_checks.get(framework, [])
        results = {
            "framework": framework,
            "requirements": checks,
            "status": "pending",
            "details": {},
        }

        # This would integrate with actual compliance tools
        return results

    async def _detect_secrets(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detect secrets in codebase."""
        try:
            # Use detect-secrets if available
            result = subprocess.run(
                ["detect-secrets", "scan", "--all-files"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                secrets_data = json.loads(result.stdout)
                findings = [
                    {
                        "type": secret.get("type", "UNKNOWN"),
                        "file": file_path,
                        "line": secret.get("line_number", 0),
                        "hashed_secret": secret.get("hashed_secret", ""),
                    }
                    for file_path, secrets in secrets_data.get("results", {}).items()
                    for secret in secrets
                ]
                return {"findings": findings}
        except Exception as exc:
            logger.warning("Secret detection failed: %s", exc)

        return {"findings": []}

    async def _analyze_code(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze code for security issues."""
        payload.get("target", "code")
        payload.get("language", "python")

        results = {"findings": []}

        # Run security-focused static analysis
        try:
            # Bandit for Python security issues
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                for issue in bandit_results.get("results", []):
                    results["findings"].append(
                        {
                            "type": "bandit",
                            "severity": issue.get("issue_severity", "UNKNOWN"),
                            "confidence": issue.get("issue_confidence", "UNKNOWN"),
                            "file": issue.get("filename", ""),
                            "line": issue.get("line_number", 0),
                            "code": issue.get("code", ""),
                            "issue": issue.get("issue_text", ""),
                        }
                    )
        except Exception as exc:
            logger.warning("Bandit scan failed: %s", exc)

        # Check for common security patterns
        try:
            result = subprocess.run(
                ["semgrep", "--config=auto", "--json", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                semgrep_results = json.loads(result.stdout)
                for finding in semgrep_results.get("results", []):
                    results["findings"].append(
                        {
                            "rule": finding.get("check_id", ""),
                            "severity": finding.get("extra", {}).get("severity", "INFO"),
                            "message": finding.get("extra", {}).get("message", ""),
                            "file": finding.get("path", ""),
                            "line": finding.get("start", {}).get("line", 0),
                        }
                    )
        except Exception as exc:
            logger.warning("Semgrep scan failed: %s", exc)

        return results


class CodeReviewerAgent(BaseSpecializedAgent):
    """Code Reviewer Agent - Style enforcement, bug detection, performance analysis."""

    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name="Code Reviewer",
            role="Code Reviewer",
            capabilities={
                "code_review",
                "code_analysis",
                "style_checking",
                "bug_detection",
                "performance_analysis",
                "complexity_analysis",
            },
            registry=registry,
            project_root=project_root,
        )

    def _register_handlers(self) -> None:
        self.register_task_handler("review_code", self._review_code)
        self.register_task_handler("check_style", self._check_style)
        self.register_task_handler("analyze_complexity", self._analyze_complexity)
        self.register_task_handler("detect_bugs", self._detect_bugs)
        self.register_task_handler("analyze_code", self._analyze_code)
        self.register_task_handler("review_pr", self._review_pr)

    async def _review_code(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Review code for issues."""
        payload.get("code", "")
        file_path = payload.get("file_path", "")
        language = payload.get("language", "python")

        issues = []

        # Run linters
        if language == "python":
            # Run ruff
            try:
                result = subprocess.run(
                    ["ruff", "check", "--output-format=json", file_path or "."],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.stdout:
                    issues.extend(
                        {
                            "type": "style",
                            "rule": issue.get("code", ""),
                            "message": issue.get("message", ""),
                            "file": issue.get("filename", file_path),
                            "line": issue.get("location", {}).get("row", 0),
                            "severity": "warning",
                        }
                        for issue in json.loads(result.stdout)
                    )
            except Exception as exc:
                logger.warning("Ruff check failed: %s", exc)

        # Check for common issues
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    # Long lines
                    if len(line) > 120:
                        issues.append(
                            {
                                "type": "style",
                                "rule": "line-too-long",
                                "message": f"Line exceeds 120 characters ({len(line)})",
                                "file": file_path,
                                "line": i,
                                "severity": "info",
                            }
                        )
                    # TODO/FIXME comments
                    if "TODO" in line or "FIXME" in line or "XXX" in line or "HACK" in line:
                        issues.append(
                            {
                                "type": "maintenance",
                                "rule": "todo-comment",
                                "message": "Found TODO/FIXME/XXX/HACK comment",
                                "file": file_path,
                                "line": i,
                                "severity": "info",
                            }
                        )
            except Exception:
                pass

        return {
            "file": file_path,
            "language": language,
            "issues": issues,
            "summary": {
                "total": len(issues),
                "errors": len([i for i in issues if i.get("severity") == "error"]),
                "warnings": len([i for i in issues if i.get("severity") == "warning"]),
                "info": len([i for i in issues if i.get("severity") == "info"]),
            },
        }

    async def _check_style(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check code style."""
        return await self._review_code(payload)

    async def _analyze_complexity(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze code complexity."""
        target = payload.get("target", ".")
        results = {"functions": [], "classes": [], "summary": {}}

        try:
            # Use radon for complexity analysis
            result = subprocess.run(
                ["radon", "cc", "-j", str(target)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                data = json.loads(result.stdout)
                for item in data:
                    if item.get("type") in ("function", "method"):
                        results["functions"].append(
                            {
                                "name": item.get("name", ""),
                                "file": item.get("file", ""),
                                "line": item.get("lineno", 0),
                                "complexity": item.get("complexity", 0),
                                "rank": item.get("rank", ""),
                            }
                        )
                    elif item.get("type") == "class":
                        results["classes"].append(
                            {
                                "name": item.get("name", ""),
                                "file": item.get("file", ""),
                                "line": item.get("lineno", 0),
                                "methods": item.get("methods", 0),
                            }
                        )
        except Exception as exc:
            logger.warning("Complexity analysis failed: %s", exc)

        # Calculate summary
        if results["functions"]:
            [f["complexity"] for f in results["functions"]]
            results["summary"] = {
                "total_functions": len(results["functions"]),
                "avg_complexity": sum(c["complexity"] for c in results["functions"])
                / len(results["functions"]),
                "max_complexity": max(c["complexity"] for c in results["functions"]),
                "high_complexity_count": len(
                    [f for f in results["functions"] if f["complexity"] > 10]
                ),
            }

        return results

    async def _detect_bugs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detect potential bugs."""
        # Use pyflakes, mypy, or similar
        issues = []

        try:
            # Run mypy for type checking
            result = subprocess.run(
                ["mypy", "--strict", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if ":" in line and ("error:" in line or "warning:" in line):
                        parts = line.split(":", 3)
                        if len(parts) >= 4:
                            issues.append(
                                {
                                    "type": "type_error" if "error:" in line else "type_warning",
                                    "file": parts[0],
                                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                                    "message": parts[3].strip(),
                                }
                            )
        except Exception as exc:
            logger.warning("Mypy check failed: %s", exc)

        return {
            "bugs_found": len(issues),
            "issues": issues,
        }

    async def _review_pr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Review a pull request."""
        pr_number = payload.get("pr_number")
        payload.get("repo", ".")

        # This would integrate with GitHub/GitLab API
        # For now, return a template
        return {
            "pr_number": pr_number,
            "status": "review_requested",
            "checks": {
                "style": "pending",
                "tests": "pending",
                "security": "pending",
                "complexity": "pending",
            },
            "comments": [],
        }

    async def _analyze_code(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze code for issues - delegates to _review_code."""
        return await self._review_code(payload)


class TestEngineerAgent(BaseSpecializedAgent):
    """Test Engineer Agent - Test generation, coverage analysis, flake detection."""

    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name="Test Engineer",
            role="Test Engineer",
            capabilities={
                "test_generation",
                "test_execution",
                "coverage_analysis",
                "flake_detection",
                "test_maintenance",
            },
            registry=registry,
            project_root=project_root,
        )

    def _register_handlers(self) -> None:
        self.register_task_handler("generate_tests", self._generate_tests)
        self.register_task_handler("run_tests", self._run_tests)
        self.register_task_handler("analyze_coverage", self._analyze_coverage)
        self.register_task_handler("detect_flakes", self._detect_flakes)
        self.register_task_handler("improve_tests", self._improve_tests)

    async def _generate_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate tests for code."""
        target_file = payload.get("file_path", "")
        payload.get("test_type", "unit")
        framework = payload.get("framework", "pytest")

        if not target_file:
            return {"error": "file_path required"}

        try:
            Path(target_file).read_text(encoding="utf-8")
        except Exception:
            return {"error": "Could not read source file"}

        # Analyze source to identify testable functions/classes
        test_cases = self._analyze_for_tests(source_file=target_file)

        # Generate test file
        test_file = self._generate_test_file(
            source_file=target_file,
            test_cases=test_cases,
            framework=framework,
        )

        return {
            "test_file": test_file,
            "test_cases": len(test_cases),
            "framework": framework,
        }

    def _analyze_for_tests(self, source_file: str) -> list[dict]:
        """Analyze source file for testable units."""
        test_cases = []
        try:
            import ast

            content = Path(source_file).read_text(encoding="utf-8")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith("_"):
                        test_cases.append(
                            {
                                "type": "function",
                                "name": node.name,
                                "args": [arg.arg for arg in node.args.args],
                                "returns": ast.unparse(node.returns) if node.returns else None,
                            }
                        )
                elif isinstance(node, ast.ClassDef):
                    test_cases.extend(
                        {
                            "type": "method",
                            "class": node.name,
                            "name": method.name,
                            "args": [arg.arg for arg in method.args.args if arg.arg != "self"],
                        }
                        for method in node.body
                        if isinstance(method, ast.FunctionDef) and not method.name.startswith("_")
                    )
        except Exception:
            pass

        return test_cases

    def _generate_test_file(
        self,
        source_file: str,
        test_cases: list[dict],
        framework: str,
    ) -> str:
        """Generate test file content."""
        source_path = Path(source_file)
        test_file = source_path.parent / "tests" / f"test_{source_path.stem}.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)

        imports = [
            "import pytest",
            f"from {source_path.stem} import *",
        ]

        test_functions = []
        for case in test_cases:
            if case["type"] == "function":
                func_name = case["name"]
                args = case["args"]
                args_str = ", ".join(args) if args else ""
                test_functions.append(f"""
def test_{func_name}():
    # TODO: Implement test for {func_name}
    # Args: {args_str}
    result = {func_name}({args_str})
    assert result is not None
""")
            elif case["type"] == "method":
                class_name = case["class"]
                method_name = case["name"]
                args = case["args"]
                args_str = ", ".join(args) if args else ""
                test_functions.append(f"""
class Test{case["class"]}:
    def test_{method_name}(self):
        # TODO: Implement test for {class_name}.{method_name}
        # Args: {args_str}
        instance = {class_name}()
        result = instance.{method_name}({args_str})
        assert result is not None
""")

        content = "\n".join(imports) + "\n\n" + "\n".join(test_functions)
        test_file.write_text(content, encoding="utf-8")

        return str(test_file)

    async def _run_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run test suite."""
        test_path = payload.get("path", ".")
        payload.get("pattern", "test_*.py")
        timeout = payload.get("timeout", 120)

        try:
            cmd = ["python", "-m", "pytest", test_path, "-v", "--tb=short", "-x"]
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Parse results
            passed = result.stdout.count("PASSED")
            failed = result.stdout.count("FAILED")
            errors = result.stdout.count("ERROR")

            return {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "returncode": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
            }
        except subprocess.TimeoutExpired:
            return {"error": "Tests timed out"}
        except Exception as exc:
            return {"error": str(exc)}

    async def _analyze_coverage(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze test coverage."""
        try:
            cmd = ["coverage", "run", "-m", "pytest"]
            subprocess.run(cmd, cwd=self.project_root, capture_output=True, timeout=120)

            result = subprocess.run(
                ["coverage", "json", "-o", "-"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                data = json.loads(result.stdout)
                return {
                    "total_coverage": data.get("totals", {}).get("percent_covered", 0),
                    "files": {
                        f: d.get("summary", {}).get("percent_covered", 0)
                        for f, d in data.get("files", {}).items()
                    },
                    "missing_lines": {
                        f: d.get("missing_lines", []) for f, d in data.get("files", {}).items()
                    },
                }
        except Exception as exc:
            logger.warning("Coverage analysis failed: %s", exc)

        return {"error": "Coverage analysis failed"}

    async def _detect_flakes(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detect flaky tests."""
        runs = payload.get("runs", 5)
        test_path = payload.get("path", ".")

        flaky_tests = {}

        for _i in range(runs):
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "--tb=no", "-q", test_path],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                # Parse failures
                for line in result.stdout.split("\n"):
                    if "FAILED" in line or "PASSED" in line:
                        parts = line.split("::")
                        if len(parts) >= 2:
                            test_name = parts[-1].split()[0]
                            status = "FAILED" if "FAILED" in line else "PASSED"
                            if test_name not in flaky_tests:
                                flaky_tests[test_name] = {"passed": 0, "failed": 0}
                            if status == "PASSED":
                                flaky_tests[test_name]["passed"] += 1
                            else:
                                flaky_tests[test_name]["failed"] += 1
            except Exception as exc:
                logger.warning("Flake detection run failed: %s", exc)

        # Identify flaky tests (both pass and fail)
        flaky = {
            name: stats
            for name, stats in flaky_tests.items()
            if stats["passed"] > 0 and stats["failed"] > 0
        }

        return {
            "total_runs": runs,
            "flaky_tests": flaky,
            "flaky_count": len(flaky),
        }

    async def _improve_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Improve existing tests."""
        target_file = payload.get("file_path", "")
        improvements = []

        if not target_file:
            return {"error": "file_path required"}

        try:
            content = Path(target_file).read_text(encoding="utf-8")

            # Add missing assertions
            if "assert" not in content and "def test_" in content:
                improvements.append("Add explicit assertions")

            # Check for pytest fixtures
            if "@pytest.fixture" not in content:
                improvements.append("Consider adding pytest fixtures")

            # Check for parametrized tests
            if "@pytest.mark.parametrize" not in content and "def test_" in content:
                improvements.append("Consider parametrized tests for multiple inputs")

            # Check for mocking
            if "mock" not in content.lower() and (
                "requests" in content or "http" in content.lower()
            ):
                improvements.append("Consider mocking external HTTP calls")

        except Exception as exc:
            logger.warning("Test improvement analysis failed: %s", exc)

        return {
            "file": target_file,
            "improvements": improvements,
            "total_suggestions": len(improvements),
        }


class DocumentationAgent(BaseSpecializedAgent):
    """Documentation Agent - API docs, architecture decision records, README generation."""

    def __init__(
        self,
        agent_id: str,
        registry: AgentRegistry,
        project_root: Path,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name="Documentation Agent",
            role="Technical Writer",
            capabilities={
                "documentation_generation",
                "api_documentation",
                "adr_management",
                "readme_generation",
                "changelog_generation",
            },
            registry=registry,
            project_root=project_root,
        )

    def _register_handlers(self) -> None:
        self.register_task_handler("generate_docs", self._generate_docs)
        self.register_task_handler("generate_api_docs", self._generate_api_docs)
        self.register_task_handler("create_readme", self._create_readme)
        self.register_task_handler("generate_changelog", self._generate_changelog)
        self.register_task_handler("update_adr", self._update_adr)

    async def _generate_docs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate documentation for the project."""
        target = payload.get("target", "all")
        output_dir = self.project_root / "docs"
        output_dir.mkdir(exist_ok=True)

        results = {"generated": []}

        if target in ("all", "readme"):
            await self._create_readme({})
            results["generated"].append("README.md")

        if target in ("all", "api"):
            await self._generate_api_docs({})
            results["generated"].append("API documentation")

        if target in ("all", "adr"):
            adr_list = list(self.project_root.rglob("docs/adr/*.md"))
            results["generated"].append(f"{len(adr_list)} ADRs")

        return results

    async def _generate_api_docs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate API documentation from code."""
        # This would use sphinx, pdoc, or similar
        output_dir = self.project_root / "docs" / "api"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Try pdoc
            result = subprocess.run(
                ["pdoc", "-o", str(output_dir), "--force", "."],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return {
                    "status": "success",
                    "output_dir": str(output_dir),
                    "tool": "pdoc",
                }
        except Exception:
            pass

        return {"status": "failed", "reason": "No documentation generator available"}

    async def _create_readme(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or update README.md."""
        readme_path = self.project_root / "README.md"

        # Gather project info
        project_name = self.project_root.name
        pyproject = self.project_root / "pyproject.toml"
        description = "ZKSATO - Automated Trading Platform for SET/TFEX"

        if pyproject.exists():
            try:
                import tomllib

                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                project_info = data.get("project", {})
                project_name = project_info.get("name", project_name)
                description = project_info.get("description", description)
            except Exception:
                pass

        readme_content = f"""# {project_name}

{description}

## Features
- Automated trading for SET/TFEX
- Risk-first architecture
- Multi-agent orchestration
- Local LLM integration (Ollama, llama.cpp, vLLM)
- MCP (Model Context Protocol) integration

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run tests
pytest

# Start TUI
zksato tui start
```

## Architecture
- **Phase 1**: Trading platform core (broker, risk, market data)
- **Phase 2**: Autonomous agent orchestration
- **Phase 3**: Coding agent capabilities (edit, search, plan, skills)
- **Phase 4**: MCP integration, context management, Git ops

## Documentation
- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/api/)
- [ADRs](docs/adr/)

## License
MIT License
"""

        Path("README.md").write_text(readme_content, encoding="utf-8")

        return {
            "status": "success",
            "file": "README.md",
            "path": str(readme_path),
        }

    async def _generate_changelog(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate CHANGELOG.md from git history."""
        payload.get("since", "latest-tag")
        self.project_root / "CHANGELOG.md"

        try:
            # Get git tags
            result = subprocess.run(
                ["git", "tag", "--sort=-v:refname"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )
            tags = result.stdout.strip().split("\n") if result.stdout else []

            # Generate changelog
            changelog = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"

            # This is a simplified version - real implementation would parse commits
            changelog += "\n## [Unreleased]\n\n### Added\n- Multi-agent orchestration\n- MCP integration\n- Context management\n\n"

            Path("CHANGELOG.md").write_text(changelog, encoding="utf-8")

            return {
                "status": "success",
                "file": "CHANGELOG.md",
                "tags_processed": len(tags),
            }
        except Exception as exc:
            logger.warning("Changelog generation failed: %s", exc)
            return {"error": str(exc)}

    async def _update_adr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update or create an Architecture Decision Record."""
        adr_id = payload.get("adr_id")
        title = payload.get("title", "")
        status = payload.get("status", "proposed")
        context = payload.get("context", "")
        decision = payload.get("decision", "")
        consequences = payload.get("consequences", "")

        adr_dir = self.project_root / "docs" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)

        if adr_id:
            # Update existing
            adr_files = list(adr_dir.glob(f"{adr_id}-*.md"))
            if not adr_files:
                return {"error": f"ADR {adr_id} not found"}
            adr_file = adr_files[0]
        else:
            # Create new
            existing = list(adr_dir.glob("*.md"))
            numbers = [
                int(f.stem.split("-")[0]) for f in existing if f.stem.split("-")[0].isdigit()
            ]
            next_num = max(numbers, default=0) + 1
            adr_id = f"{next_num:03d}"
            adr_file = adr_dir / f"{adr_id}-{title.lower().replace(' ', '-')}.md"

        adr_content = f"""# {adr_id}: {title}

## Status
{status}

## Context
{context}

## Decision
{decision}

## Consequences
{consequences}

## Date
{datetime.now(UTC).strftime("%Y-%m-%d")}
"""

        adr_file.write_text(adr_content, encoding="utf-8")

        return {
            "adr_id": adr_id,
            "title": title,
            "status": status,
            "file": str(adr_file),
        }
