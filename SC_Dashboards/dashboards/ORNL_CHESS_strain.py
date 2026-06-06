#!/usr/bin/env python3
"""
ScientistCloud Bokeh entry point for the ORNL CHESS / NSDF strain dashboard.

Implementation lives in the symlinked ``nsdf_dashboard`` package under
``scientistCloudLib/SCLib_Dashboards/nsdf_dashboard`` (NSDF repo checkout).
"""
from __future__ import annotations

import os
import runpy
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCLIB = ""
for _candidate in (
    os.path.abspath(os.path.join(_HERE, "..", "..", "..", "scientistCloudLib", "SCLib_Dashboards")),
    os.path.abspath(os.path.join(_HERE, "SCLib_Dashboards")),
):
    if os.path.isdir(_candidate):
        _SCLIB = _candidate
        if _candidate not in sys.path:
            sys.path.insert(0, _candidate)
        break

if not _SCLIB or not os.path.isdir(os.path.join(_SCLIB, "nsdf_dashboard")):
    raise ImportError(
        "nsdf_dashboard package not found under SCLib_Dashboards. "
        "On the build host run SC_Docker/scripts/sync_ornl_nsdf_dashboard.sh "
        "after cloning the NSDF dashboard repo (see NSDF_DASHBOARD_HOME in env.scientistcloud), "
        "then rebuild the ORNL_CHESS_strain image."
    )

os.environ.setdefault("PYTHONPATH", _SCLIB)

runpy.run_module("nsdf_dashboard.ORNL_CHESS_strain", run_name="__main__")
