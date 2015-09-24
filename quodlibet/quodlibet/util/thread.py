# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Utils for executing things in a thread controlled from the main loop"""

from multiprocessing.pool import ThreadPool

from gi.repository import GLib

from quodlibet import util


@util.enum
class Priority(int):
    HIGH = 0
    BACKGROUND = 1


class Cancellable(object):
    """Subset of Gio.Cancellable so it can be used as well"""

    def __init__(self):
        self._cancelled = False

    def is_cancelled(self):
        return self._cancelled

    def reset(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True


_pools = {}
_prio_mapping = {
    Priority.HIGH: GLib.PRIORITY_DEFAULT,
    Priority.BACKGROUND: GLib.PRIORITY_LOW,
}


def _get_pool(priority):
    """Return a (shared) pool for a given priority"""

    global _pools

    if not priority in _pools:
        _pools[priority] = ThreadPool()
    return _pools[priority]


def _wrap_function(function, cancellable, args, kwargs):

    def wrap():
        # check once we are scheduled
        if not cancellable.is_cancelled():
            try:
                return function(*args, **kwargs)
            except:
                # ThreadPool catches the exception for the async result
                # which we don't use. Print instead as if it was not catched.
                util.print_exc()
                raise

    return wrap


def _wrap_callback(priority, cancellable, callback):

    def callback_main(cancellable, callback, result):
        if not cancellable.is_cancelled():
            callback(result)
        return False

    def callback_thread(result):
        global _prio_mapping

        if not cancellable.is_cancelled():
            glib_priority = _prio_mapping[priority]
            GLib.idle_add(callback_main, cancellable, callback, result,
                          priority=glib_priority)

    return callback_thread


def _call_async(priority, function, cancellable, callback, args, kwargs):
    assert cancellable is not None
    assert function is not None
    assert callback is not None

    if args is None:
        args = tuple()
    if kwargs is None:
        kwargs = {}

    pool = _get_pool(priority)
    wrapped_func = _wrap_function(function, cancellable, args, kwargs)
    wrapped_callback = _wrap_callback(priority, cancellable, callback)
    pool.apply_async(wrapped_func, callback=wrapped_callback)


def terminate_all():
    """Terminate all pools, doesn't wait for task completion.

    Can be called multiple times and call_async() etc. can still be used.
    """

    global _pools

    for key, pool in _pools.items():
        del _pools[key]
        pool.terminate()


def call_async(function, cancellable, callback, args=None, kwargs=None):
    """Call `function` in a thread that gets passed the `cancellable`
    and the passed args/kwargs.

    The return value will get passed to `callback` which will be called
    in the main thread. It will not be called if the `cancellable` gets
    cancelled and is not guaranteed to be called at all (on event loop
    shutdown for example)
    """

    _call_async(Priority.HIGH, function, cancellable, callback, args, kwargs)


def call_async_background(function, cancellable, callback, args=None,
                          kwargs=None):
    """Same as call_async but for background tasks (network etc.)"""

    _call_async(Priority.BACKGROUND, function, cancellable, callback,
                args, kwargs)
