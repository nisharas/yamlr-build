import sys

from yamlr.core.context import HealContext
from yamlr.models import ManifestIdentity, Shard
from yamlr.parsers.structurer import YamlrStructurer


def debug_indentation():
    structurer = YamlrStructurer(catalog={}, validator=None)

    # Create some dummy shards for two documents
    shards1 = [
        Shard(line_no=1, indent=0, key="apiVersion", value="v1"),
        Shard(line_no=2, indent=0, key="metadata", value=None),
        Shard(line_no=3, indent=2, key="name", value="doc1"),
    ]

    shards2 = [
        Shard(line_no=5, indent=0, key="apiVersion", value="v1"),
        Shard(line_no=6, indent=0, key="metadata", value=None),
        Shard(line_no=7, indent=4, key="name", value="doc2"),
    ]

    # Mock context
    context = HealContext(raw_text="")
    context.identities = [ManifestIdentity(kind="Pod", name="doc1"), ManifestIdentity(kind="Pod", name="doc2")]
    context.shards = shards1 + [Shard(line_no=4, indent=0, key="---", value=None, is_doc_boundary=True)] + shards2

    print("Reconstructing...")
    docs = structurer.reconstruct(context)
    print(f"Reconstructed {len(docs)} docs")

    for i, doc in enumerate(docs):
        print(f"Doc {i + 1} indent_step: {getattr(doc, 'indent_step', 'N/A')}")

    print("Serializing...")
    content = structurer.serialize(docs)
    print("SERIALIZED CONTENT:")
    print(content)


if __name__ == "__main__":
    try:
        debug_indentation()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
