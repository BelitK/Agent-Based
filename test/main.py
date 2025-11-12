# nqueens_tinyllama_shared_model.py
# One shared TinyLlama LLM acts as the recursive reasoning core.
# Coordinator queries TinyLlama each outer step for an improved full-board assignment.
# Queen agents only apply rows and ACK. No PyTorch model here.
#
# Requirements:
#   pip install mango-agents requests
#   Install and run a local LLM server, e.g. Ollama with a TinyLlama-ish model:
#     - ollama pull tinyllama:latest   # or any 1B-3B instruct-capable model
#     - ollama serve                   # listens on http://localhost:11434
#
# Run:
#   python nqueens_tinyllama_shared_model.py

import asyncio
import json
from typing import List, Optional, Tuple

import requests
import mango


# ================= Config =================
N = 8                       # board size
OUTER_STEPS = 16            # max refinement rounds
MODEL_NAME = "tinyllama"    # Ollama model tag (adjust as installed)
OLLAMA_URL = "http://localhost:11434/api/chat"
TIMEOUT_S = 60
TEMPERATURE = 0.2

# ================= Helpers =================

def conflicts(rows: List[int]) -> int:
    bad = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            ri, rj = rows[i], rows[j]
            if ri == rj or abs(ri - rj) == abs(i - j):
                bad += 1
    return bad


def is_valid_rows(rows: List[int], n: int) -> bool:
    if len(rows) != n:
        return False
    for r in rows:
        if not isinstance(r, int) or r < 0 or r >= n:
            return False
    return True


# ================= LLM client (Ollama Chat) =================
class TinyLlamaClient:
    def __init__(self, model: str = MODEL_NAME, url: str = OLLAMA_URL, temperature: float = TEMPERATURE):
        self.model = model
        self.url = url
        self.temperature = temperature

    def propose_rows(self, n: int, prev_rows: Optional[List[int]], step: int) -> Tuple[List[int], float, str]:
        """Ask the LLM to return a better full-board assignment.
        Returns (rows, halt_prob, rationale). If parsing fails, raises Exception.
        """
        system = (
            "You solve n-Queens by iterative refinement.\n"
            "Return strict JSON only: {\"rows\":[...],\"halt\":<0..1>,\"why\":\"...\"}.\n"
            "No extra text. rows must have length n with integers in [0..n-1].\n"
            "Aim to reduce conflicts each step."
        )
        user = {
            "n": n,
            "step": step,
            "board": prev_rows,
            "rule": "No two queens share a row or diagonal.",
            "request": "Propose an improved full assignment and an estimated halting probability.",
        }
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            "stream": False,
        }
        resp = requests.post(self.url, json=payload, timeout=TIMEOUT_S)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        # Some models may add backticks; try to locate JSON
        content_str = content.strip()
        if content_str.startswith("```"):
            content_str = content_str.strip("`\n ")
        try:
            parsed = json.loads(content_str)
        except Exception as e:
            raise RuntimeError(f"LLM returned non-JSON: {content_str[:200]}") from e
        rows = parsed.get("rows")
        halt = float(parsed.get("halt", 0.0))
        why = str(parsed.get("why", ""))
        if not isinstance(rows, list) or not is_valid_rows(rows, n):
            raise RuntimeError(f"Invalid rows {rows}")
        return rows, halt, why


# ================= Mango agents =================
class QueenAgent(mango.Agent):
    def __init__(self, col_idx: int):
        super().__init__()
        self.col = col_idx
        self.row: Optional[int] = None

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SET_ROWS":
            rows = content["rows"]
            self.row = int(rows[self.col])
            self.schedule_instant_message({"type": "ACK", "col": self.col, "row": self.row}, mango.sender_addr(meta))


class Coordinator(mango.Agent):
    def __init__(self, n: int, client: TinyLlamaClient):
        super().__init__()
        self.n = n
        self.client = client
        self.rows: List[int] = [i % n for i in range(n)]  # simple init
        self.await_acks = asyncio.Event()
        self.acks = 0

    def on_ready(self):
        self.schedule_instant_message({"type": "SOLVE", "step": 0}, self.addr)

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SOLVE":
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
        old_conf = conflicts(self.rows)
        try:
            new_rows, halt_prob, why = self.client.propose_rows(self.n, self.rows, step)
        except Exception as e:
            print(f"[Coordinator] LLM error at step {step}: {e}. Retrying with same rows.")
            new_rows, halt_prob, why = self.rows, 0.0, "retry fallback"

        new_conf = conflicts(new_rows)
        improved = new_conf <= old_conf
        # Commit if improved or allow neutral moves early on
        if improved or step < 2:
            self.rows = new_rows
        else:
            # keep old if worse
            halt_prob *= 0.5

        await self._broadcast_rows_and_wait(self.rows, step)

        c = conflicts(self.rows)
        print(f"[Coordinator] step {step}: conflicts {old_conf} -> {c}, halt={halt_prob:.2f}, why={why[:80]}")

        if c == 0 or halt_prob > 0.9 or step + 1 >= OUTER_STEPS:
            print("[Coordinator] Done.")
            return
        self.schedule_instant_message({"type": "SOLVE", "step": step + 1}, self.addr)


# ================= Topology and runtime =================
async def main():
    # Build a star topology: Coordinator connected to all queens
    with mango.create_topology() as topo:
        client = TinyLlamaClient()
        coord = Coordinator(N, client)
        queens = [QueenAgent(i) for i in range(N)]
        node_c = topo.add_node(coord)
        nodes_q = [topo.add_node(q) for q in queens]
        for nq in nodes_q:
            topo.add_edge(node_c, nq)

    async with mango.run_with_tcp(1, coord, *queens):
        # Let coordinator drive; wait enough time
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
