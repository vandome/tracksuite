import pytest

ecflow = pytest.importorskip("ecflow")

from tracksuite.ecflow_client import (  # noqa: E402
    ATTRIBUTE_SETTERS,
    DEFAULT_SYNC_ATTRIBUTES,
    EcflowClient,
)


class RecordingClient:
    """Stands in for a connected EcflowClient.

    update_node_attributes only reaches the server through the single-attribute
    setters, so recording those is enough to assert what a sync would write, without
    a live ecflow server.
    """

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if not name.startswith("set_"):
            raise AttributeError(name)

        def record(node_path, key, value):
            self.calls.append((name, key, value))

        return record


def make_task(label, expver):
    defs = ecflow.Defs()
    task = defs.add_suite("s").add_task("t")
    task.add_label("info", label)
    task.add_variable("PGEN_EXPVER", expver)
    task.add_event("done")
    # the Defs owns the node; returning both keeps it alive
    return defs, task


def test_attribute_setters_cover_the_default_collections():
    """Every collection synchronised by default must have a setter to write it.

    replace_on_server names collections in the plural, as ecflow exposes them, while
    the client exposes singular setters. Nothing derives one from the other, so this
    asserts the map is complete rather than trusting a naming convention.
    """
    for collection in (*DEFAULT_SYNC_ATTRIBUTES, "variables"):
        assert collection in ATTRIBUTE_SETTERS
        setter_name, _cast = ATTRIBUTE_SETTERS[collection]
        assert hasattr(
            EcflowClient, setter_name
        ), f"{collection} maps to {setter_name}, which EcflowClient does not define"


def test_differing_attribute_is_written_back():
    old_defs, old = make_task("running step 120", "0001")
    new_defs, new = make_task("", "9001")
    assert old_defs and new_defs

    client = RecordingClient()
    EcflowClient.update_node_attributes(client, new, old, list(DEFAULT_SYNC_ATTRIBUTES))

    assert ("set_label", "info", "running step 120") in client.calls


def test_variables_are_only_synchronised_when_asked():
    old_defs, old = make_task("same", "0001")
    new_defs, new = make_task("same", "9001")
    assert old_defs and new_defs

    without = RecordingClient()
    EcflowClient.update_node_attributes(
        without, new, old, list(DEFAULT_SYNC_ATTRIBUTES)
    )
    assert without.calls == []

    with_vars = RecordingClient()
    EcflowClient.update_node_attributes(
        with_vars, new, old, [*DEFAULT_SYNC_ATTRIBUTES, "variables"]
    )
    assert ("set_variable", "PGEN_EXPVER", "0001") in with_vars.calls


def test_identical_attributes_are_left_alone():
    old_defs, old = make_task("same", "0001")
    new_defs, new = make_task("same", "0001")
    assert old_defs and new_defs

    client = RecordingClient()
    EcflowClient.update_node_attributes(
        client, new, old, [*DEFAULT_SYNC_ATTRIBUTES, "variables"]
    )
    assert client.calls == []


def test_unknown_collection_is_skipped_not_fatal():
    """A sync must not abort the walk over a collection it cannot write.

    replace_on_server applies the new definition BEFORE synchronising, so raising
    here would leave the suite replaced with its live state only half restored.
    """
    old_defs, old = make_task("a", "0001")
    new_defs, new = make_task("b", "9001")
    assert old_defs and new_defs

    client = RecordingClient()
    EcflowClient.update_node_attributes(client, new, old, ["limits"])
    assert client.calls == []


def test_meter_value_is_coerced_for_its_setter():
    """meter.value() is an int; set_meter reaches client.alter, which needs a str."""
    _setter, cast = ATTRIBUTE_SETTERS["meters"]
    assert cast(120) == "120"

    _setter, cast = ATTRIBUTE_SETTERS["events"]
    assert cast(True) is True
