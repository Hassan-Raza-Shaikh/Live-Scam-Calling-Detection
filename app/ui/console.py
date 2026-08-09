class ConsoleUI:
    """Command Line Console layout interface helper."""
    def render_threat_log(self, log_lines: list):
        for line in log_lines:
            print(line)
