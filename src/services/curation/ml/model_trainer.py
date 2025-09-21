"""Model Trainer
Advanced machine learning model training pipeline for content curation and recommendation systems.
Supports multiple algorithms, hyperparameter optimization, and model evaluation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVR

from ..models.content_item import ContentItem
from ..models.user_interaction import UserInteraction
from ..models.user_profile import UserProfile
from .feature_extractor import ContentFeatures, FeatureExtractor, UserFeatures

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelMetrics:
    """Model performance metrics"""

    model_name: str
    task_type: str  # 'regression', 'classification', 'ranking'
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    mse: float | None = None
    mae: float | None = None
    r2_score: float | None = None
    cross_val_score: float | None = None
    training_time: float = 0.0
    prediction_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for model training"""

    model_type: str
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    feature_selection: bool = True
    cross_validation_folds: int = 5
    test_size: float = 0.2
    random_state: int = 42
    max_features: int | None = None
    feature_scaling: bool = True


class ModelTrainer:
    """Advanced ML model training pipeline for curation systems"""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.feature_extractor = FeatureExtractor()
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.trained_models: dict[str, Any] = {}
        self.model_metrics: dict[str, ModelMetrics] = {}

        # Model configurations
        self.model_configs = {
            "content_quality": ModelConfig(
                model_type="regression",
                hyperparameters={
                    "RandomForest": {
                        "n_estimators": 100,
                        "max_depth": 10,
                        "random_state": 42,
                    },
                    "GradientBoosting": {
                        "n_estimators": 100,
                        "learning_rate": 0.1,
                        "max_depth": 6,
                    },
                    "SVR": {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
                    "MLP": {
                        "hidden_layer_sizes": (100, 50),
                        "max_iter": 500,
                        "random_state": 42,
                    },
                },
            ),
            "user_preference": ModelConfig(
                model_type="classification",
                hyperparameters={
                    "LogisticRegression": {"C": 1.0, "random_state": 42},
                    "RandomForest": {
                        "n_estimators": 100,
                        "max_depth": 10,
                        "random_state": 42,
                    },
                    "MLP": {
                        "hidden_layer_sizes": (100, 50),
                        "max_iter": 500,
                        "random_state": 42,
                    },
                },
            ),
            "recommendation_score": ModelConfig(
                model_type="regression",
                hyperparameters={
                    "RandomForest": {
                        "n_estimators": 200,
                        "max_depth": 15,
                        "random_state": 42,
                    },
                    "GradientBoosting": {
                        "n_estimators": 200,
                        "learning_rate": 0.05,
                        "max_depth": 8,
                    },
                    "MLP": {
                        "hidden_layer_sizes": (200, 100, 50),
                        "max_iter": 1000,
                        "random_state": 42,
                    },
                },
            ),
        }

    async def train_content_quality_model(
        self,
        contents: list[ContentItem],
        interactions: list[UserInteraction],
    ) -> ModelMetrics:
        """Train model to predict content quality scores"""
        logger.info("Training content quality model")

        try:
            # Prepare training data
            X, y = await self._prepare_content_quality_data(contents, interactions)

            if len(X) < 10:  # Need minimum data for training
                logger.warning("Insufficient data for content quality model training")
                return ModelMetrics(
                    model_name="content_quality",
                    task_type="regression",
                )

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

            # Scale features
            if self.model_configs["content_quality"].feature_scaling:
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)
            else:
                X_train_scaled = X_train
                X_test_scaled = X_test

            # Train multiple models and select best
            best_model = None
            best_score = -np.inf
            best_metrics = None

            for model_name, params in self.model_configs[
                "content_quality"
            ].hyperparameters.items():
                logger.info(f"Training {model_name} for content quality")

                start_time = datetime.now()

                if model_name == "RandomForest":
                    model = RandomForestRegressor(**params)
                elif model_name == "GradientBoosting":
                    model = GradientBoostingRegressor(**params)
                elif model_name == "SVR":
                    model = SVR(**params)
                elif model_name == "MLP":
                    model = MLPRegressor(**params)
                else:
                    continue

                # Train model
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)

                training_time = (datetime.now() - start_time).total_seconds()

                # Calculate metrics
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                # Cross-validation
                cv_scores = cross_val_score(
                    model,
                    X_train_scaled,
                    y_train,
                    cv=5,
                    scoring="r2",
                )
                cv_score = cv_scores.mean()

                metrics = ModelMetrics(
                    model_name=f"content_quality_{model_name}",
                    task_type="regression",
                    mse=mse,
                    mae=mae,
                    r2_score=r2,
                    cross_val_score=cv_score,
                    training_time=training_time,
                )

                # Select best model based on R² score
                if r2 > best_score:
                    best_score = r2
                    best_model = model
                    best_metrics = metrics

            # Save best model
            if best_model is not None:
                model_path = self.models_dir / "content_quality_model.pkl"
                joblib.dump(best_model, model_path)
                self.trained_models["content_quality"] = best_model
                self.model_metrics["content_quality"] = best_metrics

                logger.info(
                    f"Content quality model trained successfully. R²: {best_score:.3f}",
                )
                return best_metrics

        except Exception as e:
            logger.error(f"Error training content quality model: {e}")
            raise

        return ModelMetrics(model_name="content_quality", task_type="regression")

    async def train_user_preference_model(
        self,
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> ModelMetrics:
        """Train model to predict user preferences"""
        logger.info("Training user preference model")

        try:
            # Prepare training data
            X, y = await self._prepare_user_preference_data(user_profiles, interactions)

            if len(X) < 10:  # Need minimum data for training
                logger.warning("Insufficient data for user preference model training")
                return ModelMetrics(
                    model_name="user_preference",
                    task_type="classification",
                )

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y,
            )

            # Scale features
            if self.model_configs["user_preference"].feature_scaling:
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)
            else:
                X_train_scaled = X_train
                X_test_scaled = X_test

            # Train multiple models and select best
            best_model = None
            best_score = -np.inf
            best_metrics = None

            for model_name, params in self.model_configs[
                "user_preference"
            ].hyperparameters.items():
                logger.info(f"Training {model_name} for user preference")

                start_time = datetime.now()

                if model_name == "LogisticRegression":
                    model = LogisticRegression(**params)
                elif model_name == "RandomForest":
                    model = RandomForestRegressor(**params)
                elif model_name == "MLP":
                    model = MLPRegressor(**params)
                else:
                    continue

                # Train model
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)

                training_time = (datetime.now() - start_time).total_seconds()

                # Calculate metrics
                accuracy = accuracy_score(y_test, y_pred)
                precision = precision_score(y_test, y_pred, average="weighted")
                recall = recall_score(y_test, y_pred, average="weighted")
                f1 = f1_score(y_test, y_pred, average="weighted")

                # Cross-validation
                cv_scores = cross_val_score(
                    model,
                    X_train_scaled,
                    y_train,
                    cv=5,
                    scoring="accuracy",
                )
                cv_score = cv_scores.mean()

                metrics = ModelMetrics(
                    model_name=f"user_preference_{model_name}",
                    task_type="classification",
                    accuracy=accuracy,
                    precision=precision,
                    recall=recall,
                    f1_score=f1,
                    cross_val_score=cv_score,
                    training_time=training_time,
                )

                # Select best model based on F1 score
                if f1 > best_score:
                    best_score = f1
                    best_model = model
                    best_metrics = metrics

            # Save best model
            if best_model is not None:
                model_path = self.models_dir / "user_preference_model.pkl"
                joblib.dump(best_model, model_path)
                self.trained_models["user_preference"] = best_model
                self.model_metrics["user_preference"] = best_metrics

                logger.info(
                    f"User preference model trained successfully. F1: {best_score:.3f}",
                )
                return best_metrics

        except Exception as e:
            logger.error(f"Error training user preference model: {e}")
            raise

        return ModelMetrics(model_name="user_preference", task_type="classification")

    async def train_recommendation_model(
        self,
        contents: list[ContentItem],
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> ModelMetrics:
        """Train model to predict recommendation scores"""
        logger.info("Training recommendation model")

        try:
            # Prepare training data
            X, y = await self._prepare_recommendation_data(
                contents,
                user_profiles,
                interactions,
            )

            if len(X) < 10:  # Need minimum data for training
                logger.warning("Insufficient data for recommendation model training")
                return ModelMetrics(model_name="recommendation", task_type="regression")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

            # Scale features
            if self.model_configs["recommendation_score"].feature_scaling:
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)
            else:
                X_train_scaled = X_train
                X_test_scaled = X_test

            # Train multiple models and select best
            best_model = None
            best_score = -np.inf
            best_metrics = None

            for model_name, params in self.model_configs[
                "recommendation_score"
            ].hyperparameters.items():
                logger.info(f"Training {model_name} for recommendation scoring")

                start_time = datetime.now()

                if model_name == "RandomForest":
                    model = RandomForestRegressor(**params)
                elif model_name == "GradientBoosting":
                    model = GradientBoostingRegressor(**params)
                elif model_name == "MLP":
                    model = MLPRegressor(**params)
                else:
                    continue

                # Train model
                model.fit(X_train_scaled, y_train)

                # Evaluate
                y_pred = model.predict(X_test_scaled)

                training_time = (datetime.now() - start_time).total_seconds()

                # Calculate metrics
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                # Cross-validation
                cv_scores = cross_val_score(
                    model,
                    X_train_scaled,
                    y_train,
                    cv=5,
                    scoring="r2",
                )
                cv_score = cv_scores.mean()

                metrics = ModelMetrics(
                    model_name=f"recommendation_{model_name}",
                    task_type="regression",
                    mse=mse,
                    mae=mae,
                    r2_score=r2,
                    cross_val_score=cv_score,
                    training_time=training_time,
                )

                # Select best model based on R² score
                if r2 > best_score:
                    best_score = r2
                    best_model = model
                    best_metrics = metrics

            # Save best model
            if best_model is not None:
                model_path = self.models_dir / "recommendation_model.pkl"
                joblib.dump(best_model, model_path)
                self.trained_models["recommendation"] = best_model
                self.model_metrics["recommendation"] = best_metrics

                logger.info(
                    f"Recommendation model trained successfully. R²: {best_score:.3f}",
                )
                return best_metrics

        except Exception as e:
            logger.error(f"Error training recommendation model: {e}")
            raise

        return ModelMetrics(model_name="recommendation", task_type="regression")

    async def _prepare_content_quality_data(
        self,
        contents: list[ContentItem],
        interactions: list[UserInteraction],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data for content quality model"""
        X_list = []
        y_list = []

        for content in contents:
            try:
                # Extract features
                content_features = (
                    await self.feature_extractor.extract_content_features(content)
                )

                # Calculate target quality score from interactions
                content_interactions = [
                    i for i in interactions if i.content_id == content.id
                ]

                if not content_interactions:
                    continue

                # Calculate quality score from interactions
                quality_score = self._calculate_interaction_quality_score(
                    content_interactions,
                )

                # Combine features
                feature_vector = await self.feature_extractor.get_feature_vector(
                    content_features,
                    UserFeatures(user_id="dummy"),
                )

                X_list.append(feature_vector)
                y_list.append(quality_score)

            except Exception as e:
                logger.warning(f"Error processing content {content.id}: {e}")
                continue

        return np.array(X_list), np.array(y_list)

    async def _prepare_user_preference_data(
        self,
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data for user preference model"""
        X_list = []
        y_list = []

        for user_profile in user_profiles:
            try:
                # Get user interactions
                user_interactions = [
                    i for i in interactions if i.user_id == user_profile.user_id
                ]

                if not user_interactions:
                    continue

                # Extract features
                user_features = await self.feature_extractor.extract_user_features(
                    user_profile,
                    user_interactions,
                )

                # Determine preference category based on interaction patterns
                preference_category = self._determine_preference_category(
                    user_interactions,
                )

                # Combine features
                feature_vector = await self.feature_extractor.get_feature_vector(
                    ContentFeatures(content_id="dummy"),
                    user_features,
                )

                X_list.append(feature_vector)
                y_list.append(preference_category)

            except Exception as e:
                logger.warning(f"Error processing user {user_profile.user_id}: {e}")
                continue

        return np.array(X_list), np.array(y_list)

    async def _prepare_recommendation_data(
        self,
        contents: list[ContentItem],
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data for recommendation model"""
        X_list = []
        y_list = []

        for user_profile in user_profiles:
            user_interactions = [
                i for i in interactions if i.user_id == user_profile.user_id
            ]

            if not user_interactions:
                continue

            # Extract user features
            user_features = await self.feature_extractor.extract_user_features(
                user_profile,
                user_interactions,
            )

            for content in contents:
                try:
                    # Extract content features
                    content_features = (
                        await self.feature_extractor.extract_content_features(content)
                    )

                    # Check if user interacted with this content
                    user_content_interaction = next(
                        (i for i in user_interactions if i.content_id == content.id),
                        None,
                    )

                    if user_content_interaction:
                        # Use interaction score as target
                        target_score = self._calculate_interaction_score(
                            user_content_interaction,
                        )
                    else:
                        # Skip if no interaction (would need negative sampling for real
                        # implementation)
                        continue

                    # Combine features
                    feature_vector = await self.feature_extractor.get_feature_vector(
                        content_features,
                        user_features,
                    )

                    X_list.append(feature_vector)
                    y_list.append(target_score)

                except Exception as e:
                    logger.warning(
                        f"Error processing content {content.id} for user {
                            user_profile.user_id
                        }: {e}",
                    )
                    continue

        return np.array(X_list), np.array(y_list)

    def _calculate_interaction_quality_score(
        self,
        interactions: list[UserInteraction],
    ) -> float:
        """Calculate quality score from interactions"""
        if not interactions:
            return 0.0

        # Weight different interaction types
        weights = {
            "view": 0.1,
            "like": 0.3,
            "share": 0.5,
            "save": 0.4,
            "click": 0.2,
            "dismiss": -0.2,
        }

        total_score = 0.0
        total_weight = 0.0

        for interaction in interactions:
            weight = weights.get(interaction.interaction_type, 0.0)
            total_score += weight
            total_weight += abs(weight)

        return total_score / max(total_weight, 1.0)

    def _determine_preference_category(
        self,
        interactions: list[UserInteraction],
    ) -> int:
        """Determine user preference category from interactions"""
        if not interactions:
            return 0

        # Analyze interaction patterns
        interaction_types = [i.interaction_type for i in interactions]

        # Simple categorization based on dominant interaction type
        if "share" in interaction_types:
            return 1  # High engagement
        if "like" in interaction_types:
            return 2  # Medium engagement
        if "view" in interactions:
            return 3  # Low engagement
        return 0  # Unknown

    def _calculate_interaction_score(self, interaction: UserInteraction) -> float:
        """Calculate score from individual interaction"""
        scores = {
            "view": 0.1,
            "like": 0.3,
            "share": 0.5,
            "save": 0.4,
            "click": 0.2,
            "dismiss": -0.2,
        }

        base_score = scores.get(interaction.interaction_type, 0.0)

        # Adjust based on session duration
        if interaction.session_duration:
            duration_factor = min(
                interaction.session_duration / 300,
                1.0,
            )  # Max 5 minutes
            base_score *= 1 + duration_factor

        return base_score

    async def load_models(self) -> dict[str, bool]:
        """Load pre-trained models from disk"""
        loaded_models = {}

        model_files = {
            "content_quality": "content_quality_model.pkl",
            "user_preference": "user_preference_model.pkl",
            "recommendation": "recommendation_model.pkl",
        }

        for model_name, filename in model_files.items():
            model_path = self.models_dir / filename
            if model_path.exists():
                try:
                    model = joblib.load(model_path)
                    self.trained_models[model_name] = model
                    loaded_models[model_name] = True
                    logger.info(f"Loaded {model_name} model")
                except Exception as e:
                    logger.error(f"Error loading {model_name} model: {e}")
                    loaded_models[model_name] = False
            else:
                loaded_models[model_name] = False

        return loaded_models

    async def save_models(self) -> dict[str, bool]:
        """Save trained models to disk"""
        saved_models = {}

        for model_name, model in self.trained_models.items():
            try:
                model_path = self.models_dir / f"{model_name}_model.pkl"
                joblib.dump(model, model_path)
                saved_models[model_name] = True
                logger.info(f"Saved {model_name} model")
            except Exception as e:
                logger.error(f"Error saving {model_name} model: {e}")
                saved_models[model_name] = False

        return saved_models

    async def predict_content_quality(self, content: ContentItem) -> float:
        """Predict quality score for content"""
        if "content_quality" not in self.trained_models:
            logger.warning("Content quality model not trained")
            return 0.0

        try:
            # Extract features
            content_features = await self.feature_extractor.extract_content_features(
                content,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                content_features,
                UserFeatures(user_id="dummy"),
            )

            # Scale features
            feature_vector_scaled = self.scaler.transform([feature_vector])

            # Predict
            prediction = self.trained_models["content_quality"].predict(
                feature_vector_scaled,
            )[0]
            return max(0.0, min(1.0, prediction))  # Clamp to [0, 1]

        except Exception as e:
            logger.error(f"Error predicting content quality: {e}")
            return 0.0

    async def predict_user_preference(
        self,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> int:
        """Predict user preference category"""
        if "user_preference" not in self.trained_models:
            logger.warning("User preference model not trained")
            return 0

        try:
            # Extract features
            user_features = await self.feature_extractor.extract_user_features(
                user_profile,
                interactions,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                ContentFeatures(content_id="dummy"),
                user_features,
            )

            # Scale features
            feature_vector_scaled = self.scaler.transform([feature_vector])

            # Predict
            prediction = self.trained_models["user_preference"].predict(
                feature_vector_scaled,
            )[0]
            return int(prediction)

        except Exception as e:
            logger.error(f"Error predicting user preference: {e}")
            return 0

    async def predict_recommendation_score(
        self,
        content: ContentItem,
        user_profile: UserProfile,
        interactions: list[UserInteraction],
    ) -> float:
        """Predict recommendation score for content-user pair"""
        if "recommendation" not in self.trained_models:
            logger.warning("Recommendation model not trained")
            return 0.0

        try:
            # Extract features
            content_features = await self.feature_extractor.extract_content_features(
                content,
            )
            user_features = await self.feature_extractor.extract_user_features(
                user_profile,
                interactions,
            )
            feature_vector = await self.feature_extractor.get_feature_vector(
                content_features,
                user_features,
            )

            # Scale features
            feature_vector_scaled = self.scaler.transform([feature_vector])

            # Predict
            prediction = self.trained_models["recommendation"].predict(
                feature_vector_scaled,
            )[0]
            return max(0.0, min(1.0, prediction))  # Clamp to [0, 1]

        except Exception as e:
            logger.error(f"Error predicting recommendation score: {e}")
            return 0.0

    def get_model_metrics(self) -> dict[str, ModelMetrics]:
        """Get metrics for all trained models"""
        return self.model_metrics.copy()

    async def retrain_models(
        self,
        contents: list[ContentItem],
        user_profiles: list[UserProfile],
        interactions: list[UserInteraction],
    ) -> dict[str, ModelMetrics]:
        """Retrain all models with new data"""
        logger.info("Retraining all models")

        results = {}

        # Train content quality model
        try:
            results["content_quality"] = await self.train_content_quality_model(
                contents,
                interactions,
            )
        except Exception as e:
            logger.error(f"Error retraining content quality model: {e}")

        # Train user preference model
        try:
            results["user_preference"] = await self.train_user_preference_model(
                user_profiles,
                interactions,
            )
        except Exception as e:
            logger.error(f"Error retraining user preference model: {e}")

        # Train recommendation model
        try:
            results["recommendation"] = await self.train_recommendation_model(
                contents,
                user_profiles,
                interactions,
            )
        except Exception as e:
            logger.error(f"Error retraining recommendation model: {e}")

        # Save models
        await self.save_models()

        logger.info("Model retraining completed")
        return results
