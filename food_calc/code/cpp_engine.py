"""Optional native accelerator for the plan search.

The heavy Pareto search of ``alg._solve_frontier`` is ported to C++ and built
into a small shared library (``food_calc/native/engine.dll`` on Windows,
``libengine.so`` / ``libengine.dylib`` elsewhere, next to the C++ source).
This module loads it through ``ctypes`` and hands raw arrays back and forth.

When the library is missing or a task exceeds its limits, callers fall back
to the pure Python engine, so results are unchanged - only the speed differs.
All engine state lives on the C++ side inside one call, so concurrent calls
from the HTTP server are safe.
"""

import ctypes
from pathlib import Path

# Individual action kinds, mirroring the C++ Act kinds and the option order
# in alg._individual_options: first keep, then eat, then roast.
ACTION_KINDS = {"keep": 0, "eat": 1, "roast": 2}

_NATIVE_DIR = Path(__file__).resolve().parent.parent / "native"
_LIBRARY_NAMES = ("engine.dll", "libengine.so", "libengine.dylib")

_library = None
_engine = "Python"
_searched = False

_DOUBLE_P = ctypes.POINTER(ctypes.c_double)
_INT32_P = ctypes.POINTER(ctypes.c_int32)
_INT8_P = ctypes.POINTER(ctypes.c_int8)


def engine_name():
    """Return the engine powering the current plan search."""
    available()
    return _engine


def _bind(library):
    """Set the C prototype of ``dstmeta_solve``."""
    function = library.dstmeta_solve
    function.restype = ctypes.c_int32
    function.argtypes = [
        ctypes.c_int32,                # types
        _INT32_P,                      # type_counts
        _INT32_P,                      # ind_off
        _DOUBLE_P,                     # ind_stats
        _INT32_P,                      # ind_kind
        ctypes.c_int32,                # pot_count
        _INT32_P,                      # pot_keys
        _INT32_P,                      # pot_off
        _INT32_P,                      # pot_dish
        _DOUBLE_P,                     # pot_stats
        _INT8_P,                       # pot_cooked
        ctypes.c_int32,                # chosen_stat
        _DOUBLE_P,                     # losses
        _DOUBLE_P,                     # out_total
        _DOUBLE_P,                     # out_totals
        _INT32_P,                      # out_group_count
        _INT32_P,                      # out_groups
        ctypes.c_int32,                # groups_cap
        _INT8_P,                       # out_ind
    ]
    return function


def available():
    """Return True when the native engine is usable."""
    global _library, _engine, _searched
    if _searched:
        return _library is not None

    _searched = True
    for name in _LIBRARY_NAMES:
        path = _NATIVE_DIR / name
        if not path.exists():
            continue
        try:
            _library = _bind(ctypes.CDLL(str(path)))
            _engine = "C++"
            break
        except OSError:
            _library = None
            _engine = "Python"
    return _library is not None


def _pointer(sequence, ctype):
    """Return a ctypes pointer for ``sequence``, or ``None`` when empty."""
    array = (ctype * len(sequence))(*sequence)
    return array, ctypes.cast(array, ctypes.POINTER(ctype))


def solve(
    type_counts,
    ind_off,
    ind_stats,
    ind_kind,
    pot_keys,
    pot_off,
    pot_dish,
    pot_stats,
    pot_cooked,
    chosen_stat,
    losses,
):
    """Run one native search and return ``(total, totals, groups, individuals)``.

    ``groups`` is a list of ``(dish_id, t0, t1, t2, t3)`` cook groups and
    ``individuals`` maps each type to ``(keep, eat, roast)`` item counts.
    Returns ``None`` when the native engine reports an error; callers then
    use the Python engine.  Return code -3 (nothing feasible) is reported as
    ``("keep",)`` style output by the caller, like ``alg.find_best_plan``.
    """
    if not available() or not type_counts:
        return None

    types = len(type_counts)
    instance_count = sum(type_counts)
    groups_cap = instance_count // 4 + 1

    counts_arr, counts_p = _pointer(type_counts, ctypes.c_int32)
    ind_off_arr, ind_off_p = _pointer(ind_off, ctypes.c_int32)
    ind_stats_arr, ind_stats_p = _pointer(ind_stats, ctypes.c_double)
    ind_kind_arr, ind_kind_p = _pointer(ind_kind, ctypes.c_int32)
    pot_keys_arr, pot_keys_p = _pointer(pot_keys, ctypes.c_int32)
    pot_off_arr, pot_off_p = _pointer(pot_off, ctypes.c_int32)
    pot_dish_arr, pot_dish_p = _pointer(pot_dish, ctypes.c_int32)
    pot_stats_arr, pot_stats_p = _pointer(pot_stats, ctypes.c_double)
    pot_cooked_arr, pot_cooked_p = _pointer(pot_cooked, ctypes.c_int8)
    losses_arr, losses_p = _pointer(losses, ctypes.c_double)

    # The pointer objects returned by _pointer keep the arrays alive for the
    # duration of the call.
    total = ctypes.c_double()
    totals_arr = (ctypes.c_double * 3)()
    group_count = ctypes.c_int32()
    groups_arr = (ctypes.c_int32 * (groups_cap * 5))()
    individuals_arr = (ctypes.c_int8 * (types * 3))()

    code = _library(
        types,
        counts_p,
        ind_off_p,
        ind_stats_p,
        ind_kind_p,
        len(pot_off) - 1,
        pot_keys_p,
        pot_off_p,
        pot_dish_p,
        pot_stats_p,
        pot_cooked_p,
        chosen_stat,
        losses_p,
        ctypes.byref(total),
        totals_arr,
        ctypes.byref(group_count),
        groups_arr,
        groups_cap,
        individuals_arr,
    )

    if code != 0:
        # -1/-2 bad task, -3 nothing feasible: the Python engine reproduces
        # its own (unreachable) keep-everything fallback, so just re-run it.
        return None

    groups = []
    for g in range(group_count.value):
        base = g * 5
        groups.append(tuple(groups_arr[base:base + 5]))
    individuals = list(individuals_arr)
    return total.value, list(totals_arr), groups, individuals
