#!/usr/bin/env python3
"""
Performance Narrative Visualizer (VAL-02-7)
-------------------------------------------
Generates a marketing-grade "Performance Narrative" graph using matplotlib.
Style: Neon-Blue / Dark Mode (Vibe Coding).
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def generate_graph():
    history_path = Path("stress_history.json")
    output_path = Path("docs/perf_narrative.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not history_path.exists():
        print(f"Error: {history_path} not found.")
        return

    with open(history_path, "r") as f:
        data = json.load(f)

    # Sort data by total_files to ensure a clean line
    data = sorted(data, key=lambda x: x["total_files"])

    x = [d["total_files"] for d in data]
    y_throughput = [d["files_per_sec"] for d in data]
    y_memory = [d["peak_mem_gb"] for d in data]

    # Style: Vibe Coding Dark Mode
    plt.style.use("dark_background")
    fig, ax1 = plt.subplots(figsize=(12, 7))

    # Background color customization
    fig.patch.set_facecolor("#0B0E14")
    ax1.set_facecolor("#0B0E14")

    # Throughput Axis
    color_tp = "#00D9FF"  # Neon Cyber Blue
    lns1 = ax1.plot(
        x,
        y_throughput,
        marker="o",
        linewidth=3,
        markersize=8,
        color=color_tp,
        label="Throughput (Files/sec)",
        alpha=0.9,
    )

    ax1.set_xlabel("Scale (Total Manifests)", fontsize=12, labelpad=15, color="#8B949E")
    ax1.set_ylabel("Efficiency (Files/sec)", fontsize=12, labelpad=15, color=color_tp)
    ax1.tick_params(axis="y", labelcolor=color_tp)

    # Use comma formatting for counts
    ax1.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ",")))
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ",")))

    # Memory Axis (Stability)
    ax2 = ax1.twinx()
    color_mem = "#FF007A"  # Neon Pink
    lns2 = ax2.step(
        x, y_memory, where="post", color=color_mem, linestyle="--", linewidth=2, label="Peak Memory (GB)", alpha=0.6
    )

    ax2.set_ylabel("Peak RAM (GB)", fontsize=12, labelpad=15, color=color_mem)
    ax2.tick_params(axis="y", labelcolor=color_mem)
    ax2.set_ylim(0, 1.5)  # Hard requirement limit

    # Formatting
    plt.title(
        "YAMLR Performance Narrative: Scalability Proof (VAL-02-7)",
        fontsize=16,
        pad=30,
        fontweight="bold",
        color="#FFFFFF",
    )

    # Legend
    lns = lns1 + lns2
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc="upper left", frameon=False, fontsize=10)

    # Grid
    ax1.grid(True, linestyle=":", alpha=0.1, color="#FFFFFF")

    # Annotations
    if len(x) > 1:
        # Surgical Efficiency Knee
        knee_idx = 1  # Where slope stays high
        ax1.annotate(
            "Amortization Threshold",
            xy=(x[knee_idx], y_throughput[knee_idx]),
            xytext=(x[knee_idx] + 5000, y_throughput[knee_idx] - 2000),
            arrowprops=dict(facecolor="#8B949E", shrink=0.05, width=1, headwidth=5),
            fontsize=10,
            color="#8B949E",
        )

        # Hyperscale Proof point
        last_idx = -1
        ax1.annotate(
            f"Hyperscale Proof: {y_throughput[last_idx]:,.0f} files/sec",
            xy=(x[last_idx], y_throughput[last_idx]),
            xytext=(x[last_idx] - 25000, y_throughput[last_idx] + 1000),
            fontsize=11,
            color="#FFFFFF",
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor="#0B0E14")
    print(f"✅ Performance Graph Generated: {output_path}")


if __name__ == "__main__":
    generate_graph()
