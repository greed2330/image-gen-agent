import pytest
from pydantic import ValidationError

from app.models.schemas import (
    GenRequest,
    Intent,
    NsfwLevel,
    PipelineTrace,
    Resolution,
    WorkflowType,
)


def test_intent_defaults():
    i = Intent()
    assert i.nsfw_level == NsfwLevel.SAFE
    assert i.seed_tags == []


def test_intent_nsfw_levels():
    i = Intent(nsfw_level=NsfwLevel.EXPLICIT, identity_tags=["1girl"])
    assert i.nsfw_level == 2


def test_gen_request_requires_message():
    with pytest.raises(ValidationError):
        GenRequest(chat_id="room1")   # message missing


def test_pipeline_trace_record():
    import time
    trace = PipelineTrace()
    t = time.monotonic()
    trace.record("test_stage", {"in": 1}, {"out": 2}, t)
    assert len(trace.stages) == 1
    assert trace.stages[0].name == "test_stage"
    assert trace.stages[0].elapsed_ms >= 0


def test_pipeline_trace_dump_format():
    import time
    trace = PipelineTrace()
    trace.record("① intent", {"msg": "hello"}, {"tags": ["1girl"]}, time.monotonic())
    dump = trace.dump()
    assert "① intent" in dump
    assert "hello" in dump
