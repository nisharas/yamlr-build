import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from scripts.simulate_hyperscale import (
    BASE_DIR,
    generate_amazon_cluster,
    generate_google_cluster,
    generate_netflix_cluster,
)


def run_ultra_gen(count_per_style=2000):
    if BASE_DIR.exists():
        import shutil

        shutil.rmtree(BASE_DIR)

    generate_google_cluster(count_per_style)
    generate_amazon_cluster(count_per_style)
    generate_netflix_cluster(count_per_style)
    print(f"\nUltra-Scale Simulation Corpus Generated ({count_per_style * 3} files).")


if __name__ == "__main__":
    run_ultra_gen(2000)
