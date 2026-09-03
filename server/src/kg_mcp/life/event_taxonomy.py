from typing import Dict, List


EVENT_TYPES: List[str] = [
    "APP_FOCUS",
    "ARTIFACT_VIEW",
    "ARTIFACT_EDIT",
    "SEARCH",
    "COMMUNICATION",
    "MEETING",
    "TASK_UPDATE",
    "DOWNLOAD_UPLOAD",
    "DECISION",
    "TODO_FOUND",
    "ERROR_BLOCKER",
    "CONTEXT_SWITCH",
    "IDLE",
    "CODE_NAV",
    "RUN_BUILD_TEST",
    "COMMIT_PR",
]

EVENT_TYPE_WEIGHTS: Dict[str, float] = {
    "ARTIFACT_EDIT": 1.2,
    "SEARCH": 0.9,
    "ARTIFACT_VIEW": 0.6,
    "MEETING": 0.8,
    "DECISION": 1.4,
    "TODO_FOUND": 1.1,
    "ERROR_BLOCKER": 1.2,
    "TASK_UPDATE": 1.0,
    "COMMUNICATION": 0.7,
    "APP_FOCUS": 0.3,
    "CONTEXT_SWITCH": 0.4,
    "IDLE": 0.1,
    "CODE_NAV": 0.9,
    "RUN_BUILD_TEST": 1.0,
    "COMMIT_PR": 1.1,
    "DOWNLOAD_UPLOAD": 0.7,
}

DEFAULT_EVENT_WEIGHT: float = 0.5
