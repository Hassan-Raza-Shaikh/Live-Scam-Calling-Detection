class WorkflowSupervisor:
    """Supervises the high-level state execution pipeline."""
    
    def prepare_workflow(self, session_id: str, raw_text: str):
        return {
            "session_id": session_id,
            "raw_text": raw_text,
            "status": "ready"
        }
