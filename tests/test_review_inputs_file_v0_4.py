"""Declarative input files cannot become executable plans or weaken source gates."""
import hashlib
import json

import pytest

from epah_diagnosis import review_workflow_v0_4 as workflow
from test_review_workflow_v0_4 import setup, successful_runner


def configuration(tmp_path):
    root, inputs, target = setup(tmp_path)
    path = tmp_path / "inputs.json"
    values = {name: str(getattr(inputs, name).relative_to(tmp_path))
              for name in inputs.__dataclass_fields__ if getattr(inputs, name) is not None}
    document = {"schema_version": "0.4-review-inputs-1", "inputs": values}
    path.write_text(json.dumps(document), encoding="utf-8")
    return root, inputs, target, path, document


def test_relative_paths_and_configuration_hash_are_bound_to_the_run(tmp_path):
    root, inputs, target, path, _ = configuration(tmp_path)
    loaded, binding = workflow.load_inputs_file(path)
    assert loaded == inputs
    assert binding["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = workflow.run(loaded, target, root=root, input_configuration=binding,
                           runner=successful_runner(target))
    assert receipt["plan"]["input_configuration"] == binding
    assert json.loads((target / "run.json").read_text())["plan"]["input_configuration"] == binding


@pytest.mark.parametrize("change", [
    lambda doc: doc.update(steps=[{"command": ["arbitrary"]}]),
    lambda doc: doc.update(allow_incomplete=True),
    lambda doc: doc["inputs"].update(command="arbitrary"),
    lambda doc: doc["inputs"].pop("registry"),
    lambda doc: doc["inputs"].update(bundle=None),
])
def test_unknown_policy_commands_and_incomplete_contracts_are_rejected(tmp_path, change):
    _, _, target, path, document = configuration(tmp_path)
    change(document)
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        workflow.load_inputs_file(path)
    assert not target.exists()


def test_duplicate_keys_are_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"schema_version":"0.4-review-inputs-1","inputs":{},"inputs":{}}')
    with pytest.raises(ValueError, match="Duplicate"):
        workflow.load_inputs_file(path)


def test_input_file_still_requires_explicit_incomplete_option_and_existing_sources(tmp_path):
    root, _, target, path, document = configuration(tmp_path)
    document["inputs"].pop("housing_dir")
    path.write_text(json.dumps(document))
    loaded, _ = workflow.load_inputs_file(path)
    assert workflow.make_plan(loaded, target, root=root)["can_run"] is False
    with pytest.raises(ValueError, match="Incomplete inputs"):
        workflow.run(loaded, target, root=root)
    document["inputs"]["bundle"] = "not-acquired"
    path.write_text(json.dumps(document))
    loaded, _ = workflow.load_inputs_file(path)
    with pytest.raises(ValueError, match="Missing local input"):
        workflow.make_plan(loaded, target, root=root, allow_incomplete=True)
    assert not target.exists()


def test_cli_input_file_delegates_to_existing_plan_and_rejects_mixed_options(tmp_path, monkeypatch, capsys):
    root, _, target, path, _ = configuration(tmp_path)
    monkeypatch.setattr(workflow, "ROOT", root)
    original = workflow.make_plan
    monkeypatch.setattr(workflow, "make_plan", lambda inputs, out, **kw: original(inputs, out, root=root, **kw))
    assert workflow.main(["plan", "--inputs-file", str(path), "--out-dir", str(target)]) == 0
    assert "input_configuration" in capsys.readouterr().out
    assert not target.exists()
    with pytest.raises(SystemExit) as result:
        workflow.main(["plan", "--inputs-file", str(path), "--registry", "other.csv", "--out-dir", str(target)])
    assert result.value.code == 2
