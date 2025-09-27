#!/usr/bin/env python3
"""PAKE System - Feature Engineering Service
Phase 9B: Advanced AI/ML Pipeline Integration

Provides comprehensive feature engineering capabilities including feature extraction,
transformation, selection, and automated feature pipeline management.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Types of features"""

    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    COMPLEX = "complex"


class TransformationType(Enum):
    """Types of feature transformations"""

    SCALING = "scaling"
    ENCODING = "encoding"
    NORMALIZATION = "normalization"
    BINNING = "binning"
    POLYNOMIAL = "polynomial"
    LOGARITHMIC = "logarithmic"
    SQUARE_ROOT = "square_root"
    RECIPROCAL = "reciprocal"


class SelectionMethod(Enum):
    """Feature selection methods"""

    CORRELATION = "correlation"
    MUTUAL_INFORMATION = "mutual_information"
    CHI_SQUARE = "chi_square"
    F_SCORE = "f_score"
    RECURSIVE_ELIMINATION = "recursive_elimination"
    LASSO = "lasso"
    RANDOM_FOREST = "random_forest"


@dataclass(frozen=True)
class FeatureDefinition:
    """Immutable feature definition"""

    feature_name: str
    feature_type: FeatureType
    description: str = ""
    source_column: str | None = None
    transformation_pipeline: list[str] = field(default_factory=list)
    validation_rules: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "feature_name": self.feature_name,
            "feature_type": self.feature_type.value,
            "description": self.description,
            "source_column": self.source_column,
            "transformation_pipeline": self.transformation_pipeline,
            "validation_rules": self.validation_rules,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class FeatureSet:
    """Immutable feature set definition"""

    feature_set_id: str
    feature_set_name: str
    features: list[FeatureDefinition]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "feature_set_id": self.feature_set_id,
            "feature_set_name": self.feature_set_name,
            "features": [f.to_dict() for f in self.features],
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class FeaturePipeline:
    """Immutable feature pipeline definition"""

    pipeline_id: str
    pipeline_name: str
    feature_set_id: str
    transformations: list[dict[str, Any]]
    output_schema: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "pipeline_id": self.pipeline_id,
            "pipeline_name": self.pipeline_name,
            "feature_set_id": self.feature_set_id,
            "transformations": self.transformations,
            "output_schema": self.output_schema,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
        }


@dataclass(frozen=True)
class FeatureProcessingResult:
    """Immutable feature processing result"""

    pipeline_id: str
    input_data_shape: tuple[int, int]
    output_data_shape: tuple[int, int]
    processing_time_ms: float
    features_created: int
    features_dropped: int
    validation_errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "pipeline_id": self.pipeline_id,
            "input_data_shape": self.input_data_shape,
            "output_data_shape": self.output_data_shape,
            "processing_time_ms": self.processing_time_ms,
            "features_created": self.features_created,
            "features_dropped": self.features_dropped,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata,
            "processed_at": self.processed_at.isoformat(),
        }


@dataclass
class FeatureEngineeringConfig:
    """Configuration for feature engineering service"""

    # Storage settings
    feature_storage_path: str = "/tmp/pake_features"
    pipeline_storage_path: str = "/tmp/pake_pipelines"
    cache_storage_path: str = "/tmp/pake_cache"

    # Processing settings
    max_concurrent_pipelines: int = 10
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    enable_validation: bool = True

    # Feature selection settings
    max_features: int = 1000
    correlation_threshold: float = 0.95
    mutual_info_threshold: float = 0.01

    # Performance settings
    batch_size: int = 10000
    enable_parallel_processing: bool = True
    max_workers: int = 4

    # Monitoring
    enable_processing_monitoring: bool = True
    monitoring_interval_seconds: int = 60


class FeatureTransformer(ABC):
    """Abstract base class for feature transformers"""

    @abstractmethod
    def fit(self, data: pd.DataFrame) -> "FeatureTransformer":
        """Fit transformer to data"""

    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform data"""

    @abstractmethod
    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform data"""

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """Get output feature names"""


