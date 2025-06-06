import warnings
from numbers import Integral as Integral, Real as Real
from typing import ClassVar, Literal
from typing_extensions import Self

import numpy as np
import scipy.linalg
from numpy import ndarray
from scipy import linalg

from ._typing import ArrayLike, Float, Int, MatrixLike
from .base import BaseEstimator, ClassifierMixin, ClassNamePrefixFeaturesOutMixin, TransformerMixin
from .covariance import (
    empirical_covariance as empirical_covariance,
    ledoit_wolf as ledoit_wolf,
    shrunk_covariance as shrunk_covariance,
)
from .covariance._shrunk_covariance import OAS
from .linear_model._base import LinearClassifierMixin
from .preprocessing import StandardScaler as StandardScaler
from .utils._array_api import get_namespace as get_namespace
from .utils._param_validation import HasMethods as HasMethods, Interval as Interval, StrOptions as StrOptions
from .utils.extmath import softmax as softmax
from .utils.multiclass import check_classification_targets as check_classification_targets, unique_labels as unique_labels
from .utils.validation import check_is_fitted as check_is_fitted

# Authors: Clemens Brunner
#          Martin Billinger
#          Matthieu Perrot
#          Mathieu Blondel

# License: BSD 3-Clause

__all__ = ["LinearDiscriminantAnalysis", "QuadraticDiscriminantAnalysis"]

class LinearDiscriminantAnalysis(
    ClassNamePrefixFeaturesOutMixin,
    LinearClassifierMixin,
    TransformerMixin,
    BaseEstimator,
):
    feature_names_in_: ndarray = ...
    n_features_in_: int = ...
    classes_: ArrayLike = ...
    xbar_: ArrayLike = ...
    scalings_: ArrayLike = ...
    priors_: ArrayLike = ...
    means_: ArrayLike = ...
    explained_variance_ratio_: ndarray = ...
    covariance_: ArrayLike = ...
    intercept_: ndarray = ...
    coef_: ndarray = ...

    _parameter_constraints: ClassVar[dict] = ...

    def __init__(
        self,
        solver: Literal["svd", "lsqr", "eigen"] = "svd",
        shrinkage: float | None | str = None,
        priors: None | ArrayLike = None,
        n_components: None | Int = None,
        store_covariance: bool = False,
        tol: Float = 1e-4,
        covariance_estimator: None | BaseEstimator | OAS = None,
    ) -> None: ...
    def fit(self, X: MatrixLike, y: ArrayLike) -> Self: ...
    def transform(self, X: MatrixLike) -> ndarray: ...
    def predict_proba(self, X: MatrixLike) -> ndarray: ...
    def predict_log_proba(self, X: MatrixLike) -> ndarray: ...
    def decision_function(self, X: MatrixLike) -> ndarray: ...

class QuadraticDiscriminantAnalysis(ClassifierMixin, BaseEstimator):
    feature_names_in_: ndarray = ...
    n_features_in_: int = ...
    classes_: ndarray = ...
    scalings_: list[ndarray] = ...
    rotations_: list[ndarray] = ...
    priors_: ArrayLike = ...
    means_: ArrayLike = ...
    covariance_: list[ndarray] = ...

    _parameter_constraints: ClassVar[dict] = ...

    def __init__(
        self, *, priors: None | ArrayLike = None, reg_param: Float = 0.0, store_covariance: bool = False, tol: Float = 1.0e-4
    ) -> None: ...
    def fit(self, X: MatrixLike, y: ArrayLike) -> Self: ...
    def decision_function(self, X: MatrixLike) -> ndarray: ...
    def predict(self, X: MatrixLike) -> ndarray: ...
    def predict_proba(self, X: MatrixLike) -> ndarray: ...
    def predict_log_proba(self, X: MatrixLike) -> ndarray: ...
