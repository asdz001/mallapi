# -----------------------------------------------------------------------------
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
import numpy as np

from ...util.event import Event
from ...visuals import AxisVisual
from .viewbox import ViewBox
from .widget import Widget

class AxisWidget(Widget):
    def __init__(self, orientation: str = "left", **kwargs): ...
    def on_resize(self, event: Event): ...
    def _update_axis(self): ...
    def _axis_ends(self): ...
    def link_view(self, view: ViewBox): ...
    def _view_changed(self, event=None): ...
