from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "spade-distributed.yml"
CHECKOUT_SHA = "11bd71901bbe5b1630ceea73d27597364c9af683"
UPLOAD_SHA = "ea165f8d65b6e75b540449e92b4886f43607fa02"
PYTHON_AMD64_DIGEST = (
    "sha256:eaeffb6e8511935426934aac863940fbd004ef31dab0d7fc27a129bb7c19d9a8"
)


def _workflow() -> tuple[str, dict[str, object]]:
    text = WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict)
    return text, parsed


def test_workflow_is_manual_only_read_only_and_source_sha_bound() -> None:
    text, workflow = _workflow()

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"phase", "source_sha", "confirmation"}
    assert inputs["phase"]["type"] == "choice"
    assert inputs["phase"]["options"] == ["development", "lockbox"]
    assert "EVENT_SHA: ${{ github.sha }}" in text
    assert "WORKFLOW_SHA: ${{ github.workflow_sha }}" in text
    assert '[[ "$EVENT_SHA" == "$SOURCE_SHA" ]]' in text
    assert '[[ "$WORKFLOW_SHA" == "$SOURCE_SHA" ]]' in text
    assert "invalid registered confirmation" in text
    assert "if" not in workflow["jobs"]["plan"]
    assert "git rev-parse HEAD" in text
    assert "git status --porcelain" in text
    assert "RUN_REGISTERED_DEVELOPMENT" in text
    assert "RUN_REGISTERED_LOCKBOX" in text
    assert "pull_request" not in workflow["on"]
    assert "push" not in workflow["on"]
    assert "schedule" not in workflow["on"]


def test_workflow_pins_every_action_and_linux_x64_python_image() -> None:
    text, workflow = _workflow()
    uses = re.findall(r"\buses:\s*([^\s#]+)", text)

    assert uses
    assert set(uses) == {
        f"actions/checkout@{CHECKOUT_SHA}",
        f"actions/upload-artifact@{UPLOAD_SHA}",
    }
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", item) for item in uses)
    for job in workflow["jobs"].values():
        assert job["container"] == f"python@{PYTHON_AMD64_DIGEST}"
    assert "Python 3.11.15" in text
    assert "x86_64" in text


def test_workflow_freezes_cpu_threads_and_runs_at_most_two_execs() -> None:
    text, workflow = _workflow()
    expected = {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
        "CUDA_VISIBLE_DEVICES": "",
    }
    assert workflow["env"] == expected
    run_job = workflow["jobs"]["run-shards"]
    assert run_job["strategy"]["max-parallel"] == "40"
    assert run_job["strategy"]["fail-fast"] == "false"
    assert run_job["strategy"]["matrix"] == "${{ fromJSON(needs.plan.outputs.matrix) }}"
    # One preflight plus four logical shard calls. The calls form two sequential
    # concurrent pairs; development disables the second pair.
    assert text.count("scripts/run_spade_actions_worker.py") == 5
    assert text.count(" &\n") == 4
    assert "torch.set_num_threads(1)" not in text  # enforced inside the tested wrapper
    execute = next(
        step for step in run_job["steps"] if step["name"].startswith("Execute packed")
    )
    assert execute["id"] == "execute"
    execute_script = execute["run"]
    for slot in ("A", "B", "C", "D"):
        assert execute_script.count(f'--family "${slot}_FAMILY"') == 1
        assert execute_script.count(f'--out "${slot}_OUT"') == 1
        assert f"record_completion {slot.lower()} " in execute_script
    assert execute_script.index('wait "$pid_a"') < execute_script.index('pid_c=""')
    assert execute_script.index('wait "$pid_b"') < execute_script.index('pid_c=""')
    assert execute_script.index('wait "$pid_c"') < execute_script.index('exit "$status"')
    assert execute_script.index('wait "$pid_d"') < execute_script.index('exit "$status"')


def test_workflow_uploads_complete_immutable_shard_contract_without_inspection() -> None:
    text, workflow = _workflow()
    run_job = workflow["jobs"]["run-shards"]
    upload_steps = [
        step
        for step in run_job["steps"]
        if step.get("uses") == f"actions/upload-artifact@{UPLOAD_SHA}"
    ]

    assert len(upload_steps) == 4
    for step in upload_steps:
        upload = step["with"]
        assert upload["if-no-files-found"] == "error"
        assert upload["overwrite"] == "false"
        assert upload["compression-level"] == "0"
        assert upload["retention-days"] == "90"
    assert [step.get("if") for step in upload_steps] == [
        "${{ always() && steps.execute.outputs.a_complete == 'true' }}",
        "${{ always() && steps.execute.outputs.b_complete == 'true' }}",
        "${{ always() && steps.execute.outputs.c_complete == 'true' }}",
        "${{ always() && steps.execute.outputs.d_complete == 'true' }}",
    ]
    paths = sum((step["with"]["path"].splitlines() for step in upload_steps), [])
    for slot in ("a", "b", "c", "d"):
        assert f"${{{{ matrix.{slot}_out }}}}" in paths
        assert f"${{{{ matrix.{slot}_out }}}}.sha256" in paths
        assert f"${{{{ matrix.{slot}_out }}}}.resume.json" in paths
        assert f"${{{{ matrix.{slot}_out }}}}.manifest.json" in paths
        assert sum(f"matrix.{slot}_out" in path for path in paths) == 4
    forbidden = (
        "analyse_spade",
        "select_spade",
        "merge_spade",
        "jq ",
        "cat results/",
    )
    assert not any(token in text for token in forbidden)


def test_workflow_matrix_is_generated_not_handwritten_and_capped_at_256() -> None:
    text, workflow = _workflow()
    plan_job = workflow["jobs"]["plan"]
    matrix_step = next(step for step in plan_job["steps"] if step.get("id") == "matrix")

    assert "scripts/make_spade_actions_matrix.py" in matrix_step["run"]
    assert "--expected-source-sha" in matrix_step["run"]
    assert "--batch-index 0" in matrix_step["run"]
    assert "--batch-size 256" in matrix_step["run"]
    assert "registered dispatch must contain exactly one complete matrix" in text
    assert workflow["jobs"]["run-shards"]["needs"] == "plan"
