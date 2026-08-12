import logging
from pathlib import Path

import structlog

from usural_prospect_finder.utils.logging import configure_logging


def test_structured_file_logging_creates_directory_and_context(tmp_path: Path) -> None:
    log_dir = tmp_path / "nested" / "logs"
    configure_logging("INFO", log_dir)
    structlog.get_logger().info(
        "audit_completed", domain="example.com", audit_id="audit-1", duration_ms=12
    )
    for handler in logging.getLogger().handlers:
        handler.flush()
    content = (log_dir / "prospect-finder.log").read_text(encoding="utf-8")
    assert '"domain": "example.com"' in content
    assert '"audit_id": "audit-1"' in content
