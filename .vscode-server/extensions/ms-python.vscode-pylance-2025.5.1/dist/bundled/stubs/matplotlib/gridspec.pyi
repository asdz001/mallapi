from collections.abc import Sequence

from ._typing import *
from .backend_bases import RendererBase
from .figure import Figure, FigureBase, SubplotParams

class GridSpecBase:
    def __init__(
        self,
        nrows: int,
        ncols: int,
        height_ratios: ArrayLike = ...,
        width_ratios: ArrayLike = ...,
    ) -> None: ...

    nrows = ...
    ncols = ...
    def get_geometry(self) -> tuple[int, int]: ...
    def get_subplot_params(self, figure: Figure = ...): ...
    def new_subplotspec(self, loc: tuple[int, int], rowspan: int = ..., colspan: int = ...) -> SubplotSpec: ...
    def set_width_ratios(self, width_ratios: ArrayLike) -> None: ...
    def get_width_ratios(self) -> list[float]: ...
    def set_height_ratios(self, height_ratios: ArrayLike) -> None: ...
    def get_height_ratios(self) -> list[float]: ...
    def get_grid_positions(self, fig: Figure, raw: bool = False): ...
    def __getitem__(self, key) -> SubplotSpec: ...
    def subplots(self, *, sharex=..., sharey=..., squeeze=..., subplot_kw=...): ...

class GridSpec(GridSpecBase):
    def __init__(
        self,
        nrows: int,
        ncols: int,
        figure: FigureBase = ...,
        left: float = ...,
        bottom: float = ...,
        right: float = ...,
        top: float = ...,
        wspace: float = ...,
        hspace: float = ...,
        width_ratios: ArrayLike = ...,
        height_ratios: ArrayLike = ...,
    ) -> None: ...
    def update(self, **kwargs) -> None: ...
    def get_subplot_params(self, figure: FigureBase = ...) -> SubplotParams: ...
    def locally_modified_subplot_params(self) -> list[str]: ...
    def tight_layout(
        self,
        figure: Figure,
        renderer: RendererBase = ...,
        pad: float = ...,
        h_pad: float = ...,
        w_pad: float = ...,
        rect: Sequence[float] = ...,
    ) -> None: ...

class GridSpecFromSubplotSpec(GridSpecBase):
    def __init__(
        self,
        nrows: int,
        ncols: int,
        subplot_spec: SubplotSpec,
        wspace: float = ...,
        hspace: float = ...,
        height_ratios: ArrayLike = ...,
        width_ratios: ArrayLike = ...,
    ) -> None: ...
    def get_subplot_params(self, figure: Figure = ...) -> SubplotParams: ...
    def get_topmost_subplotspec(self) -> SubplotSpec: ...

class SubplotSpec:
    def __init__(
        self,
        gridspec: GridSpecBase,
        num1: int,
        num2: int = ...,
    ) -> None: ...
    @property
    def num2(self): ...
    @num2.setter
    def num2(self, value): ...
    def get_gridspec(self) -> GridSpecBase: ...
    def get_geometry(self): ...
    @property
    def rowspan(self) -> range: ...
    @property
    def colspan(self) -> range: ...
    def is_first_row(self) -> bool: ...
    def is_last_row(self) -> bool: ...
    def is_first_col(self) -> bool: ...
    def is_last_col(self) -> bool: ...
    def get_position(self, figure: Figure): ...
    def get_topmost_subplotspec(self) -> SubplotSpec: ...
    def __eq__(self, other: SubplotSpec) -> bool: ...
    def __hash__(self) -> int: ...
    def subgridspec(self, nrows: int, ncols: int, **kwargs) -> GridSpecFromSubplotSpec: ...
