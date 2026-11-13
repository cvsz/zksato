"""zksato-automation: Trading automation, scheduler, and agent OS."""

from zksato_automation.agent_os.a2a import A2AMessage, AgentRegistry
from zksato_automation.agent_os.engine import AgentEngine
from zksato_automation.agent_os.session import AgentSession
from zksato_automation.agent_os.skills import SkillRegistry
from zksato_automation.agent_os.subaccount import SubAccount
from zksato_automation.scheduler import TradingScheduler
from zksato_automation.scheduler.hooks import HookManager
from zksato_automation.scheduler.state import CheckpointManager
from zksato_automation.service import TradingService
from zksato_automation.tools.registry import ToolRegistry

__version__ = "2.0.0-dev"

__all__ = [
    "A2AMessage",
    "AgentEngine",
    "AgentRegistry",
    "AgentSession",
    "CheckpointManager",
    "HookManager",
    "SkillRegistry",
    "SubAccount",
    "ToolRegistry",
    "TradingScheduler",
    "TradingService",
]
