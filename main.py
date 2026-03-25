from typing import List
from cat import hook, AgenticWorkflowConfig, BaseAgenticWorkflowHandler

from .agent import ReActAgentConfig


@hook
def factory_allowed_agentic_workflows(allowed: List[AgenticWorkflowConfig], cat) -> List[AgenticWorkflowConfig]:
    allowed.append(ReActAgentConfig)  # type: ignore
    return allowed
