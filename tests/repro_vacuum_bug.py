import unittest
from yamlr.core.stages.vacuum import StageTenVacuum
from yamlr.core.context import HealContext

class TestVacuumBug(unittest.TestCase):
    def test_block_scalar_protection(self):
        vacuum = StageTenVacuum(enabled=True)
        context = HealContext(
            file_path="test.yaml",
            raw_text="""
data: |
  line1

  line2
next: field
"""
        )
        vacuum.run(context)
        
        expected = """
data: |
  line1

  line2
next: field
"""
        # Vacuum should NOT remove the blank line between line1 and line2
        # because it is inside a block scalar.
        self.assertEqual(context.raw_text.strip(), expected.strip())

    def test_block_scalar_with_comment(self):
        vacuum = StageTenVacuum(enabled=True)
        context = HealContext(
            file_path="test.yaml",
            raw_text="""
data: | # Some comment
  line1

  line2
next: field
"""
        )
        vacuum.run(context)
        
        # If the regex is too strict, it might miss the block scalar start 
        # because of the comment, then purge the blank line.
        self.assertIn("\n\n", context.raw_text, "Blank line inside block scalar with comment was purged!")

    def test_block_scalar_with_whitespace_blank_line(self):
        vacuum = StageTenVacuum(enabled=True)
        # 2 spaces on the blank line
        context = HealContext(
            file_path="test.yaml",
            raw_text="""
data: |
  line1
  
  line2
"""
        )
        vacuum.run(context)
        self.assertIn("\n  \n", context.raw_text, "Indented blank line inside block scalar was purged!")

if __name__ == "__main__":
    unittest.main()
