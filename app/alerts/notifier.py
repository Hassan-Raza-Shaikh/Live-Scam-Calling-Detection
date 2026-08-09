class AlertNotifier:
    """Dispatches warning notifications via sound, UI, or socket events."""
    def send_notification(self, title: str, body: str):
        print(f"[ALERT]: {title} - {body}")
