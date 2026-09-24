from datetime import datetime


class AgentLogger:
    def __init__(self):
        self.entries = []

    def log(self, stage: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = {
            "time": timestamp,
            "stage": stage,
            "message": message,
        }

        self.entries.append(entry)

        print(f"[{timestamp}] [{stage}] {message}")

    def get_entries(self):
        return self.entries