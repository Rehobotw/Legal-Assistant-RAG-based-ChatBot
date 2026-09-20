from dataclasses import dataclass

@dataclass
class Conversation:
    id: int
    user_id: int
    title: str