class NumericalScaler(FeatureTransformer):
    """Numerical feature scaler"""

    def __init__(self, method: str = "standard"):
        self.method = method
        self.scaler = None
        self.feature_names = []

    def fit(self, data: pd.DataFrame) -> "NumericalScaler":
        """Fit scaler to numerical data"""
        from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

        if self.method == "standard":
            self.scaler = StandardScaler()
        elif self.method == "minmax":
            self.scaler = MinMaxScaler()
        elif self.method == "robust":
            self.scaler = RobustScaler()
        else:
            raise ValueError(f"Unsupported scaling method: {self.method}")

        # Select numerical columns
        numerical_cols = data.select_dtypes(include=[np.number]).columns
        self.feature_names = list(numerical_cols)

        if len(numerical_cols) > 0:
            self.scaler.fit(data[numerical_cols])

        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform numerical data"""
        if self.scaler is None:
            raise ValueError("Scaler not fitted")

        numerical_cols = data.select_dtypes(include=[np.number]).columns
        if len(numerical_cols) == 0:
            return data.copy()

        transformed_data = data.copy()
        transformed_data[numerical_cols] = self.scaler.transform(data[numerical_cols])

        return transformed_data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform data"""
        return self.fit(data).transform(data)

    def get_feature_names(self) -> list[str]:
        """Get feature names"""
        return self.feature_names


class CategoricalEncoder(FeatureTransformer):
    """Categorical feature encoder"""

    def __init__(self, method: str = "onehot", handle_unknown: str = "ignore"):
        self.method = method
        self.handle_unknown = handle_unknown
        self.encoder = None
        self.feature_names = []
        self.categorical_columns = []

    def fit(self, data: pd.DataFrame) -> "CategoricalEncoder":
        """Fit encoder to categorical data"""
        from sklearn.preprocessing import LabelEncoder, OneHotEncoder, OrdinalEncoder

        # Select categorical columns
        self.categorical_columns = data.select_dtypes(
            include=["object", "category"],
        ).columns.tolist()

        if len(self.categorical_columns) == 0:
            return self

        if self.method == "onehot":
            self.encoder = OneHotEncoder(
                handle_unknown=self.handle_unknown,
                sparse_output=False,
            )
            self.encoder.fit(data[self.categorical_columns])

            # Generate feature names
            self.feature_names = []
            for i, col in enumerate(self.categorical_columns):
                categories = self.encoder.categories_[i]
                for cat in categories:
                    self.feature_names.append(f"{col}_{cat}")

        elif self.method == "label":
            self.encoder = LabelEncoder()
            # For multiple columns, we'll encode each separately
            self.feature_names = self.categorical_columns.copy()

        elif self.method == "ordinal":
            self.encoder = OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1,
            )
            self.encoder.fit(data[self.categorical_columns])
            self.feature_names = self.categorical_columns.copy()

        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform categorical data"""
        if self.encoder is None or len(self.categorical_columns) == 0:
            return data.copy()

        transformed_data = data.copy()

        if self.method == "onehot":
            encoded = self.encoder.transform(data[self.categorical_columns])
            encoded_df = pd.DataFrame(
                encoded,
                columns=self.feature_names,
                index=data.index,
            )

            # Drop original categorical columns and add encoded ones
            transformed_data = transformed_data.drop(columns=self.categorical_columns)
            transformed_data = pd.concat([transformed_data, encoded_df], axis=1)

        elif self.method == "label":
            for col in self.categorical_columns:
                if col in data.columns:
                    le = LabelEncoder()
                    le.fit(data[col].astype(str))
                    transformed_data[col] = le.transform(data[col].astype(str))

        elif self.method == "ordinal":
            encoded = self.encoder.transform(data[self.categorical_columns])
            transformed_data[self.categorical_columns] = encoded

        return transformed_data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform data"""
        return self.fit(data).transform(data)

    def get_feature_names(self) -> list[str]:
        """Get feature names"""
        return self.feature_names


