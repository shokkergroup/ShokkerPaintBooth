from __future__ import annotations

import hashlib
from pathlib import Path

from _forge_semantic_instance_compiler_boundary import (
    create_compiler_job,
    create_synthetic_semantic_case,
    evaluate_compiler_boundary,
)


def test_embedded_semantic_qa_path_remains_hash_resolvable(tmp_path: Path) -> None:
    semantic_job, lineage = create_synthetic_semantic_case(tmp_path / "inputs", "valid_split")
    compiler_job = create_compiler_job(tmp_path / "compiler_job.json", semantic_job, lineage)
    output = tmp_path / "output"

    result = evaluate_compiler_boundary(compiler_job, output)
    qa_record = result["semantic_gate_report"]["qa_visual"]
    recorded = Path(qa_record["path"])
    resolved = recorded if recorded.is_absolute() else output / recorded

    assert resolved.is_file()
    assert hashlib.sha256(resolved.read_bytes()).hexdigest() == qa_record["sha256"]
