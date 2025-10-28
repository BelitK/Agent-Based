#Fibonacci agents example
import asyncio
from mango import Agent, create_tcp_container, activate, sender_addr


class FibAgent(Agent):
    def __init__(self, name: str, nmax: int):
        super().__init__()
        self.name = name
        self.nmax = nmax

    def handle_message(self, content, meta):
        """
        content: {"n": int, "a": int, "b": int}
                 where a=f_{n-1}, b=f_n
        """
        n = int(content["n"])
        a = int(content["a"])
        b = int(content["b"])

        print(f"[{self.name}] n={n}, f_n={b}")

        if n >= self.nmax:
            # reached target index, do not continue
            return

        # compute next tuple and send back to original sender
        nxt = a + b
        self.schedule_instant_message(
            {"n": n + 1, "a": b, "b": nxt},
            sender_addr(meta)
        )


async def main():
    NMAX = 10  # choose your stop index here (n >= 1). Example: 10 -> stops at f10

    container = create_tcp_container(addr=("127.0.0.1", 5555))

    a = container.register(FibAgent("AgentA", NMAX))
    b = container.register(FibAgent("AgentB", NMAX))

    async with activate(container):
        # Kick off with (n=2, a=f1=1, b=f2=1). This prints f2=1 first.
        # If you want to include n=1 as first print, you can send two seeds or start at n=1.
        a.schedule_instant_message({"n": 2, "a": 1, "b": 1}, b.addr)

        # Give the ping-pong a moment to finish
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
