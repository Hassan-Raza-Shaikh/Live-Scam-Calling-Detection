class UIWidgets:
    """Renders small UI element blocks (threat banners, status dots, metrics gauges)."""
    def get_threat_banner(self, level: str) -> str:
        return f"*** THREAT ALERT: {level} ***"