class TextFeatureExtractor(FeatureTransformer):
    """Text feature extractor"""

    def __init__(self, method: str = "tfidf", max_features: int = 1000):
        self.method = method
        self.max_features = max_features
        self.extractor = None
        self.feature_names = []
        self.text_columns = []

    def fit(self, data: pd.DataFrame) -> "TextFeatureExtractor":
        """Fit text extractor"""
        from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

        # Select text columns
        self.text_columns = data.select_dtypes(include=["object"]).columns.tolist()

        if len(self.text_columns) == 0:
            return self

        # Combine text columns
        text_data = (
            data[self.text_columns]
            .fillna("")
            .astype(str)
            .apply(lambda x: " ".join(x), axis=1)
        )

        if self.method == "tfidf":
            self.extractor = TfidfVectorizer(
                max_features=self.max_features,
                stop_words="english",
                ngram_range=(1, 2),
            )
        elif self.method == "count":
            self.extractor = CountVectorizer(
                max_features=self.max_features,
                stop_words="english",
                ngram_range=(1, 2),
            )
        else:
            raise ValueError(f"Unsupported text extraction method: {self.method}")

        self.extractor.fit(text_data)
        self.feature_names = [
            f"text_{name}" for name in self.extractor.get_feature_names_out()
        ]

        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform text data"""
        if self.extractor is None or len(self.text_columns) == 0:
            return data.copy()

        # Combine text columns
        text_data = (
            data[self.text_columns]
            .fillna("")
            .astype(str)
            .apply(lambda x: " ".join(x), axis=1)
        )

        # Extract features
        extracted_features = self.extractor.transform(text_data)
        extracted_df = pd.DataFrame(
            extracted_features.toarray(),
            columns=self.feature_names,
            index=data.index,
        )

        # Drop original text columns and add extracted features
        transformed_data = data.drop(columns=self.text_columns)
        transformed_data = pd.concat([transformed_data, extracted_df], axis=1)

        return transformed_data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform data"""
        return self.fit(data).transform(data)

    def get_feature_names(self) -> list[str]:
        """Get feature names"""
        return self.feature_names


