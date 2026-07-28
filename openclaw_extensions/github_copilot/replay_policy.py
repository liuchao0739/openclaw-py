from typing import Dict, List


def buildGithubCopilotReplayPolicy(modelId: str) -> Dict:
    return {}


def sanitizeGithubCopilotReplayHistory(history: List[Dict]) -> List[Dict]:
    return history


__all__ = ["buildGithubCopilotReplayPolicy", "sanitizeGithubCopilotReplayHistory"]