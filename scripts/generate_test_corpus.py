import os
import random
from pathlib import Path

# Targeted corruption patterns
PATTERNS = [
    # Indentation
    lambda s: s.replace("  ", "   "),  # 3-space conversion
    lambda s: s.replace("  ", "\t"),  # Tab conversion
    lambda s: s.lstrip(),  # Flush-left
    lambda s: " " + s,  # Odd offset
    # Punctuation
    lambda s: s.replace(":", ""),  # Missing colon
    lambda s: s.replace(": ", ":"),  # Fused value
    lambda s: s.replace('"', ""),  # Missing quotes
    lambda s: s + '"' if '"' in s else s,  # Unbalanced quotes
    # List corruption
    lambda s: s.replace("- ", "-"),  # Fused dash
    lambda s: s.replace("  - ", "- "),  # Flush-left list item
    # Combined
    lambda s: s.lstrip().replace(":", ""),  # Flush-left + missing colon
]

BASE_YAML = """
apiVersion: v1
kind: Service
metadata:
  name: test-service
  namespace: default
  labels:
    app: test
spec:
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
  selector:
    app: test
  type: ClusterIP
"""


def generate():
    root_dir = Path(__file__).parent.parent.resolve()
    corpus_dir = root_dir / "tests/corpus/toxic"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    lines = BASE_YAML.strip().split("\n")

    for i in range(110):
        corrupted_lines = []
        # Choose 2-3 lines to corrupt randomly
        to_corrupt = random.sample(range(len(lines)), k=random.randint(2, 4))

        for idx, line in enumerate(lines):
            if idx in to_corrupt:
                pattern = random.choice(PATTERNS)
                corrupted_lines.append(pattern(line))
            else:
                corrupted_lines.append(line)

        file_path = corpus_dir / f"toxic_{i:03d}.yaml"
        file_path.write_text("\n".join(corrupted_lines), encoding="utf-8")

    print(f"Generated 110 toxic files in {corpus_dir}")


if __name__ == "__main__":
    generate()
