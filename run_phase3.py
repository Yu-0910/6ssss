# -*- coding: utf-8 -*-
import runpy
from pathlib import Path
root = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(root))
runpy.run_path(str(root / "scripts" / "aggregate_phase3.py"), run_name="__main__")
