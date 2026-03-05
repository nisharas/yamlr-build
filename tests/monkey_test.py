import sys
from pathlib import Path
import random
import string

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from yamlr.core.engine import YamlrEngine

def generate_garbage_yaml(depth=3):
    if depth == 0:
        return random.choice([
            "".join(random.choices(string.ascii_letters, k=10)),
            str(random.randint(0, 1000)),
            "true", "false", "null", "!!binary", "2026-02-13"
        ])
    
    lines = []
    for _ in range(random.randint(1, 5)):
        key = "".join(random.choices(string.ascii_letters, k=5))
        indent = "  " * (3 - depth)
        if random.random() > 0.3:
            lines.append(f"{indent}{key}: {generate_garbage_yaml(depth - 1)}")
        else:
            lines.append(f"{indent}- {generate_garbage_yaml(depth - 1)}")
    return "\n".join(lines)

def monkey_test():
    print("[MONKEY] Starting Monkey Test (Fuzzing)...")
    workspace = Path(__file__).parent.parent
    engine = YamlrEngine.quick(str(workspace))
    
    for i in range(50):
        garbage = generate_garbage_yaml(random.randint(1, 4))
        if random.random() > 0.8:
            # Inject some deliberate K8s-looking but broken stuff
            garbage += "\nkind: Deploymnet\nreppplicas: \"10\"\n"
            
        try:
            result = engine.audit_stream(garbage)
            print(f"Test {i+1}: Result={result.status} (Health={result.health_score})")
        except Exception as e:
            print(f"❌ Monkey Test FAILED at iteration {i+1} with input:\n{garbage}")
            print(f"Error: {e}")
            sys.exit(1)

    print("[MONKEY] Monkey Test PASSED (50 iterations)")

if __name__ == "__main__":
    monkey_test()
