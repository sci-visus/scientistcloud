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
for _candidate in (
    os.path.abspath(os.path.join(_HERE, "..", "..", "..", "scientistCloudLib", "SCLib_Dashboards")),
    os.path.abspath(os.path.join(_HERE, "SCLib_Dashboards")),
):
    if os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)
        break

runpy.run_module("nsdf_dashboard.ORNL_CHESS_strain", run_name="__main__")
