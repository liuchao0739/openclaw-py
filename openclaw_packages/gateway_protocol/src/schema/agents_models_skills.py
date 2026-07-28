from typing import Optional, List, Any

class AgentSummary:
    agent_id: str
    name: Optional[str]
    description: Optional[str]
    version: Optional[str]
    status: Optional[str]
    metadata: Optional[dict]

class AgentsCreateParams:
    name: str
    description: Optional[str]
    version: Optional[str]
    metadata: Optional[dict]

class AgentsCreateResult:
    agent_id: str
    name: str
    description: Optional[str]
    version: Optional[str]
    metadata: Optional[dict]

class AgentsModelsSkillsGetParams:
    agent_id: Optional[str]
    metadata: Optional[dict]

class AgentsModelsSkillsGetResult:
    models: List[str]
    skills: List[str]
    metadata: Optional[dict]
