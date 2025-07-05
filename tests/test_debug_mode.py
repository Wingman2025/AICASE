import os
import sys
import types
import asyncio
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'agents'))
from agents.stream_events import RunItemStreamEvent, RawResponsesStreamEvent
import chatbot

class DummyResult:
    def __init__(self, events):
        self.events = events
        self.final_output = "done"
    async def stream_events(self):
        for ev in self.events:
            yield ev

def test_process_user_message_debug(monkeypatch):
    events = [
        RunItemStreamEvent(name="tool_called", item="t1"),
        RawResponsesStreamEvent(data="raw")
    ]

    async def fake_run_streamed(*args, **kwargs):
        return DummyResult(events)

    monkeypatch.setattr(chatbot.Runner, "run_streamed", fake_run_streamed)

    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    chatbot.db_utils.IS_RAILWAY = 'DATABASE_URL' in os.environ

    class DummyApp:
        def callback(self, *args, **kwargs):
            def wrapper(func):
                return func
            return wrapper

    process_msg, _ = chatbot.register_callbacks(DummyApp())

    monkeypatch.setattr(chatbot, 'current_user', types.SimpleNamespace(is_authenticated=False))
    monkeypatch.setattr(chatbot.dash, "callback_context", types.SimpleNamespace(triggered=[{"prop_id": "send-button.n_clicks"}]))

    chat_history, _, conv_data, _ = process_msg(1, None, {}, {"session_id": "s1"}, "hello", {"messages": [], "session_id": "s1"}, True)

    debug_msgs = [m for m in conv_data["messages"] if m["role"] == "debug"]
    assert len(debug_msgs) == 2


def test_forecast_plan_debug(monkeypatch):
    events = [RunItemStreamEvent(name="tool_called", item="d1")]

    async def fake_orchestrate(question, debug=False):
        assert debug is True
        return "ok", events

    monkeypatch.setattr(chatbot, "orchestrate_forecast_to_plan", fake_orchestrate)

    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    chatbot.db_utils.IS_RAILWAY = 'DATABASE_URL' in os.environ

    class DummyApp:
        def callback(self, *args, **kwargs):
            def wrapper(func):
                return func
            return wrapper

    process_msg, _ = chatbot.register_callbacks(DummyApp())

    monkeypatch.setattr(chatbot, 'current_user', types.SimpleNamespace(is_authenticated=False))
    monkeypatch.setattr(chatbot.dash, "callback_context", types.SimpleNamespace(triggered=[{"prop_id": "send-button.n_clicks"}]))

    chat_history, _, conv_data, _ = process_msg(
        1,
        None,
        {},
        {"session_id": "s1"},
        "/forecast-plan: hi",
        {"messages": [], "session_id": "s1"},
        True,
    )

    debug_msgs = [m for m in conv_data["messages"] if m["role"] == "debug"]
    assert len(debug_msgs) == 1
