from pathlib import Path
from modelinfo.change_log import ChangeLogManager, ErrorTracker

def test_write_change_log_creates_file(tmp_path):
    cl = ChangeLogManager(log_dir=str(tmp_path))
    from modelinfo.models import ChangeRecord
    changes = [
        ChangeRecord(table_name="pricing", model_id="openai/gpt-4o",
                     field_name="input_price_per_1m", old_value="2.5", new_value="2.0",
                     source_url="https://example.com")
    ]
    cl.write(changes, source_name="openrouter")
    log_file = tmp_path / "change_log.md"
    assert log_file.exists()
    content = log_file.read_text()
    assert "openai/gpt-4o" in content
    assert "2.5" in content
    assert "2.0" in content

def test_error_tracker_logs_and_retrieves(tmp_path):
    et = ErrorTracker(error_dir=str(tmp_path))
    et.log_error("openai", "https://openai.com/pricing", "ParseError: table not found")
    errors = et.get_recent_errors()
    assert len(errors) == 1
    assert errors[0]["source"] == "openai"

def test_error_tracker_triggers_issue_on_3x(tmp_path):
    et = ErrorTracker(error_dir=str(tmp_path))
    for i in range(3):
        et.log_error("openai", "https://openai.com/pricing", "ParseError")
    assert et.should_create_issue("openai") is True

def test_error_tracker_no_issue_on_2x(tmp_path):
    et = ErrorTracker(error_dir=str(tmp_path))
    et.log_error("openai", "https://openai.com/pricing", "ParseError")
    et.log_error("openai", "https://openai.com/pricing", "ParseError")
    assert et.should_create_issue("openai") is False
