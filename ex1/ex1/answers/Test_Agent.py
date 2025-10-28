from mango import Agent, sender_addr
import asyncio

class PVAgent(Agent):
    def __init__(self, neighbor=None):
        super().__init__()
        self.message_count = 0
        self.neighbor = neighbor
        print("Hello I am a Reflexive agent!")

    def handle_message(self, content, meta):
        # increment counter and show receipt
        self.message_count += 1
        print(f"[{self.addr}] Received ({self.message_count}): {content}  meta={meta}")
        if self.message_count <= 10:
            self.schedule_instant_message("Ping" if str(content).lower().startswith("pong") else "Pong", sender_addr(meta))


    def get_message_count(self):
        return self.message_count