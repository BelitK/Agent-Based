import asyncio
import random
import math
from mango import Agent, create_tcp_container, activate, create_topology  # ← import topology

# ---------- Price Generator ----------
def price_generator(min_price=0.08, max_price=0.25, step=0.1):
    """Infinite generator that yields smooth day-like prices. step based"""
    t = 0.0
    while True:
        base = 0.165 + 0.07 * math.sin(t)              # sinusoidal daily curve
        noise = random.uniform(-0.015, 0.015)
        price = max(min_price, min(max_price, base + noise))
        yield round(price, 3)
        t += step

# ---------- Agents ----------
class Market(Agent):
    def on_ready(self):
        # Topology service injects neighbors automatically
        nbrs = self.neighbors()  # same as neighbors(State.NORMAL)
        print(f"[MARKET] neighbors:", [str(n) for n in nbrs])

        # Optional hello to each neighbor
        for addr in nbrs:
            self.schedule_instant_message(f"hello from {self.aid}", addr)

    async def broadcast_prices(self, price_gen, interval=1.0):
        """Broadcast generated prices to all topology neighbors indefinitely."""
        tick = 0
        for price in price_gen:
            print(f"[MARKET] tick={tick:03d} -> price={price:.3f} €/kWh")
            for addr in self.neighbors():
                self.schedule_instant_message({"type": "PRICE", "price": price}, addr)
            tick += 1
            await asyncio.sleep(interval)

class House(Agent):
    def __init__(self, name, buy_thr, sell_thr, capacity, charge_rate=0.5, sell_rate=0.5):
        super().__init__()
        self.name = name
        self.buy_thr = buy_thr
        self.sell_thr = sell_thr
        self.capacity = capacity
        self.saved_energy = 0.0
        self.charge_rate = charge_rate
        self.sell_rate = sell_rate
        self.mode = "IDLE"

    def handle_message(self, content, meta):
        if not isinstance(content, dict) or content.get("type") != "PRICE":
            return
        price = float(content["price"])
        print(f'{content}')

        # Hysteresis-based switching
        if price <= self.buy_thr and self.mode != "CHARGE":
            self.mode = "CHARGE"
            print(f"[{self.name}] price={price:.3f} -> CHARGE battery")
        elif price >= self.sell_thr and self.mode != "SELL":
            self.mode = "SELL"
            print(f"[{self.name}] price={price:.3f} -> SELL surplus")
        elif self.buy_thr < price < self.sell_thr and self.mode != "IDLE":
            self.mode = "IDLE"
            print(f"[{self.name}] price={price:.3f} -> IDLE")

        # Apply action
        if self.mode == "CHARGE":
            old = self.saved_energy
            self.saved_energy = min(self.capacity, self.saved_energy + self.charge_rate)
            delta = self.saved_energy - old
            if delta > 0:
                print(f"[{self.name}] +{delta:.2f} kWh charged (stored={self.saved_energy:.2f}/{self.capacity})")
        elif self.mode == "SELL":
            sold = min(self.sell_rate, self.saved_energy)
            self.saved_energy -= sold
            print(f"[{self.name}] sold {sold:.2f} kWh (stored={self.saved_energy:.2f}/{self.capacity})")

# ---------- Main ----------
async def main():
    container = create_tcp_container(addr=("127.0.0.1", 5555))

    # Create agents
    market = Market()
    h1 = House("HouseA", buy_thr=0.10, sell_thr=0.18, capacity=3.0)
    h2 = House("HouseB", buy_thr=0.12, sell_thr=0.20, capacity=4.0)
    h3 = House("HouseC", buy_thr=0.09, sell_thr=0.16, capacity=2.5)
    h4 = House("HouseD", buy_thr=0.11, sell_thr=0.19, capacity=3.5)

    # Register agents
    market = container.register(market)
    h1 = container.register(h1)
    h2 = container.register(h2)
    h3 = container.register(h3)
    h4 = container.register(h4)

    # Build topology: connect Market to each House, One-to-Many connection for price broadcasting
    # Undirected edges mean Market sees Houses as neighbors and vice versa
    with create_topology() as topo:
        m_id = topo.add_node(market)
        h1_id = topo.add_node(h1)
        h2_id = topo.add_node(h2)
        h3_id = topo.add_node(h3)
        h4_id = topo.add_node(h4)

        topo.add_edge(m_id, h1_id)
        topo.add_edge(m_id, h2_id)
        topo.add_edge(m_id, h3_id)
        topo.add_edge(m_id, h4_id)

    async with activate(container):
        gen = price_generator()
        await market.broadcast_prices(gen, interval=1.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MAIN] stopped by user.")
