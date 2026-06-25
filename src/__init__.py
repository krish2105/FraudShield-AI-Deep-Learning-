"""
FraudShield AI - source package.

This package contains all reusable logic for the payment fraud
sequence-detection project: configuration, data loading, preprocessing,
feature engineering, sequence building, model training, evaluation,
prediction and business rules.

All modules use RELATIVE paths (resolved from the project root) so the
project runs on any machine without editing hardcoded paths.
"""

__version__ = "1.0.0"
__all__ = [
    "config",
    "data_loader",
    "make_sample_data",
    "preprocessing",
    "feature_engineering",
    "sequence_builder",
    "business_rules",
    "utils",
]
