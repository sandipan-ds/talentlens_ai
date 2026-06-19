from pathlib import Path

from src.resume_parsing.parser import parse_resume


def test_parse_resume_extracts_contact_and_name():
    sample_file = Path("data/original/BusinessAnalyst/01888170110d1ccf.pdf")
    profile = parse_resume(sample_file)

    assert profile["name"]["value"] == "John Wood"
    assert "+1-925-885-5155" in profile["contact"]["phones"]
    assert "help@enhancv.com" in profile["contact"]["emails"]
    assert profile["experience"]["entries"]
