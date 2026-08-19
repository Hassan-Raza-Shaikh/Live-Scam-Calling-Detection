class ConversationError(Exception):
    """Base exception for all Conversation Context Framework errors."""
    pass

class StateError(ConversationError):
    """Raised when there are issues updating or retrieving the conversation state."""
    pass

class MemoryError(ConversationError):
    """Raised when memory window constraints are violated or experience issues."""
    pass
