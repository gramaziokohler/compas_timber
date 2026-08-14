import pytest
from synthetic import stack
from synthetic import three_way_interlock

from assembly_sequencing import generate
from assembly_sequencing import get_tracer
from assembly_sequencing import set_tracer
from assembly_sequencing import trace
from assembly_sequencing import tracing


@pytest.fixture(autouse=True)
def tracer_off():
    """No test may leak a tracer into another."""
    previous = set_tracer(None)
    yield
    set_tracer(previous)


def test_tracing_is_off_by_default():
    assert tracing() is False
    assert get_tracer() is None
    trace("this goes nowhere")


def test_library_code_is_silent_unless_asked(capsys):
    generate(stack())
    assert capsys.readouterr().out == ""


def test_a_callable_collects_messages():
    # The Grasshopper pattern: wire the list to a panel.
    lines = []
    set_tracer(lines.append)
    generate(stack())
    assert lines
    assert any("sequencing 3 elements" in line for line in lines)


def test_true_installs_print(capsys):
    set_tracer(True)
    trace("hello")
    assert capsys.readouterr().out == "hello\n"


def test_set_tracer_returns_the_previous_one():
    first = []
    assert set_tracer(first.append) is None
    second = []
    assert set_tracer(second.append) == first.append
    assert set_tracer(None) == second.append


def test_false_and_none_both_disable():
    set_tracer(print)
    set_tracer(False)
    assert tracing() is False
    set_tracer(print)
    set_tracer(None)
    assert tracing() is False


def test_a_non_callable_raises():
    with pytest.raises(TypeError):
        set_tracer("verbose")


def test_the_trace_names_every_step_and_the_element_removed():
    lines = []
    set_tracer(lines.append)
    generate(stack())
    steps = [line for line in lines if line.startswith("step")]
    assert len(steps) == 3
    assert "removed top" in steps[0]
    assert "complete: 3 elements sequenced" in lines[-1]


def test_a_dead_end_is_traced_with_a_reason_per_element():
    lines = []
    set_tracer(lines.append)
    generate(three_way_interlock())
    assert any("DEAD END" in line for line in lines)
    assert any("alpha" in line and "1-DOF" in line for line in lines)


def test_the_trace_says_whether_the_geometry_check_ran():
    lines = []
    set_tracer(lines.append)
    generate(stack())
    assert any("geometry check OFF" in line for line in lines)
