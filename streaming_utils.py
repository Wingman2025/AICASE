import inspect
from typing import Callable, Iterable, Tuple, Any, List

from agents import Runner

async def run_streamed_collect(agent: Any, input: Iterable, on_event: Callable[[Any], None] | None = None) -> Tuple[Any, List[Any]]:
    """Run an agent in streaming mode collecting events.

    Parameters
    ----------
    agent : Any
        Agent to execute.
    input : Iterable
        Input sequence for the agent.
    on_event : Callable[[Any], None] | None, optional
        Optional callback executed for each streaming event as it arrives.

    Returns
    -------
    Tuple[Any, List[Any]]
        Runner result object and list of collected events.
    """
    run_streamed = Runner.run_streamed
    events: List[Any] = []
    try:
        if inspect.iscoroutinefunction(run_streamed):
            result = await run_streamed(agent, input=input)
        else:
            result = run_streamed(agent, input=input)

        async for event in result.stream_events():
            if on_event:
                try:
                    on_event(event)
                except Exception:
                    pass
            events.append(event)
        return result, events
    except Exception:
        raise


