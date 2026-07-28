from typing import Literal, Final, Optional, List, Any

ARTIFACT_TYPE = Literal["directory", "file"]

ARTIFACT_TYPE_DIRECTORY: Literal["directory"] = "directory"
ARTIFACT_TYPE_FILE: Literal["file"] = "file"

ARTIFACT_TYPES: Final[tuple] = (
    ARTIFACT_TYPE_DIRECTORY,
    ARTIFACT_TYPE_FILE,
)

ARTIFACT_PUSH_POLICY = Literal["manual", "auto"]

ARTIFACT_PUSH_POLICY_MANUAL: Literal["manual"] = "manual"
ARTIFACT_PUSH_POLICY_AUTO: Literal["auto"] = "auto"

ARTIFACT_PUSH_POLICIES: Final[tuple] = (
    ARTIFACT_PUSH_POLICY_MANUAL,
    ARTIFACT_PUSH_POLICY_AUTO,
)

class Artifact:
    artifact_id: str
    name: str
    artifact_type: ARTIFACT_TYPE
    push_policy: ARTIFACT_PUSH_POLICY
    metadata: Optional[dict]

class ArtifactsListParams:
    metadata: Optional[dict]

class ArtifactsListResult:
    artifacts: List[Artifact]
    metadata: Optional[dict]

class ArtifactsGetParams:
    artifact_id: Optional[str]
    metadata: Optional[dict]

class ArtifactsGetResult:
    artifact: Optional[Artifact]
    metadata: Optional[dict]

class ArtifactsPushParams:
    artifact_id: str
    metadata: Optional[dict]

class ArtifactsPushResult:
    artifact_id: str
    status: str
    metadata: Optional[dict]

class ArtifactsPullParams:
    artifact_id: str
    metadata: Optional[dict]

class ArtifactsPullResult:
    artifact_id: str
    status: str
    metadata: Optional[dict]

class ArtifactsDeleteParams:
    artifact_id: str
    metadata: Optional[dict]

class ArtifactsDeleteResult:
    artifact_id: str
    metadata: Optional[dict]
