# nqueens_visualizer_agent.py
# A plug‑in VisualizerAgent for your n‑Queens Mango projects.
# It listens for {type:"SET_ROWS", rows:[...], step:int} and renders a PNG frame per step.
#
# Usage (example):
#   from nqueens_visualizer_agent import VisualizerAgent
#   vis = VisualizerAgent(board_size=N, out_dir="frames_llm")
#   ... add vis as a node in your mango topology and connect coordinator -> visualizer
#   The coordinator can reuse the same SET_ROWS broadcast it sends to queens.
#
# Requirements:
#   pip install matplotlib

import os
import asyncio
from typing import List

import matplotlib
matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import mango


class VisualizerAgent(mango.Agent):
    def __init__(self, board_size: int, out_dir: str = "frames", annotate_conflicts: bool = True):
        super().__init__()
        self.n = board_size
        self.out_dir = out_dir
        self.annotate_conflicts = annotate_conflicts
        self.last_step = -1
        os.makedirs(self.out_dir, exist_ok=True)
        self._done = asyncio.Event()

    def handle_message(self, content, meta):
        t = content.get("type")
        if t == "SET_ROWS":
            rows: List[int] = content["rows"]
            step = int(content.get("step", 0))
            self.last_step = step
            self._render_frame(rows, step)
        elif t == "DONE":
            self._done.set()

    async def wait_done(self, timeout: float = 0):
        if timeout > 0:
            try:
                await asyncio.wait_for(self._done.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
        else:
            await self._done.wait()

    # ---------- Rendering ----------
    def _render_frame(self, rows: List[int], step: int):
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.set_xlim(0, self.n)
        ax.set_ylim(0, self.n)
        ax.set_xticks(range(self.n))
        ax.set_yticks(range(self.n))
        ax.set_aspect('equal')
        ax.grid(True, which='both')
        ax.invert_yaxis()
        ax.set_title(f"n-Queens step {step}")

        # draw board squares
        for i in range(self.n):
            for j in range(self.n):
                if (i + j) % 2 == 0:
                    # leave default background for one color
                    pass
                else:
                    ax.add_patch(Rectangle((i, j), 1, 1, alpha=0.1))

        # draw queens and optional conflict markers
        conflicts = 0
        for c, r in enumerate(rows):
            ax.text(c + 0.5, r + 0.6, "♛", ha='center', va='center', fontsize=18)
        # compute conflicts for annotation
        if self.annotate_conflicts:
            for i in range(self.n):
                for j in range(i + 1, self.n):
                    if rows[i] == rows[j] or abs(rows[i] - rows[j]) == abs(i - j):
                        conflicts += 1
            ax.text(0.02, 0.98, f"conflicts: {conflicts}", transform=ax.transAxes, va='top')

        frame_path = os.path.join(self.out_dir, f"step_{step:03d}.png")
        plt.tight_layout()
        fig.savefig(frame_path, dpi=140)
        plt.close(fig)
        print(f"[Visualizer] wrote {frame_path}")


# ---------- Convenience: simple stitch to GIF (optional) ----------
# Call from your script after run ends if you have imageio installed.

def make_gif(out_dir: str, gif_path: str, fps: int = 2):
    try:
        import imageio
    except ImportError:
        print("imageio not installed; skipping GIF export.")
        return
    frames = []
    files = sorted([f for f in os.listdir(out_dir) if f.endswith('.png')])
    for f in files:
        frames.append(imageio.v2.imread(os.path.join(out_dir, f)))
    if frames:
        imageio.mimsave(gif_path, frames, fps=fps)
        print(f"[Visualizer] GIF saved to {gif_path}")
    else:
        print("[Visualizer] no frames found; GIF not created.")