class FeatureSelector(FeatureTransformer):
    """Feature selector"""

    def __init__(self, method: SelectionMethod, k: int = 10):
        self.method = method
        self.k = k
        self.selector = None
        self.selected_features = []
        self.feature_names = []

    def fit(
        self,
        data: pd.DataFrame,
        target: pd.Series | None = None,
    ) -> "FeatureSelector":
        """Fit feature selector"""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.feature_selection import (
            f_classif,
            f_regression,
            mutual_info_classif,
            mutual_info_regression,
        )

        self.feature_names = data.columns.tolist()

        if self.method == SelectionMethod.CORRELATION:
            # Remove highly correlated features
            corr_matrix = data.corr().abs()
            upper_tri = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool),
            )
            self.selected_features = [
                col for col in upper_tri.columns if any(upper_tri[col] > 0.95)
            ]
            self.selected_features = [
                col for col in data.columns if col not in self.selected_features
            ]

        elif self.method == SelectionMethod.MUTUAL_INFORMATION:
            if target is not None:
                if target.dtype == "object" or len(target.unique()) < 10:
                    # Classification
                    mi_scores = mutual_info_classif(data, target)
                else:
                    # Regression
                    mi_scores = mutual_info_regression(data, target)

                # Select top k features
                feature_scores = list(zip(data.columns, mi_scores, strict=False))
                feature_scores.sort(key=lambda x: x[1], reverse=True)
                self.selected_features = [feat[0] for feat in feature_scores[: self.k]]
            else:
                self.selected_features = self.feature_names

        elif self.method == SelectionMethod.F_SCORE:
            if target is not None:
                if target.dtype == "object" or len(target.unique()) < 10:
                    # Classification
                    f_scores, _ = f_classif(data, target)
                else:
                    # Regression
                    f_scores, _ = f_regression(data, target)

                # Select top k features
                feature_scores = list(zip(data.columns, f_scores, strict=False))
                feature_scores.sort(key=lambda x: x[1], reverse=True)
                self.selected_features = [feat[0] for feat in feature_scores[: self.k]]
            else:
                self.selected_features = self.feature_names

        elif self.method == SelectionMethod.RANDOM_FOREST:
            if target is not None:
                if target.dtype == "object" or len(target.unique()) < 10:
                    # Classification
                    rf = RandomForestClassifier(n_estimators=100, random_state=42)
                else:
                    # Regression
                    rf = RandomForestRegressor(n_estimators=100, random_state=42)

                rf.fit(data, target)
                feature_importance = rf.feature_importances_

                # Select top k features
                feature_scores = list(
                    zip(data.columns, feature_importance, strict=False)
                )
                feature_scores.sort(key=lambda x: x[1], reverse=True)
                self.selected_features = [feat[0] for feat in feature_scores[: self.k]]
            else:
                self.selected_features = self.feature_names

        else:
            self.selected_features = self.feature_names

        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform data by selecting features"""
        return data[self.selected_features]

    def fit_transform(
        self,
        data: pd.DataFrame,
        target: pd.Series | None = None,
    ) -> pd.DataFrame:
        """Fit and transform data"""
        return self.fit(data, target).transform(data)

    def get_feature_names(self) -> list[str]:
        """Get selected feature names"""
        return self.selected_features


class FeatureStore:
    """Feature store for managing feature definitions and metadata"""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.feature_sets: dict[str, FeatureSet] = {}
        self.feature_pipelines: dict[str, FeaturePipeline] = {}
        self.feature_cache: dict[str, pd.DataFrame] = {}

        # Load existing definitions
        self._load_feature_definitions()

    def _load_feature_definitions(self):
        """Load existing feature definitions from storage"""
        try:
            # Load feature sets
            feature_sets_file = self.storage_path / "feature_sets.json"
            if feature_sets_file.exists():
                with open(feature_sets_file) as f:
                    feature_sets_data = json.load(f)
                    for fs_data in feature_sets_data:
                        features = [FeatureDefinition(**f) for f in fs_data["features"]]
                        feature_set = FeatureSet(
                            feature_set_id=fs_data["feature_set_id"],
                            feature_set_name=fs_data["feature_set_name"],
                            features=features,
                            created_at=datetime.fromisoformat(fs_data["created_at"]),
                            version=fs_data["version"],
                            description=fs_data["description"],
                            tags=fs_data["tags"],
                        )
                        self.feature_sets[feature_set.feature_set_id] = feature_set

            # Load feature pipelines
            pipelines_file = self.storage_path / "feature_pipelines.json"
            if pipelines_file.exists():
                with open(pipelines_file) as f:
                    pipelines_data = json.load(f)
                    for pipeline_data in pipelines_data:
                        pipeline = FeaturePipeline(
                            pipeline_id=pipeline_data["pipeline_id"],
                            pipeline_name=pipeline_data["pipeline_name"],
                            feature_set_id=pipeline_data["feature_set_id"],
                            transformations=pipeline_data["transformations"],
                            output_schema=pipeline_data["output_schema"],
                            created_at=datetime.fromisoformat(
                                pipeline_data["created_at"],
                            ),
                            version=pipeline_data["version"],
                        )
                        self.feature_pipelines[pipeline.pipeline_id] = pipeline

            logger.info(
                f"Loaded {len(self.feature_sets)} feature sets and {len(self.feature_pipelines)} pipelines",
            )

        except Exception as e:
            logger.error(f"Failed to load feature definitions: {e}")

    def _save_feature_definitions(self):
        """Save feature definitions to storage"""
        try:
            # Save feature sets
            feature_sets_data = [fs.to_dict() for fs in self.feature_sets.values()]
            with open(self.storage_path / "feature_sets.json", "w") as f:
                json.dump(feature_sets_data, f, indent=2)

            # Save feature pipelines
            pipelines_data = [fp.to_dict() for fp in self.feature_pipelines.values()]
            with open(self.storage_path / "feature_pipelines.json", "w") as f:
                json.dump(pipelines_data, f, indent=2)

            logger.info("Saved feature definitions")

        except Exception as e:
            logger.error(f"Failed to save feature definitions: {e}")

    def register_feature_set(self, feature_set: FeatureSet) -> bool:
        """Register a new feature set"""
        try:
            self.feature_sets[feature_set.feature_set_id] = feature_set
            self._save_feature_definitions()
            logger.info(f"Registered feature set {feature_set.feature_set_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register feature set: {e}")
            return False

    def register_feature_pipeline(self, pipeline: FeaturePipeline) -> bool:
        """Register a new feature pipeline"""
        try:
            self.feature_pipelines[pipeline.pipeline_id] = pipeline
            self._save_feature_definitions()
            logger.info(f"Registered feature pipeline {pipeline.pipeline_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register feature pipeline: {e}")
            return False

    def get_feature_set(self, feature_set_id: str) -> FeatureSet | None:
        """Get feature set by ID"""
        return self.feature_sets.get(feature_set_id)

    def get_feature_pipeline(self, pipeline_id: str) -> FeaturePipeline | None:
        """Get feature pipeline by ID"""
        return self.feature_pipelines.get(pipeline_id)

    def list_feature_sets(self) -> list[FeatureSet]:
        """List all feature sets"""
        return list(self.feature_sets.values())

    def list_feature_pipelines(self) -> list[FeaturePipeline]:
        """List all feature pipelines"""
        return list(self.feature_pipelines.values())

    def cache_features(self, cache_key: str, features: pd.DataFrame):
        """Cache processed features"""
        self.feature_cache[cache_key] = features.copy()

    def get_cached_features(self, cache_key: str) -> pd.DataFrame | None:
        """Get cached features"""
        return self.feature_cache.get(cache_key)

    def clear_cache(self):
        """Clear feature cache"""
        self.feature_cache.clear()


class FeatureEngineer:
    """Main feature engineering service.
    Provides comprehensive feature engineering capabilities with automated pipelines.
    """

    def __init__(self, config: FeatureEngineeringConfig = None):
        self.config = config or FeatureEngineeringConfig()

        # Initialize feature store
        self.feature_store = FeatureStore(self.config.feature_storage_path)

        # Available transformers
        self.transformers: dict[str, FeatureTransformer] = {}

        # Processing statistics
        self.stats = {
            "pipelines_executed": 0,
            "features_created": 0,
            "features_dropped": 0,
            "processing_time_total": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        logger.info("Initialized Feature Engineer")

    async def process_features(
        self,
        data: pd.DataFrame,
        pipeline_id: str,
        target: pd.Series | None = None,
    ) -> tuple[pd.DataFrame, FeatureProcessingResult]:
        """Process features using specified pipeline"""
        start_time = time.time()

        try:
            # Get pipeline definition
            pipeline = self.feature_store.get_feature_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Check cache
            cache_key = self._generate_cache_key(data, pipeline_id)
            if self.config.enable_caching:
                cached_features = self.feature_store.get_cached_features(cache_key)
                if cached_features is not None:
                    self.stats["cache_hits"] += 1
                    logger.info(f"Using cached features for pipeline {pipeline_id}")
                    return cached_features, self._create_processing_result(
                        pipeline_id,
                        data.shape,
                        cached_features.shape,
                        0.0,
                        0,
                        0,
                    )

            self.stats["cache_misses"] += 1

            # Process features
            processed_data = data.copy()
            features_created = 0
            features_dropped = 0

            for transformation in pipeline.transformations:
                processed_data, created, dropped = await self._apply_transformation(
                    processed_data,
                    transformation,
                    target,
                )
                features_created += created
                features_dropped += dropped

            # Cache processed features
            if self.config.enable_caching:
                self.feature_store.cache_features(cache_key, processed_data)

            # Create processing result
            processing_time = (time.time() - start_time) * 1000
            result = self._create_processing_result(
                pipeline_id,
                data.shape,
                processed_data.shape,
                processing_time,
                features_created,
                features_dropped,
            )

            # Update statistics
            self.stats["pipelines_executed"] += 1
            self.stats["features_created"] += features_created
            self.stats["features_dropped"] += features_dropped
            self.stats["processing_time_total"] += processing_time

            logger.info(f"Processed features with pipeline {pipeline_id}")
            return processed_data, result

        except Exception as e:
            logger.error(f"Feature processing failed: {e}")
            raise

    async def _apply_transformation(
        self,
        data: pd.DataFrame,
        transformation: dict[str, Any],
        target: pd.Series | None = None,
    ) -> tuple[pd.DataFrame, int, int]:
        """Apply a single transformation"""
        try:
            transformation_type = transformation.get("type")
            params = transformation.get("params", {})

            features_before = data.shape[1]

            if transformation_type == "numerical_scaling":
                transformer = NumericalScaler(method=params.get("method", "standard"))
                data = transformer.fit_transform(data)

            elif transformation_type == "categorical_encoding":
                transformer = CategoricalEncoder(method=params.get("method", "onehot"))
                data = transformer.fit_transform(data)

            elif transformation_type == "text_extraction":
                transformer = TextFeatureExtractor(
                    method=params.get("method", "tfidf"),
                    max_features=params.get("max_features", 1000),
                )
                data = transformer.fit_transform(data)

            elif transformation_type == "feature_selection":
                transformer = FeatureSelector(
                    method=SelectionMethod(params.get("method", "mutual_information")),
                    k=params.get("k", 10),
                )
                data = transformer.fit_transform(data, target)

            elif transformation_type == "custom":
                # Custom transformation
                custom_func = transformation.get("function")
                if custom_func:
                    data = custom_func(data)

            features_after = data.shape[1]
            features_created = max(0, features_after - features_before)
            features_dropped = max(0, features_before - features_after)

            return data, features_created, features_dropped

        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            raise

    def _generate_cache_key(self, data: pd.DataFrame, pipeline_id: str) -> str:
        """Generate cache key for data and pipeline"""
        data_hash = hashlib.sha256(pd.util.hash_pandas_object(data).values).hexdigest()[
            :16
        ]
        return f"{pipeline_id}_{data_hash}"

    def _create_processing_result(
        self,
        pipeline_id: str,
        input_shape: tuple[int, int],
        output_shape: tuple[int, int],
        processing_time: float,
        features_created: int,
        features_dropped: int,
    ) -> FeatureProcessingResult:
        """Create processing result"""
        return FeatureProcessingResult(
            pipeline_id=pipeline_id,
            input_data_shape=input_shape,
            output_data_shape=output_shape,
            processing_time_ms=processing_time,
            features_created=features_created,
            features_dropped=features_dropped,
        )

    async def create_automated_pipeline(
        self,
        data: pd.DataFrame,
        target: pd.Series | None = None,
        pipeline_name: str = "auto_pipeline",
    ) -> str:
        """Create an automated feature pipeline"""
        try:
            pipeline_id = f"{pipeline_name}_{int(time.time())}"
            transformations = []

            # Analyze data types and create appropriate transformations
            numerical_cols = data.select_dtypes(include=[np.number]).columns
            categorical_cols = data.select_dtypes(
                include=["object", "category"],
            ).columns

            # Add numerical scaling
            if len(numerical_cols) > 0:
                transformations.append(
                    {"type": "numerical_scaling", "params": {"method": "standard"}},
                )

            # Add categorical encoding
            if len(categorical_cols) > 0:
                transformations.append(
                    {"type": "categorical_encoding", "params": {"method": "onehot"}},
                )

            # Add feature selection if target is provided
            if target is not None:
                transformations.append(
                    {
                        "type": "feature_selection",
                        "params": {
                            "method": "mutual_information",
                            "k": min(50, data.shape[1]),
                        },
                    },
                )

            # Create pipeline
            pipeline = FeaturePipeline(
                pipeline_id=pipeline_id,
                pipeline_name=pipeline_name,
                feature_set_id="auto_features",
                transformations=transformations,
                output_schema={"type": "auto_generated"},
            )

            # Register pipeline
            self.feature_store.register_feature_pipeline(pipeline)

            logger.info(f"Created automated pipeline {pipeline_id}")
            return pipeline_id

        except Exception as e:
            logger.error(f"Failed to create automated pipeline: {e}")
            raise

    def get_processing_statistics(self) -> dict[str, Any]:
        """Get processing statistics"""
        stats = self.stats.copy()

        if stats["pipelines_executed"] > 0:
            stats["average_processing_time_ms"] = (
                stats["processing_time_total"] / stats["pipelines_executed"]
            )
            stats["cache_hit_rate"] = stats["cache_hits"] / (
                stats["cache_hits"] + stats["cache_misses"]
            )
        else:
            stats["average_processing_time_ms"] = 0.0
            stats["cache_hit_rate"] = 0.0

        stats["registered_pipelines"] = len(self.feature_store.feature_pipelines)
        stats["registered_feature_sets"] = len(self.feature_store.feature_sets)
        stats["cached_features"] = len(self.feature_store.feature_cache)

        return stats


# Production-ready factory functions
def create_production_feature_engineer() -> FeatureEngineer:
    """Create production-ready feature engineer"""
    config = FeatureEngineeringConfig(
        feature_storage_path="/tmp/pake_features/production",
        pipeline_storage_path="/tmp/pake_pipelines/production",
        cache_storage_path="/tmp/pake_cache/production",
        max_concurrent_pipelines=20,
        enable_caching=True,
        cache_ttl_hours=48,
        enable_validation=True,
        max_features=5000,
        correlation_threshold=0.9,
        mutual_info_threshold=0.005,
        batch_size=50000,
        enable_parallel_processing=True,
        max_workers=8,
        enable_processing_monitoring=True,
        monitoring_interval_seconds=30,
    )

    return FeatureEngineer(config)


if __name__ == "__main__":
    # Example usage
    async def main():
        engineer = FeatureEngineer()

        # Create sample data
        data = pd.DataFrame(
            {
                "numerical_1": np.random.normal(0, 1, 100),
                "numerical_2": np.random.normal(5, 2, 100),
                "categorical_1": np.random.choice(["A", "B", "C"], 100),
                "categorical_2": np.random.choice(["X", "Y"], 100),
                "text_1": ["This is sample text " + str(i) for i in range(100)],
            },
        )

        target = pd.Series(np.random.choice([0, 1], 100))

        # Create automated pipeline
        pipeline_id = await engineer.create_automated_pipeline(
            data,
            target,
            "test_pipeline",
        )
        print(f"Created pipeline: {pipeline_id}")

        # Process features
        processed_data, result = await engineer.process_features(
            data,
            pipeline_id,
            target,
        )

        print(f"Original shape: {data.shape}")
        print(f"Processed shape: {processed_data.shape}")
        print(f"Processing time: {result.processing_time_ms:.2f}ms")
        print(f"Features created: {result.features_created}")
        print(f"Features dropped: {result.features_dropped}")

        # Get statistics
        stats = engineer.get_processing_statistics()
        print(f"Statistics: {stats}")

    asyncio.run(main())
