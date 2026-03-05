# -*- coding:utf-8 -*-

import os
import sys

# Get app path
if getattr(sys, "frozen", False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.append(app_path)
