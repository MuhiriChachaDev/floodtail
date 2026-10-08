"""Explainability: SHAP, counterfactuals, model cards."""

from packages.xai.counterfactual import counterfactual_for_location
from packages.xai.model_card import build_model_card, list_model_cards
from packages.xai.shap_global import global_shap
from packages.xai.shap_local import local_shap_for_row

__all__ = [
    "build_model_card",
    "counterfactual_for_location",
    "global_shap",
    "list_model_cards",
    "local_shap_for_row",
]
