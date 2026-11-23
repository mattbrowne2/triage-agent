from enum import StrEnum, auto


class ToolName(StrEnum):
    QUERY_LOGS = auto()
    SEARCH_PAST_INCIDENTS = auto()
    SUMMARIZE_LOG_PATTERNS = auto()
    CREATE_JIRA_TICKET = auto()
