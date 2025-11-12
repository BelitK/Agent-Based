# nqueens_tinyllama_with_visualizer.py
# TinyLlama-driven shared solver + VisualizerAgent integration.
# Coordinator queries a local TinyLlama (via Ollama HTTP) each step, broadcasts rows to queens
# and the visualizer, which saves PNG frames per step.
# Author: BelitK
# Requirements:
#   pip install mango-agents requests matplotlib
#   Optional for GIF: pip install imageio
#   Local LLM server (Ollama):
#       ollama pull tinyllama:latest
#       ollama serve   # http://localhost:11434
#
# Run:
#   python nqueens_tinyllama_with_visualizer.py
#   (optional) from nqueens_visualizer_agent import make_gif; make_gif("frames_llm", "nqueens_run.gif", fps=2)

import asyncio
import json
from typing import List, Optional, Tuple

import requests
import mango

from nqueens_visualizer_agent import VisualizerAgent, make_gif

# ================= Config =================
N = 8                      # board size
OUTER_STEPS = 32             # max refinement rounds
MODEL_NAME = "gemma3:12b"     # Ollama model tag
OLLAMA_URL = "http://localhost:11434/api"
TIMEOUT_S = 60
TEMPERATURE = 0
FRAMES_DIR = "frames_llm"

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
# This version follows the paper's TRM cycle by passing (x, y, z) and receiving (z', y', halt).
class TinyLlamaClient:
    def __init__(self, model: str = MODEL_NAME, url: str = OLLAMA_URL, temperature: float = TEMPERATURE):
        self.model = model
        self.url = url.rstrip("/")
        self.temperature = temperature

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
        return json.loads(text)

    def _validate_rows(self, rows, n: int):
        if not isinstance(rows, list) or len(rows) != n:
            raise RuntimeError(f"rows must be length {n}")
        for r in rows:
            if not isinstance(r, int) or r < 0 or r >= n:
                raise RuntimeError(f"invalid row {r}")

    def improve(self, n: int, x_rows: List[int], y_rows: List[int], z_text: str, step: int) -> Tuple[List[int], float, str, str]:
        """TRM-style call: give (x, y, z) and get (y', z', halt, why).
        Returns (rows, halt, why, z_new).
        """
        system = (
            "You are a recursive reasoning module implementing a Tiny Recursive Model (TRM)."
            "Inputs: x=current board (rows per column), y=previous proposal, z=latent scratchpad."
            "At each step, refine z and then refine y to reduce conflicts."
            "At each step try to make a move that reduces conflicts"
            "When stuck make a random move then try in next step."
            "Return STRICT JSON only with keys: rows (int[n]), halt (0..1), why (string), z (string)."
            "No extra text or code fences."
        )
        user = {
            "n": n,
            "step": step,
            "x": x_rows,
            "y": y_rows,
            "z": z_text,
            "rule": "No two queens share a row or diagonal.",
            "request": "First update z to summarize constraints and conflicts, then update y to reduce conflicts."
        }
        # try /chat then fallback /generate
        payload_chat = {
            "model": self.model,
            "temperature": self.temperature,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            "stream": False,
        }
        try:
            resp = requests.post(f"{self.url}/chat", json=payload_chat, timeout=TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            parsed = self._extract_json(content)
        except Exception:
            prompt = system + "" + json.dumps(user)
            payload_gen = {
                "model": self.model,
                "temperature": min(self.temperature, 0.3),
                "format": "json",
                "prompt": prompt,
                "stream": False,
            }
            resp = requests.post(f"{self.url}/generate", json=payload_gen, timeout=TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("response", "")
            parsed = self._extract_json(content)

        rows = parsed.get("rows")
        halt = float(parsed.get("halt", 0.0))
        why = str(parsed.get("why", ""))
        z_new = str(parsed.get("z", ""))
        self._validate_rows(rows, n)
        return rows, halt, why, z_new


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
        elif t == "DONE":
            # ignore
            pass


class Coordinator(mango.Agent):
    def __init__(self, n: int, client: TinyLlamaClient):
        super().__init__()
        self.n = n
        self.client = client
        # TRM state: x (observed board), y (proposal), z (latent scratchpad)
        self.x_rows: List[int] = [i % n for i in range(n)]  # observed board (here same as y initially)
        self.y_rows: List[int] = self.x_rows.copy()         # proposal refined across steps
        self.z_text: str = ""                                 # latent scratchpad text
        self.await_acks = asyncio.Event()
        self.acks = 0
        self.await_acks = asyncio.Event()
        self.acks = 0

    def on_ready(self):
        # broadcast initial y as frame 0
        for nb in self.neighbors():
            self.schedule_instant_message({"type": "SET_ROWS", "rows": self.y_rows, "step": 0}, nb)
        self.schedule_instant_message({"type": "SOLVE", "step": 1}, self.addr)

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SOLVE":
            step = content.get("step", 1)
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

    async def _broadcast_done(self):
        for nb in self.neighbors():
            self.schedule_instant_message({"type": "DONE"}, nb)

    async def _outer_step(self, step: int):
        old_conf = conflicts(self.y_rows)
        try:
            # TRM step: (x, y, z) -> (y', z', halt)
            new_rows, halt_prob, why, z_new = self.client.improve(
                self.n, self.x_rows, self.y_rows, self.z_text, step
            )
        except Exception as e:
            print(f"[Coordinator] LLM error at step {step}: {e}. Keeping previous rows.")
            new_rows, halt_prob, why, z_new = self.y_rows, 0.0, "retry fallback", self.z_text

        new_conf = conflicts(new_rows)
        improved = new_conf <= old_conf
        # Commit policy (can be changed to simulated annealing or min-conflicts gate)
        if improved or step < 2:
            self.y_rows = new_rows
            self.z_text = z_new
        else:
            halt_prob *= 0.5

        await self._broadcast_rows_and_wait(self.y_rows, step)

        c = conflicts(self.y_rows)
        print(f"[Coordinator] step {step}: conflicts {old_conf} -> {c}, halt={halt_prob:.2f}, why={why[:80]}")

        if c == 0 or halt_prob > 0.9 or step + 1 > OUTER_STEPS:
            print("[Coordinator] Done.")
            await self._broadcast_done()
            return
        self.schedule_instant_message({"type": "SOLVE", "step": step + 1}, self.addr)


# ================= Topology and runtime =================
async def main():
    # Build star: Coordinator -> queens and visualizer
    with mango.create_topology() as topo:
        client = TinyLlamaClient()
        coord = Coordinator(N, client)
        queens = [QueenAgent(i) for i in range(N)]
        vis = VisualizerAgent(board_size=N, out_dir=FRAMES_DIR)

        node_c = topo.add_node(coord)
        nodes_q = [topo.add_node(q) for q in queens]
        node_v = topo.add_node(vis)
        # connect coordinator to all others
        for nq in nodes_q:
            topo.add_edge(node_c, nq)
        topo.add_edge(node_c, node_v)

    async with mango.run_with_tcp(1, coord, *queens, vis):
        # allow enough time for steps + rendering
        await vis.wait_done(timeout=300)


if __name__ == "__main__":
    asyncio.run(main())
    make_gif(FRAMES_DIR, "nqueens_run.gif", fps=2)