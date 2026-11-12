"""zksato-automation: Trading automation, scheduler, and agent OS."""

from zksato_automation.scheduler import TradingScheduler
from zksato_automation.service import TradingService
from zksato_automation.agent_os.skills import SkillRegistry
from zksato_automation.agent_os.subaccount import SubAccount
from zksato_automation.agent_os.engine import AgentEngine
from zksato_automation.agent_os.session import AgentSession
from zksato_automation.tools.registry import ToolRegistry
from zksato_automation.scheduler.hooks import HookManager
from zksato_automation.agent_os.a2a import AgentRegistry, A2AMessage
from zksato_automation.scheduler.state import CheckpointManager

__version__ = "2.0.0-dev"

__all__ = [
    "TradingScheduler",
    "TradingService",
    "SkillRegistry",
    "SubAccount",
    "AgentEngine",
    "AgentSession",
    "ToolRegistry",
    "HookManager",
    "AgentRegistry",
    "A2AMessage",
    "CheckpointManager",
]