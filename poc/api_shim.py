"""Misconception shim for LLM-written OR-Tools code (solution arm for the CO solver-API failures).
SHIM is Python source prepended to the program before execution. It makes the library tolerant of the misuse
patterns observed in the 8B/32B probes, and logs each use as `#SHIM:<name>` on stderr:
  add_iter     : CpModel.Add/add(<generator or list of constraints>) -> add each one
  register_cb  : RoutingModel.SetArcCostEvaluatorOfAllVehicles(<python function>) -> register it first
  params_alias : routing_enums_pb2.RoutingSearchParameters / SearchParameters() -> DefaultRoutingSearchParameters()
"""
SHIM = r'''
def _llm_shim():
    import sys, types
    def _log(n): print("#SHIM:" + n, file=sys.stderr)
    try:
        from ortools.sat.python import cp_model as _cm
        _orig_add = _cm.CpModel.add
        def _add(self, ct, *a, **k):
            if isinstance(ct, (types.GeneratorType, list, tuple)):
                _log("add_iter")
                return [_orig_add(self, c) for c in ct]
            return _orig_add(self, ct, *a, **k)
        _cm.CpModel.add = _add
        _cm.CpModel.Add = _add
    except Exception:
        pass
    try:
        from ortools.constraint_solver import pywrapcp as _pw, routing_enums_pb2 as _re
        _keep = []
        _orig_set = _pw.RoutingModel.SetArcCostEvaluatorOfAllVehicles
        def _set(self, cb, *a):
            if callable(cb):
                _log("register_cb"); _keep.append(cb)
                cb = self.RegisterTransitCallback(cb)
            return _orig_set(self, cb, *a)
        _pw.RoutingModel.SetArcCostEvaluatorOfAllVehicles = _set
        for _nm in ("RoutingSearchParameters", "SearchParameters"):
            if not hasattr(_re, _nm):
                def _mk(*a, _nm=_nm, **k):
                    _log("params_alias"); return _pw.DefaultRoutingSearchParameters()
                setattr(_re, _nm, _mk)
    except Exception:
        pass
_llm_shim()
del _llm_shim
'''
