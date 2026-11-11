"""Node-local staging of a Slurm job's output files (user 2026-11-11: write to /local-data on the node, then move to /home1).

poc/slurm/job.sh puts this folder on PYTHONPATH and sets POC_LOCAL to the job's own directory under /local-data, so every Python
process of the job imports this module at startup. Without POC_LOCAL it does nothing (gs15 lanes, the login node, older jobs).

A file under /NAS/SJ/POSTECH (the repo and nlp_data, the container's view of /home1/leesangjun/SJ/POSTECH) that is opened for writing
is written to $POC_LOCAL/stage/<the same relative path> instead. Reads, existence checks, directory listings and globs see the staged
copy first and the shared one otherwise, so a later command of the same job reads what an earlier one wrote. Appending to a shared file
first copies it into the stage. When the job ends, job.sh hands the stage to the user and moves it onto /home1.
Not covered: low-level os.open (tempfile.mkstemp) and programs that are not Python (bash redirections, lean); lane.sh and
start_server.sh stage their own logs, and Lean's scratch files live in the container's /tmp.
"""
import os

if os.environ.get("POC_LOCAL"):
    import builtins
    import glob as _glob
    import io
    import shutil

    _SH = os.environ.get("POC_SHARED_ROOT", "/NAS/SJ/POSTECH/")   # override only for testing
    _ST = os.path.join(os.environ["POC_LOCAL"], "stage") + "/"
    _open, _exists, _isfile, _isdir = builtins.open, os.path.exists, os.path.isfile, os.path.isdir
    _getsize, _getmtime, _makedirs, _listdir = os.path.getsize, os.path.getmtime, os.makedirs, os.listdir
    _remove, _replace, _rename = os.remove, os.replace, os.rename
    _igl = _glob.iglob

    def _loc(p):
        """the staged path of a shared path; None for any other path (or a file descriptor)"""
        try:
            a = os.path.abspath(os.fspath(p))
        except TypeError:
            return None
        return _ST + a[len(_SH):] if a.startswith(_SH) else None

    def _rd(p):
        l = _loc(p)
        return l if l is not None and _exists(l) else p

    def _open_staged(file, mode="r", *a, **k):
        l = _loc(file)
        if l is None:
            return _open(file, mode, *a, **k)
        if any(c in mode for c in "wxa+"):
            _makedirs(os.path.dirname(l), exist_ok=True)
            if ("a" in mode or "+" in mode) and not _exists(l) and _isfile(file):
                shutil.copyfile(file, l)
            return _open(l, mode, *a, **k)
        return _open(_rd(file), mode, *a, **k)

    def _either(f):
        return lambda p, *a, **k: f(_rd(p), *a, **k)

    def _makedirs_staged(p, *a, **k):
        l = _loc(p)
        return _makedirs(l if l is not None else p, *a, **k)

    def _listdir_staged(p="."):
        l = _loc(p)
        if l is None:
            return _listdir(p)
        out = set(_listdir(p)) if _isdir(p) else set()
        return sorted(out | (set(_listdir(l)) if _isdir(l) else set()))

    def _remove_staged(p, *a, **k):
        l = _loc(p)
        if l is not None and _exists(l):
            _remove(l)
            if not _exists(p):
                return None
        return _remove(p, *a, **k)

    def _move(f):
        def g(src, dst, *a, **k):
            ls, ld = _loc(src), _loc(dst)
            if ls is not None and _exists(ls) and ld is not None:
                _makedirs(os.path.dirname(ld), exist_ok=True)
                return f(ls, ld, *a, **k)
            return f(src, dst, *a, **k)
        return g

    def _glob_staged(pattern, *a, **k):
        l = _loc(pattern)
        hits = list(_igl(pattern, *a, **k))   # the original iglob: glob.glob itself calls the (patched) module-level iglob
        if l is not None:
            seen = set(hits)
            hits += [x for x in (_SH + y[len(_ST):] for y in _igl(l, *a, **k)) if x not in seen]
        return hits

    builtins.open = io.open = _open_staged
    os.path.exists, os.path.isfile, os.path.getsize, os.path.getmtime = map(_either, (_exists, _isfile, _getsize, _getmtime))
    os.path.isdir = lambda p: _isdir(p) or (_loc(p) is not None and _isdir(_loc(p)))
    os.makedirs, os.listdir = _makedirs_staged, _listdir_staged
    os.remove = os.unlink = _remove_staged
    os.replace, os.rename = _move(_replace), _move(_rename)
    _glob.glob = _glob_staged
    _glob.iglob = lambda pattern, *a, **k: iter(_glob_staged(pattern, *a, **k))
