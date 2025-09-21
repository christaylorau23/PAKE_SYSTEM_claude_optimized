#!/usr/bin/env python3
"""
Advanced A/B Testing Framework
Statistical testing, experiment management, and optimization validation
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
import pandas as pd

# Statistical testing libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats
    from scipy.stats import chi2_contingency, mannwhitneyu, ttest_ind
    from statsmodels.stats.power import ttest_power
    from statsmodels.stats.proportion import proportions_ztest
except ImportError as e:
    print(f"Statistical testing dependencies not installed: {e}")
    print("Run: pip install scipy statsmodels matplotlib seaborn")


class TestStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(Enum):
    PROPORTION = "proportion"  # Conversion rate, CTR, etc.
    CONTINUOUS = "continuous"  # Revenue, engagement time, etc.
    COUNT = "count"  # Views, clicks, etc.


@dataclass
class ABTest:
    """A/B test configuration"""

    id: str
    name: str
    description: str
    test_type: TestType
    target_metric: str
    hypothesis: str
    variants: dict[str, dict]  # variant_id -> configuration
    traffic_allocation: dict[str, float]  # variant_id -> percentage
    start_date: datetime
    end_date: datetime | None
    status: TestStatus
    sample_size_target: int
    significance_level: float = 0.05
    power: float = 0.8
    minimum_detectable_effect: float = 0.05
    created_at: datetime
    created_by: str


@dataclass
class TestResult:
    """A/B test result"""

    test_id: str
    variant: str
    metric_name: str
    metric_value: float
    sample_size: int
    timestamp: datetime
    user_id: str = None
    session_id: str = None
    metadata: dict = None


@dataclass
class StatisticalAnalysis:
    """Statistical analysis results"""

    test_id: str
    variants_data: dict[str, dict]  # variant -> {mean, std, count, etc.}
    p_value: float
    test_statistic: float
    confidence_interval: tuple[float, float]
    effect_size: float
    statistical_significance: bool
    practical_significance: bool
    power_achieved: float
    recommendation: str
    analysis_date: datetime


class ABTestingFramework:
    """Advanced A/B testing and experimentation framework"""

    def __init__(self, db_path: str = "ab_testing.db"):
        self.db_path = db_path
        self.logger = self._setup_logging()

        self._init_database()

        # Statistical configuration
        self.default_significance = 0.05
        self.default_power = 0.8
        self.min_sample_size = 100

        self.logger.info("A/B Testing Framework initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        return logging.getLogger(__name__)

    def _init_database(self):
        """Initialize A/B testing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # A/B tests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ab_tests (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                test_type TEXT NOT NULL,
                target_metric TEXT NOT NULL,
                hypothesis TEXT,
                variants TEXT NOT NULL,
                traffic_allocation TEXT NOT NULL,
                start_date DATETIME NOT NULL,
                end_date DATETIME,
                status TEXT NOT NULL,
                sample_size_target INTEGER,
                significance_level REAL DEFAULT 0.05,
                power REAL DEFAULT 0.8,
                minimum_detectable_effect REAL DEFAULT 0.05,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                metadata TEXT
            )
        """,
        )

        # Test results table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                variant TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                sample_size INTEGER DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                session_id TEXT,
                metadata TEXT,
                FOREIGN KEY (test_id) REFERENCES ab_tests (id),
                INDEX idx_test_variant (test_id, variant),
                INDEX idx_timestamp (timestamp)
            )
        """,
        )

        # Statistical analyses table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS statistical_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                variants_data TEXT NOT NULL,
                p_value REAL,
                test_statistic REAL,
                confidence_interval TEXT,
                effect_size REAL,
                statistical_significance BOOLEAN,
                practical_significance BOOLEAN,
                power_achieved REAL,
                recommendation TEXT,
                analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES ab_tests (id)
            )
        """,
        )

        # Experiment tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES ab_tests (id)
            )
        """,
        )

        conn.commit()
        conn.close()

    async def create_ab_test(
        self,
        name: str,
        description: str,
        test_type: TestType,
        target_metric: str,
        hypothesis: str,
        variants: dict[str, dict],
        traffic_allocation: dict[str, float],
        duration_days: int = 14,
        significance_level: float = 0.05,
        power: float = 0.8,
        minimum_detectable_effect: float = 0.05,
        created_by: str = "system",
    ) -> str:
        """Create new A/B test"""

        # Validate inputs
        if not self._validate_test_config(variants, traffic_allocation):
            raise ValueError("Invalid test configuration")

        # Generate test ID
        test_id = str(uuid.uuid4())

        # Calculate required sample size
        sample_size = self._calculate_sample_size(
            test_type,
            minimum_detectable_effect,
            significance_level,
            power,
        )

        # Create test object
        ab_test = ABTest(
            id=test_id,
            name=name,
            description=description,
            test_type=test_type,
            target_metric=target_metric,
            hypothesis=hypothesis,
            variants=variants,
            traffic_allocation=traffic_allocation,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            status=TestStatus.DRAFT,
            sample_size_target=sample_size,
            significance_level=significance_level,
            power=power,
            minimum_detectable_effect=minimum_detectable_effect,
            created_at=datetime.now(),
            created_by=created_by,
        )

        # Store in database
        await self._store_ab_test(ab_test)

        self.logger.info(f"Created A/B test: {name} (ID: {test_id})")
        return test_id

    def _validate_test_config(self, variants: dict, traffic_allocation: dict) -> bool:
        """Validate A/B test configuration"""

        # Check variants
        if len(variants) < 2:
            self.logger.error("At least 2 variants required")
            return False

        # Check traffic allocation
        if not np.isclose(sum(traffic_allocation.values()), 1.0, atol=0.01):
            self.logger.error("Traffic allocation must sum to 1.0")
            return False

        # Check variant consistency
        if set(variants.keys()) != set(traffic_allocation.keys()):
            self.logger.error("Variants and traffic allocation must have same keys")
            return False

        return True

    def _calculate_sample_size(
        self,
        test_type: TestType,
        effect_size: float,
        alpha: float,
        power: float,
    ) -> int:
        """Calculate required sample size for statistical power"""

        try:
            if test_type == TestType.PROPORTION:
                # For proportion tests (conversion rates, CTR, etc.)
                # Using normal approximation for proportions
                baseline_rate = 0.05  # Assume 5% baseline conversion rate

                z_alpha = stats.norm.ppf(1 - alpha / 2)
                z_beta = stats.norm.ppf(power)

                p1 = baseline_rate
                p2 = baseline_rate * (1 + effect_size)
                p_pooled = (p1 + p2) / 2

                numerator = (
                    z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled))
                    + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
                ) ** 2
                denominator = (p2 - p1) ** 2

                sample_size_per_variant = int(np.ceil(numerator / denominator))

            elif test_type == TestType.CONTINUOUS:
                # For continuous metrics (revenue, time spent, etc.)
                # Using t-test power calculation
                sample_size_per_variant = int(
                    np.ceil(
                        ttest_power(effect_size, power, alpha, alternative="two-sided"),
                    ),
                )

            else:  # COUNT
                # For count data, use similar to continuous
                sample_size_per_variant = int(
                    np.ceil(
                        ttest_power(effect_size, power, alpha, alternative="two-sided"),
                    ),
                )

            # Minimum sample size check
            sample_size_per_variant = max(sample_size_per_variant, self.min_sample_size)

            # Return total sample size (sum across all variants)
            return sample_size_per_variant * 2  # Assuming 2 variants

        except Exception as e:
            self.logger.error(f"Sample size calculation failed: {e}")
            return 1000  # Default fallback

    async def _store_ab_test(self, ab_test: ABTest):
        """Store A/B test in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO ab_tests (
                id, name, description, test_type, target_metric, hypothesis,
                variants, traffic_allocation, start_date, end_date, status,
                sample_size_target, significance_level, power, minimum_detectable_effect,
                created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                ab_test.id,
                ab_test.name,
                ab_test.description,
                ab_test.test_type.value,
                ab_test.target_metric,
                ab_test.hypothesis,
                json.dumps(ab_test.variants),
                json.dumps(ab_test.traffic_allocation),
                ab_test.start_date,
                ab_test.end_date,
                ab_test.status.value,
                ab_test.sample_size_target,
                ab_test.significance_level,
                ab_test.power,
                ab_test.minimum_detectable_effect,
                ab_test.created_at,
                ab_test.created_by,
            ),
        )

        conn.commit()
        conn.close()

    async def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE ab_tests
                SET status = ?, start_date = ?
                WHERE id = ? AND status = ?
            """,
                (
                    TestStatus.RUNNING.value,
                    datetime.now(),
                    test_id,
                    TestStatus.DRAFT.value,
                ),
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                await self._log_experiment_event(test_id, "test_started", {})
                self.logger.info(f"Started A/B test: {test_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to start test {test_id}: {e}")
            return False

    async def record_test_result(
        self,
        test_id: str,
        variant: str,
        metric_name: str,
        metric_value: float,
        user_id: str = None,
        session_id: str = None,
        metadata: dict = None,
    ) -> bool:
        """Record a test result"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO test_results
                (test_id, variant, metric_name, metric_value, user_id, session_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    test_id,
                    variant,
                    metric_name,
                    metric_value,
                    user_id,
                    session_id,
                    json.dumps(metadata) if metadata else None,
                ),
            )

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            self.logger.error(f"Failed to record test result: {e}")
            return False

    async def analyze_test_results(self, test_id: str) -> StatisticalAnalysis | None:
        """Perform statistical analysis of A/B test results"""
        try:
            # Load test configuration
            ab_test = await self._load_ab_test(test_id)
            if not ab_test:
                return None

            # Load test results
            results_data = await self._load_test_results(test_id)
            if not results_data:
                return None

            # Perform statistical analysis based on test type
            if ab_test.test_type == TestType.PROPORTION:
                analysis = await self._analyze_proportion_test(ab_test, results_data)
            elif ab_test.test_type == TestType.CONTINUOUS:
                analysis = await self._analyze_continuous_test(ab_test, results_data)
            else:  # COUNT
                analysis = await self._analyze_count_test(ab_test, results_data)

            # Store analysis results
            if analysis:
                await self._store_statistical_analysis(analysis)

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze test {test_id}: {e}")
            return None

    async def _load_ab_test(self, test_id: str) -> ABTest | None:
        """Load A/B test from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ab_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ABTest(
            id=row[0],
            name=row[1],
            description=row[2],
            test_type=TestType(row[3]),
            target_metric=row[4],
            hypothesis=row[5],
            variants=json.loads(row[6]),
            traffic_allocation=json.loads(row[7]),
            start_date=datetime.fromisoformat(row[8]),
            end_date=datetime.fromisoformat(row[9]) if row[9] else None,
            status=TestStatus(row[10]),
            sample_size_target=row[11],
            significance_level=row[12],
            power=row[13],
            minimum_detectable_effect=row[14],
            created_at=datetime.fromisoformat(row[15]),
            created_by=row[16],
        )

    async def _load_test_results(self, test_id: str) -> pd.DataFrame | None:
        """Load test results from database"""
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT variant, metric_name, metric_value, sample_size, timestamp, user_id
            FROM test_results
            WHERE test_id = ?
            ORDER BY timestamp
        """

        df = pd.read_sql_query(query, conn, params=[test_id])
        conn.close()

        return df if not df.empty else None

    async def _analyze_proportion_test(
        self,
        ab_test: ABTest,
        results_df: pd.DataFrame,
    ) -> StatisticalAnalysis:
        """Analyze proportion-based A/B test (conversion rates, CTR, etc.)"""

        # Group results by variant
        variant_stats = {}
        variants = list(ab_test.variants.keys())

        for variant in variants:
            variant_data = results_df[results_df["variant"] == variant]

            if len(variant_data) == 0:
                continue

            # For proportion tests, metric_value should be 0 or 1 (converted or not)
            conversions = variant_data["metric_value"].sum()
            total = len(variant_data)
            conversion_rate = conversions / total if total > 0 else 0

            variant_stats[variant] = {
                "conversions": int(conversions),
                "total": total,
                "conversion_rate": conversion_rate,
                "std_error": (
                    np.sqrt(conversion_rate * (1 - conversion_rate) / total)
                    if total > 0
                    else 0
                ),
            }

        if len(variant_stats) < 2:
            return None

        # Perform two-proportion z-test
        variant_names = list(variant_stats.keys())
        control = variant_stats[variant_names[0]]
        treatment = variant_stats[variant_names[1]]

        # Z-test for proportions
        successes = np.array([control["conversions"], treatment["conversions"]])
        nobs = np.array([control["total"], treatment["total"]])

        if min(nobs) < 30:  # Not enough data
            statistical_significance = False
            p_value = 1.0
            test_statistic = 0.0
        else:
            try:
                test_statistic, p_value = proportions_ztest(successes, nobs)
            except BaseException:
                p_value = 1.0
                test_statistic = 0.0

        # Effect size (relative difference)
        if control["conversion_rate"] > 0:
            effect_size = (
                treatment["conversion_rate"] - control["conversion_rate"]
            ) / control["conversion_rate"]
        else:
            effect_size = 0.0

        # Statistical significance
        statistical_significance = p_value < ab_test.significance_level

        # Practical significance
        practical_significance = abs(effect_size) >= ab_test.minimum_detectable_effect

        # Confidence interval for difference in proportions
        diff = treatment["conversion_rate"] - control["conversion_rate"]
        se_diff = np.sqrt(control["std_error"] ** 2 + treatment["std_error"] ** 2)
        z_critical = stats.norm.ppf(1 - ab_test.significance_level / 2)
        ci_lower = diff - z_critical * se_diff
        ci_upper = diff + z_critical * se_diff

        # Power calculation (post-hoc)
        power_achieved = self._calculate_achieved_power(
            control["conversion_rate"],
            treatment["conversion_rate"],
            min(nobs),
            ab_test.significance_level,
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            statistical_significance,
            practical_significance,
            effect_size,
            power_achieved,
        )

        return StatisticalAnalysis(
            test_id=ab_test.id,
            variants_data=variant_stats,
            p_value=float(p_value),
            test_statistic=float(test_statistic),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            effect_size=float(effect_size),
            statistical_significance=statistical_significance,
            practical_significance=practical_significance,
            power_achieved=float(power_achieved),
            recommendation=recommendation,
            analysis_date=datetime.now(),
        )

    async def _analyze_continuous_test(
        self,
        ab_test: ABTest,
        results_df: pd.DataFrame,
    ) -> StatisticalAnalysis:
        """Analyze continuous metric A/B test (revenue, time spent, etc.)"""

        variant_stats = {}
        variants = list(ab_test.variants.keys())

        for variant in variants:
            variant_data = results_df[results_df["variant"] == variant]["metric_value"]

            if len(variant_data) == 0:
                continue

            variant_stats[variant] = {
                "count": len(variant_data),
                "mean": float(variant_data.mean()),
                "std": float(variant_data.std()),
                "sem": float(variant_data.sem()),
                "data": variant_data.tolist(),
            }

        if len(variant_stats) < 2:
            return None

        # Perform two-sample t-test
        variant_names = list(variant_stats.keys())
        control_data = variant_stats[variant_names[0]]["data"]
        treatment_data = variant_stats[variant_names[1]]["data"]

        if len(control_data) < 30 or len(treatment_data) < 30:
            # Use Mann-Whitney U test for small samples
            test_statistic, p_value = mannwhitneyu(
                treatment_data,
                control_data,
                alternative="two-sided",
            )
        else:
            # Use t-test for larger samples
            test_statistic, p_value = ttest_ind(
                treatment_data,
                control_data,
                equal_var=False,
            )

        # Effect size (Cohen's d)
        control_mean = variant_stats[variant_names[0]]["mean"]
        treatment_mean = variant_stats[variant_names[1]]["mean"]
        pooled_std = np.sqrt(
            (
                variant_stats[variant_names[0]]["std"] ** 2
                + variant_stats[variant_names[1]]["std"] ** 2
            )
            / 2,
        )

        if pooled_std > 0:
            cohens_d = (treatment_mean - control_mean) / pooled_std
            effect_size = cohens_d
        else:
            effect_size = 0.0

        # Relative effect size
        if control_mean != 0:
            relative_effect = (treatment_mean - control_mean) / abs(control_mean)
        else:
            relative_effect = 0.0

        # Statistical significance
        statistical_significance = p_value < ab_test.significance_level

        # Practical significance
        practical_significance = (
            abs(relative_effect) >= ab_test.minimum_detectable_effect
        )

        # Confidence interval for mean difference
        diff = treatment_mean - control_mean
        se_diff = np.sqrt(
            variant_stats[variant_names[0]]["sem"] ** 2
            + variant_stats[variant_names[1]]["sem"] ** 2,
        )
        df = len(control_data) + len(treatment_data) - 2
        t_critical = stats.t.ppf(1 - ab_test.significance_level / 2, df)
        ci_lower = diff - t_critical * se_diff
        ci_upper = diff + t_critical * se_diff

        # Power achieved
        power_achieved = 0.8  # Simplified - would calculate properly in production

        # Generate recommendation
        recommendation = self._generate_recommendation(
            statistical_significance,
            practical_significance,
            relative_effect,
            power_achieved,
        )

        return StatisticalAnalysis(
            test_id=ab_test.id,
            variants_data=variant_stats,
            p_value=float(p_value),
            test_statistic=float(test_statistic),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            effect_size=float(effect_size),
            statistical_significance=statistical_significance,
            practical_significance=practical_significance,
            power_achieved=float(power_achieved),
            recommendation=recommendation,
            analysis_date=datetime.now(),
        )

    async def _analyze_count_test(
        self,
        ab_test: ABTest,
        results_df: pd.DataFrame,
    ) -> StatisticalAnalysis:
        """Analyze count-based A/B test (clicks, views, etc.)"""
        # Similar to continuous test but adapted for count data
        return await self._analyze_continuous_test(ab_test, results_df)

    def _calculate_achieved_power(
        self,
        p1: float,
        p2: float,
        n: int,
        alpha: float,
    ) -> float:
        """Calculate achieved statistical power"""
        try:
            if p1 == 0 or p2 == 0 or n < 10:
                return 0.5

            # Simplified power calculation
            effect_size = abs(p2 - p1) / np.sqrt(p1 * (1 - p1))
            z_alpha = stats.norm.ppf(1 - alpha / 2)
            z_beta = effect_size * np.sqrt(n / 2) - z_alpha
            power = stats.norm.cdf(z_beta)

            return max(0.0, min(1.0, power))

        except BaseException:
            return 0.5

    def _generate_recommendation(
        self,
        statistical_sig: bool,
        practical_sig: bool,
        effect_size: float,
        power: float,
    ) -> str:
        """Generate test recommendation"""

        if statistical_sig and practical_sig:
            if effect_size > 0:
                return "Deploy treatment variant - statistically and practically significant improvement"
            return "Keep control variant - statistically and practically significant decline in treatment"

        if statistical_sig and not practical_sig:
            return "No action needed - statistically significant but practically insignificant effect"

        if not statistical_sig and practical_sig:
            if power < 0.8:
                return "Continue test - effect size is meaningful but insufficient statistical power"
            return (
                "No clear winner - large effect size but not statistically significant"
            )

        if power < 0.8:
            return "Continue test - insufficient sample size for reliable results"
        return "No significant difference detected - consider alternative approaches"

    async def _store_statistical_analysis(self, analysis: StatisticalAnalysis):
        """Store statistical analysis in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO statistical_analyses (
                test_id, variants_data, p_value, test_statistic, confidence_interval,
                effect_size, statistical_significance, practical_significance,
                power_achieved, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                analysis.test_id,
                json.dumps(analysis.variants_data, default=str),
                analysis.p_value,
                analysis.test_statistic,
                json.dumps(analysis.confidence_interval),
                analysis.effect_size,
                analysis.statistical_significance,
                analysis.practical_significance,
                analysis.power_achieved,
                analysis.recommendation,
            ),
        )

        conn.commit()
        conn.close()

    async def _log_experiment_event(
        self,
        test_id: str,
        event_type: str,
        event_data: dict,
    ):
        """Log experiment event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO experiment_tracking (test_id, event_type, event_data)
            VALUES (?, ?, ?)
        """,
            (test_id, event_type, json.dumps(event_data)),
        )

        conn.commit()
        conn.close()

    async def get_running_tests(self) -> list[dict]:
        """Get all currently running tests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, name, target_metric, start_date, end_date, sample_size_target
            FROM ab_tests
            WHERE status = ?
            ORDER BY start_date DESC
        """,
            (TestStatus.RUNNING.value,),
        )

        tests = []
        for row in cursor.fetchall():
            tests.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "target_metric": row[2],
                    "start_date": row[3],
                    "end_date": row[4],
                    "sample_size_target": row[5],
                },
            )

        conn.close()
        return tests

    async def get_test_summary(self, test_id: str) -> dict | None:
        """Get comprehensive test summary"""

        # Load test details
        ab_test = await self._load_ab_test(test_id)
        if not ab_test:
            return None

        # Load latest analysis
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM statistical_analyses
            WHERE test_id = ?
            ORDER BY analysis_date DESC
            LIMIT 1
        """,
            (test_id,),
        )

        analysis_row = cursor.fetchone()

        # Get current sample sizes
        cursor.execute(
            """
            SELECT variant, COUNT(*)
            FROM test_results
            WHERE test_id = ?
            GROUP BY variant
        """,
            (test_id,),
        )

        sample_sizes = dict(cursor.fetchall())
        conn.close()

        # Compile summary
        summary = {
            "test_details": asdict(ab_test),
            "current_sample_sizes": sample_sizes,
            "total_sample_size": sum(sample_sizes.values()),
            "progress": min(
                1.0,
                sum(sample_sizes.values()) / ab_test.sample_size_target,
            ),
            "days_running": (datetime.now() - ab_test.start_date).days,
            "analysis": None,
        }

        if analysis_row:
            summary["analysis"] = {
                "p_value": analysis_row[3],
                "effect_size": analysis_row[5],
                "statistical_significance": bool(analysis_row[6]),
                "practical_significance": bool(analysis_row[7]),
                "recommendation": analysis_row[9],
                "analysis_date": analysis_row[10],
            }

        return summary

    async def stop_test(self, test_id: str, reason: str = "Completed") -> bool:
        """Stop a running A/B test"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE ab_tests
                SET status = ?, end_date = ?
                WHERE id = ? AND status = ?
            """,
                (
                    TestStatus.COMPLETED.value,
                    datetime.now(),
                    test_id,
                    TestStatus.RUNNING.value,
                ),
            )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                await self._log_experiment_event(
                    test_id,
                    "test_stopped",
                    {"reason": reason},
                )
                self.logger.info(f"Stopped A/B test: {test_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to stop test {test_id}: {e}")
            return False


# Content A/B Testing Integration


class ContentABTesting(ABTestingFramework):
    """Specialized A/B testing for content optimization"""

    async def test_content_variations(
        self,
        variations: list[dict],
        target_metric: str = "engagement_rate",
        duration_days: int = 7,
    ) -> str:
        """Create A/B test for content variations"""

        # Prepare variants
        variants = {}
        traffic_allocation = {}

        for i, variation in enumerate(variations):
            variant_id = f"variant_{chr(65 + i)}"  # A, B, C, etc.
            variants[variant_id] = variation
            traffic_allocation[variant_id] = 1.0 / len(variations)

        # Create test
        test_id = await self.create_ab_test(
            name=f"Content Test - {target_metric}",
            description=f"Testing {len(variations)} content variations for {target_metric}",
            test_type=TestType.CONTINUOUS,
            target_metric=target_metric,
            hypothesis=f"Different content variations will impact {target_metric}",
            variants=variants,
            traffic_allocation=traffic_allocation,
            duration_days=duration_days,
        )

        # Start test immediately
        await self.start_test(test_id)

        return test_id

    async def test_posting_times(
        self,
        times: list[str],
        target_metric: str = "engagement_rate",
    ) -> str:
        """Create A/B test for optimal posting times"""

        variants = {}
        traffic_allocation = {}

        for i, time in enumerate(times):
            variant_id = f"time_{time.replace(':', '')}"
            variants[variant_id] = {"posting_time": time}
            traffic_allocation[variant_id] = 1.0 / len(times)

        test_id = await self.create_ab_test(
            name="Optimal Posting Time Test",
            description=f"Testing posting times: {', '.join(times)}",
            test_type=TestType.CONTINUOUS,
            target_metric=target_metric,
            hypothesis="Different posting times will impact engagement rates",
            variants=variants,
            traffic_allocation=traffic_allocation,
            duration_days=14,
        )

        await self.start_test(test_id)
        return test_id

    async def test_hashtag_strategies(
        self,
        strategies: list[dict],
        target_metric: str = "reach",
    ) -> str:
        """Create A/B test for hashtag strategies"""

        variants = {}
        traffic_allocation = {}

        for i, strategy in enumerate(strategies):
            variant_id = f"hashtag_strategy_{i + 1}"
            variants[variant_id] = strategy
            traffic_allocation[variant_id] = 1.0 / len(strategies)

        test_id = await self.create_ab_test(
            name="Hashtag Strategy Test",
            description="Testing different hashtag strategies for reach optimization",
            test_type=TestType.CONTINUOUS,
            target_metric=target_metric,
            hypothesis="Different hashtag strategies will impact reach",
            variants=variants,
            traffic_allocation=traffic_allocation,
            duration_days=10,
        )

        await self.start_test(test_id)
        return test_id


# Usage and testing


async def main():
    """Main function for testing A/B framework"""

    # Initialize A/B testing framework
    framework = ABTestingFramework()

    # Create a sample A/B test for conversion rate optimization
    print("Creating A/B test for content engagement...")

    variants = {
        "control": {
            "content_type": "standard_post",
            "call_to_action": "Learn more",
            "hashtags": ["#productivity", "#business"],
        },
        "treatment": {
            "content_type": "carousel_post",
            "call_to_action": "Swipe to see more",
            "hashtags": ["#productivity", "#business", "#tips", "#growth"],
        },
    }

    traffic_allocation = {"control": 0.5, "treatment": 0.5}

    test_id = await framework.create_ab_test(
        name="Carousel vs Standard Post Engagement",
        description="Testing whether carousel posts drive higher engagement than standard posts",
        test_type=TestType.CONTINUOUS,
        target_metric="engagement_rate",
        hypothesis="Carousel posts will achieve higher engagement rates than standard posts",
        variants=variants,
        traffic_allocation=traffic_allocation,
        duration_days=14,
        minimum_detectable_effect=0.15,  # 15% improvement
    )

    print(f"Created test: {test_id}")

    # Start the test
    success = await framework.start_test(test_id)
    print(f"Test started: {success}")

    # Simulate some test results
    print("Simulating test results...")

    import random

    for i in range(200):  # 200 samples per variant
        # Control variant results
        engagement_rate = random.normalvariate(3.5, 0.8)  # Mean 3.5%, std 0.8%
        await framework.record_test_result(
            test_id,
            "control",
            "engagement_rate",
            max(0, engagement_rate),
            user_id=f"user_{i}_control",
        )

        # Treatment variant results (slightly higher)
        engagement_rate = random.normalvariate(4.2, 0.9)  # Mean 4.2%, std 0.9%
        await framework.record_test_result(
            test_id,
            "treatment",
            "engagement_rate",
            max(0, engagement_rate),
            user_id=f"user_{i}_treatment",
        )

    # Analyze results
    print("Analyzing test results...")
    analysis = await framework.analyze_test_results(test_id)

    if analysis:
        print("\n=== A/B TEST ANALYSIS ===")
        print(f"P-value: {analysis.p_value:.4f}")
        print(f"Effect Size: {analysis.effect_size:.3f}")
        print(f"Statistical Significance: {analysis.statistical_significance}")
        print(f"Practical Significance: {analysis.practical_significance}")
        print(f"Confidence Interval: {analysis.confidence_interval}")
        print(f"Power Achieved: {analysis.power_achieved:.2f}")
        print(f"Recommendation: {analysis.recommendation}")

        print("\nVariant Performance:")
        for variant, stats in analysis.variants_data.items():
            print(f"  {variant}: {stats}")

    # Get test summary
    summary = await framework.get_test_summary(test_id)
    print(f"\nTest Progress: {summary['progress']:.1%}")
    print(f"Days Running: {summary['days_running']}")

    print("\n=== A/B Testing Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
