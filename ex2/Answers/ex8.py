import asyncio
import networkx as nx
import mango

class SampleAgent(mango.Agent):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.event = asyncio.Event()

    def on_ready(self):
        for n in self.neighbors():
            self.schedule_instant_message("Hi", n)

    def handle_message(self, content, meta):
        print(f"[{self.aid}] Received: {content} from {mango.sender_addr(meta)}")
        self.event.set()

async def main():
    container = mango.create_tcp_container("127.0.0.1:9995")

    # Build ring topology from NetworkX
    G = nx.cycle_graph(6)
    topo = mango.custom_topology(G)

    # Attach one agent per topology node, but register them in the same container
    agents = []
    for i, node in enumerate(mango.per_node(topo)):
        a = container.register(SampleAgent(f"agent_{i}"))
        node.add(a)  # bind this registered agent to the corresponding topo node
        agents.append(a)

    async with mango.activate(container):
        await asyncio.gather(agents[0].event.wait(), agents[1].event.wait())
        print("Terminated")

if __name__ == "__main__":
    asyncio.run(main())
