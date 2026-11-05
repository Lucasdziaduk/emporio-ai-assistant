"""Data ingestion, SQLite persistence, and repositories."""

from app.data.database import create_connection, foreign_key_violations, initialize_database
from app.data.loader import (
    DataLoadError,
    DataQualityIssue,
    DataValidationError,
    LoadReport,
    MissingDataFileError,
    load_dataset,
    money_to_cents,
)
from app.data.repositories import (
    CategoryRepository,
    CustomerRepository,
    DatasetRepository,
    OrderRepository,
    ProductRepository,
    PromotionRepository,
)

__all__ = [
    "create_connection",
    "initialize_database",
    "foreign_key_violations",
    "load_dataset",
    "money_to_cents",
    "LoadReport",
    "DataQualityIssue",
    "DataLoadError",
    "DataValidationError",
    "MissingDataFileError",
    "CategoryRepository",
    "ProductRepository",
    "PromotionRepository",
    "CustomerRepository",
    "OrderRepository",
    "DatasetRepository",
]
