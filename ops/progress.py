"""Shared live-progress plumbing for AssetDoctor's modal operators.

One set of WindowManager props (`assetdoctor_op_active/_progress/_status`,
registered in the package ``register()``) backs a single progress bar drawn at
the top of the N-panel. Any modal operator (F1 folder scan, F2 make-local, …)
calls :func:`set_progress` per timer tick to drive it, and :func:`clear_progress`
when it finishes or cancels.

:class:`ModalProgressMixin` packages the whole pattern: a subclass provides a
``run_steps(context)`` generator that yields ``(fraction, status)`` as it works;
the mixin runs it modally (progress bar + ESC) or synchronously via ``execute``.
"""

from __future__ import annotations

import time


def set_progress(context, fraction: float = 0.0, status: str = "") -> None:
    """Show/update the shared progress bar and repaint the sidebar."""
    wm = context.window_manager
    wm.assetdoctor_op_active = True
    wm.assetdoctor_op_progress = max(0.0, min(1.0, fraction))
    wm.assetdoctor_op_status = status
    if context.area is not None:
        context.area.tag_redraw()


def clear_progress(context) -> None:
    """Hide the shared progress bar."""
    wm = context.window_manager
    wm.assetdoctor_op_active = False
    wm.assetdoctor_op_progress = 0.0
    wm.assetdoctor_op_status = ""
    if context.area is not None:
        context.area.tag_redraw()


class ModalProgressMixin:
    """Run ``self.run_steps(context)`` as a modal operator with the shared
    progress bar + ESC cancel, or synchronously via ``execute``.

    Subclasses implement ``run_steps(context)`` as a generator that yields
    ``(fraction, status)`` while it works and performs all side effects itself
    (build/stash the report, apply mutations, and the final ``self.report(...)``).

    The modal pulls as many steps as fit in a per-tick **time budget**, so fast
    per-item work (e.g. fingerprinting) still finishes near-instantly while the UI
    stays responsive and ESC stays live; a single slow step (e.g. one make-local)
    naturally becomes one step per tick. ``execute`` just drains the generator,
    which keeps the EXEC_DEFAULT / scripting / headless-test path synchronous.
    """

    # Seconds of work to do per timer tick before yielding back to Blender.
    _PROGRESS_BUDGET = 0.04

    _timer = None
    _gen = None

    def run_steps(self, context):  # pragma: no cover - subclass responsibility
        raise NotImplementedError
        yield  # noqa: F811 - marks this as a generator for subclasses

    def cancel_message(self) -> str:
        return f"{self.bl_label} cancelled"

    def execute(self, context):
        for _ in self.run_steps(context):
            pass
        return {"FINISHED"}

    def invoke(self, context, event):
        self._gen = self.run_steps(context)
        wm = context.window_manager
        wm.progress_begin(0, 100)
        set_progress(context, 0.0, "Starting…")
        context.workspace.status_text_set(f"AssetDoctor: {self.bl_label}… (ESC to cancel)")
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC":
            self._teardown(context)
            self.report({"WARNING"}, self.cancel_message())
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        latest = None
        start = time.perf_counter()
        try:
            while True:
                latest = next(self._gen)
                if time.perf_counter() - start >= self._PROGRESS_BUDGET:
                    break
        except StopIteration:
            self._teardown(context)
            return {"FINISHED"}

        fraction, status = latest
        context.window_manager.progress_update(int(fraction * 100))
        set_progress(context, fraction, status)
        return {"RUNNING_MODAL"}

    def _teardown(self, context):
        wm = context.window_manager
        if self._timer is not None:
            wm.event_timer_remove(self._timer)
            self._timer = None
        wm.progress_end()
        clear_progress(context)
        context.workspace.status_text_set(None)
