import pytest

from yamlr.cli.main import scrub_ansi


def test_scrub_ansi():
    """Verify ANSI escape sequence scrubbing."""
    colored_text = "\x1b[31mRed Text\x1b[0m"
    clean_text = scrub_ansi(colored_text)
    assert clean_text == "Red Text"
    
    mixed_text = "Normal \x1b[1;32mBold Green\x1b[m text"
    clean_mixed = scrub_ansi(mixed_text)
    assert clean_mixed == "Normal Bold Green text"
