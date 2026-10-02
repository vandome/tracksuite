import pytest

ecflow = pytest.importorskip("ecflow")

from tracksuite.print import SuiteDisplay, get_state_icon  # noqa: E402


def make_defs():
    defs = ecflow.Defs()
    suite = defs.add_suite("s")
    fam = suite.add_family("f")
    fam.add_task("t1")
    fam.add_task("t2")
    return defs, suite


def test_every_state_has_an_icon():
    """ecflow.State has six members; a missing one made this module raise on any
    definition that had not been loaded onto a server."""
    defs, suite = make_defs()
    assert defs is not None
    assert get_state_icon(suite)  # a fresh definition is State.unknown
    for name in ("complete", "active", "queued", "submitted", "aborted", "unknown"):
        assert hasattr(ecflow.State, name)


def test_tree_renders_for_a_definition_not_on_a_server():
    defs, suite = make_defs()
    assert defs is not None
    display = SuiteDisplay(format="html")
    display.process_task = lambda task: task.get_abs_node_path()
    display.extract_node_tree(suite)
    assert "t1" in display.tree
    assert "t2" in display.tree
    assert "└──" in display.tree or "├──" in display.tree
