import asyncio
import random
import math
from mango import Agent, create_tcp_container, activate


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
    async def broadcast_prices(self, houses, price_gen, interval=1.0):
        """Broadcast generated prices indefinitely."""
        tick = 0
        for price in price_gen:
            print(f"[MARKET] tick={tick:03d} -> price={price:.3f} €/kWh")
            for h in houses:
                self.schedule_instant_message({"type": "PRICE", "price": price}, h.addr)
            tick += 1
            await asyncio.sleep(interval)


class House(Agent):
    def __init__(self, name, buy_thr, sell_thr, capacity, charge_rate=0.5, sell_rate=0.5):
        super().__init__()
        self.name = name
        self.buy_thr = buy_thr           # price threshold to buy energy
        self.sell_thr = sell_thr         # price threshold to sell energy
        self.capacity = capacity         # battery capacity (kWh)
        self.saved_energy = 0.0          # current stored energy
        self.charge_rate = charge_rate   # kWh per tick
        self.sell_rate = sell_rate       # kWh per tick
        self.mode = "IDLE"

    def handle_message(self, content, meta):
        if content.get("type") != "PRICE":
            return
        price = float(content["price"])

        # Hysteresis-based decision and mode switching
        if price <= self.buy_thr and self.mode != "CHARGE":
            self.mode = "CHARGE"
            print(f"[{self.name}] price={price:.3f} -> CHARGE battery")
        elif price >= self.sell_thr and self.mode != "SELL":
            self.mode = "SELL"
            print(f"[{self.name}] price={price:.3f} -> SELL surplus")
        elif self.buy_thr < price < self.sell_thr and self.mode != "IDLE":
            self.mode = "IDLE"
            print(f"[{self.name}] price={price:.3f} -> IDLE")

        # action application
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

    # register agents
    market = container.register(Market())
    h1 = container.register(House("HouseA", buy_thr=0.10, sell_thr=0.18, capacity=3.0))
    h2 = container.register(House("HouseB", buy_thr=0.12, sell_thr=0.20, capacity=4.0))
    h3 = container.register(House("HouseC", buy_thr=0.09, sell_thr=0.16, capacity=2.5))

    async with activate(container):
        gen = price_generator()
        await market.broadcast_prices([h1, h2, h3], gen, interval=1.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MAIN] stopped by user.")
