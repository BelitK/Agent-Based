# nqueens_trm_mango_shared_model.py
# One shared tiny recursive model (TRM-like) used by a Coordinator agent.
# Queen agents are lightweight and only apply rows they receive.
#
# Requirements:
#   pip install mango-agents torch networkx
#
# Run:
#   python nqueens_trm_mango_shared_model.py

import asyncio
from typing import List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import mango

# ========= Config =========
N = 8                  # board size
OUTER_STEPS = 16       # number of outer recursion steps
INNER_STEPS = 4        # inner latent refinement steps per outer step
H = 64                 # tiny hidden size
DEVICE = torch.device("cuda")

print(DEVICE)
# ========= Utility functions =========
def conflicts(rows: List[int]) -> int:
    """Count pairwise conflicts for a full assignment (one row per column)."""
    bad = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            ri, rj = rows[i], rows[j]
            if ri == rj or abs(ri - rj) == abs(i - j):
                bad += 1
    return bad


def project_to_rows(y_logits: torch.Tensor) -> List[int]:
    """y_logits: [n, n] logits per column. Return argmax row per column."""
    with torch.no_grad():
        rows = torch.argmax(y_logits, dim=1).tolist()
    return [int(r) for r in rows]


def encode_board(rows: List[Optional[int]], n: int) -> torch.Tensor:
    """Encode current partial board as a 2-feature per column vector:
    - feat[0]: 1.0 if column has a queen set, else 0
    - feat[1]: normalized row position if set, else 0
    Output shape: [2*n]
    """
    x = torch.zeros(n, 2, dtype=torch.float32, device=DEVICE)
    for c, r in enumerate(rows):
        if r is not None:
            x[c, 0] = 1.0
            x[c, 1] = float(r) / max(1, n - 1)
    return x.flatten()


# ========= Tiny Recursive Model (shared) =========
class SharedTRM(nn.Module):
    """
    A compact TRM-like module that refines a board assignment recursively.
    - Inputs per outer step: x (board encoding), y (current logits [n,n]), z (latent [h])
    - Inner loop: update z a few times using x and y
    - Answer update: produce new y from z and previous y
    - Halting head q: scalar in [0,1] suggesting to stop when near solution
    """
    def __init__(self, n: int, h: int):
        super().__init__()
        self.n = n
        self.h = h
        self.enc_x = nn.Linear(2 * n, h)
        self.enc_y = nn.Linear(n * n, h)
        self.fz = nn.Sequential(
            nn.Linear(h + h, h),
            nn.ReLU(),
            nn.Linear(h, h),
        )
        self.fy = nn.Sequential(
            nn.Linear(h + h, h),
            nn.ReLU(),
            nn.Linear(h, n * n),
        )
        self.halt = nn.Sequential(nn.Linear(h, 1), nn.Sigmoid())

    def improve(self, x: torch.Tensor, y_logits: torch.Tensor, z: torch.Tensor, inner_steps: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # x: [2n], y_logits: [n,n], z: [h]
        ex = torch.tanh(self.enc_x(x))
        ey = torch.tanh(self.enc_y(y_logits.flatten()))
        # inner latent refinement
        for _ in range(inner_steps):
            z = torch.tanh(self.fz(torch.cat([z, ey], dim=0)))
        # answer update
        y_new = self.fy(torch.cat([z, ey], dim=0)).view(self.n, self.n)
        q = self.halt(z).squeeze(0)  # scalar in [0,1]
        return y_new, z, q


# ========= Mango agents =========
class QueenAgent(mango.Agent):
    def __init__(self, col_idx: int):
        super().__init__()
        self.col = col_idx
        self.row: Optional[int] = None

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SET_ROWS":
            rows = content["rows"]  # full assignment list[int]
            self.row = int(rows[self.col])
            # acknowledge to coordinator
            self.schedule_instant_message({"type": "ACK", "col": self.col, "row": self.row}, mango.sender_addr(meta))


class Coordinator(mango.Agent):
    def __init__(self, n: int, model: SharedTRM):
        super().__init__()
        self.n = n
        self.model = model.to(DEVICE).eval()
        # state
        self.rows: List[Optional[int]] = [None] * n
        # start with uniform logits
        self.y_logits = torch.zeros(n, n, dtype=torch.float32, device=DEVICE)
        self.z = torch.zeros(H, dtype=torch.float32, device=DEVICE)
        self.await_acks = asyncio.Event()
        self.acks = 0

    def on_ready(self):
        self.schedule_instant_message({"type": "SOLVE", "step": 0}, self.addr)

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SOLVE":
            # kick off one outer step via background task
            step = content.get("step", 0)
            asyncio.create_task(self._outer_step(step))
        elif t == "ACK":
            self.acks += 1
            if self.acks == self.n:
                self.await_acks.set()

    async def _broadcast_rows_and_wait(self, rows_int: List[int], step: int):
        self.acks = 0
        self.await_acks.clear()
        for nb in self.neighbors():
            self.schedule_instant_message({"type": "SET_ROWS", "rows": rows_int, "step": step}, nb)
        await self.await_acks.wait()

    async def _outer_step(self, step: int):
        # encode x from current rows (fill Nones with 0 for encoding only)
        x = encode_board([r if r is not None else 0 for r in self.rows], self.n)
        with torch.no_grad():
            self.y_logits, self.z, q = self.model.improve(x, self.y_logits, self.z, INNER_STEPS)
        rows_int = project_to_rows(self.y_logits)
        # commit and broadcast
        self.rows = rows_int  # store as full assignment
        await self._broadcast_rows_and_wait(rows_int, step)

        c = conflicts(rows_int)
        print(f"[Coordinator] step {step} rows={rows_int} conflicts={c} halt_prob={float(q):.3f}")
        if c == 0 or float(q) > 0.9 or step + 1 >= OUTER_STEPS:
            print("[Coordinator] Done.")
            return
        # next step
        self.schedule_instant_message({"type": "SOLVE", "step": step + 1}, self.addr)


# ========= Topology and runtime =========
async def main():
    # Build a star topology: Coordinator connected to all queens
    with mango.create_topology() as topo:
        model = SharedTRM(N, H)
        coord = Coordinator(N, model)
        queens = [QueenAgent(i) for i in range(N)]
        node_c = topo.add_node(coord)
        nodes_q = [topo.add_node(q) for q in queens]
        for nq in nodes_q:
            topo.add_edge(node_c, nq)

    async with mango.run_with_tcp(1, coord, *queens):
        # let the coordinator drive the loop; just wait until it prints Done
        # give plenty of time; terminate when container exits the context
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
