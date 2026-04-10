from yamlr.core.utils import get_hardened_yaml


def debug_parse():
    val = "{app: nginx, env: prod}"
    hyaml = get_hardened_yaml(typ="safe")
    parsed = hyaml.load(val)
    print(f"VAL: {val}")
    print(f"PARSED: {parsed}")
    print(f"TYPE: {type(parsed)}")

    val2 = "[Ingress, Egress]"
    parsed2 = hyaml.load(val2)
    print(f"VAL2: {val2}")
    print(f"PARSED2: {parsed2}")
    print(f"TYPE2: {type(parsed2)}")


if __name__ == "__main__":
    debug_parse()
