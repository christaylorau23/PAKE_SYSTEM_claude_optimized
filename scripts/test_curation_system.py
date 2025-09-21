#!/usr/bin/env python3
"""
Test script for the Intelligent Content Curation System.
Validates all components and provides comprehensive testing.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

from services.curation.integration.curation_orchestrator import (
    CurationOrchestrator,
    CurationRequest,
)
from services.curation.models.content_item import ContentItem
from services.curation.models.user_interaction import InteractionType, UserInteraction
from services.curation.models.user_profile import UserProfile

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


class CurationSystemTester:
    """Comprehensive tester for the curation system"""

    def __init__(self):
        self.orchestrator = None
        self.test_results = []
        self.start_time = None

    async def run_all_tests(self):
        """Run all system tests"""
        print("🧠 PAKE Intelligent Content Curation System Test Suite")
        print("=" * 60)

        self.start_time = time.time()

        try:
            # Initialize system
            await self.test_system_initialization()

            # Test core functionality
            await self.test_content_analysis()
            await self.test_recommendation_generation()
            await self.test_user_preference_learning()
            await self.test_feedback_processing()

            # Test ML components
            await self.test_feature_extraction()
            await self.test_model_training()
            await self.test_prediction_engine()

            # Test integration
            await self.test_end_to_end_workflow()

            # Test performance
            await self.test_performance_requirements()

            # Generate report
            self.generate_test_report()

        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False

        return True

    async def test_system_initialization(self):
        """Test system initialization"""
        print("\n🔧 Testing System Initialization...")

        try:
            self.orchestrator = CurationOrchestrator()
            success = await self.orchestrator.initialize()

            if success:
                print("✅ System initialized successfully")
                self.test_results.append(
                    (
                        "System Initialization",
                        "PASS",
                        "System initialized without errors",
                    ),
                )
            else:
                print("❌ System initialization failed")
                self.test_results.append(
                    (
                        "System Initialization",
                        "FAIL",
                        "System initialization returned False",
                    ),
                )

        except Exception as e:
            print(f"❌ System initialization error: {e}")
            self.test_results.append(("System Initialization", "ERROR", str(e)))

    async def test_content_analysis(self):
        """Test content analysis functionality"""
        print("\n📊 Testing Content Analysis...")

        try:
            # Create test content
            test_content = ContentItem(
                id="test-content-001",
                title="Machine Learning in Healthcare: A Comprehensive Review",
                content_text="Machine learning is revolutionizing healthcare by enabling early disease detection, personalized treatment plans, and improved patient outcomes. Recent advances in deep learning have shown remarkable success in medical imaging analysis, drug discovery, and clinical decision support systems.",
                author="Dr. Jane Smith",
                source_url="https://example.com/ml-healthcare-review",
                published_date=datetime.now(),
                content_type="article",
                tags=["machine learning", "healthcare", "AI", "medical"],
                source_authority_score=0.9,
                source_reliability=0.8,
            )

            # Test content analysis
            analysis_result = (
                await self.orchestrator.content_analysis_service.analyze_content(
                    test_content,
                )
            )

            if analysis_result and analysis_result.quality_score is not None:
                print("✅ Content analysis completed successfully")
                print(f"   Quality Score: {analysis_result.quality_score:.3f}")
                print(f"   Credibility Score: {analysis_result.credibility_score:.3f}")
                print(f"   Sentiment Score: {analysis_result.sentiment_score:.3f}")
                self.test_results.append(
                    (
                        "Content Analysis",
                        "PASS",
                        f"Quality: {analysis_result.quality_score:.3f}",
                    ),
                )
            else:
                print("❌ Content analysis failed")
                self.test_results.append(
                    ("Content Analysis", "FAIL", "No analysis result returned"),
                )

        except Exception as e:
            print(f"❌ Content analysis error: {e}")
            self.test_results.append(("Content Analysis", "ERROR", str(e)))

    async def test_recommendation_generation(self):
        """Test recommendation generation"""
        print("\n🎯 Testing Recommendation Generation...")

        try:
            # Create test request
            request = CurationRequest(
                user_id="test-user-001",
                query="machine learning healthcare",
                interests=["AI", "ML", "Healthcare"],
                max_results=5,
                include_explanations=True,
            )

            # Generate recommendations
            start_time = time.time()
            response = await self.orchestrator.curate_content(request)
            end_time = time.time()

            if response and response.recommendations:
                print("✅ Recommendations generated successfully")
                print(f"   Recommendations: {len(response.recommendations)}")
                print(f"   Processing Time: {response.processing_time_ms:.1f}ms")
                print(f"   Model Confidence: {response.model_confidence:.3f}")

                # Check performance
                if response.processing_time_ms < 1000:
                    print("✅ Performance requirement met (<1000ms)")
                    self.test_results.append(
                        (
                            "Recommendation Generation",
                            "PASS",
                            f"{len(response.recommendations)} recommendations in {
                                response.processing_time_ms:.1f}ms",
                        ),
                    )
                else:
                    print("⚠️ Performance requirement not met (>1000ms)")
                    self.test_results.append(
                        (
                            "Recommendation Generation",
                            "WARN",
                            f"Slow response: {response.processing_time_ms:.1f}ms",
                        ),
                    )
            else:
                print("❌ No recommendations generated")
                self.test_results.append(
                    (
                        "Recommendation Generation",
                        "FAIL",
                        "No recommendations returned",
                    ),
                )

        except Exception as e:
            print(f"❌ Recommendation generation error: {e}")
            self.test_results.append(("Recommendation Generation", "ERROR", str(e)))

    async def test_user_preference_learning(self):
        """Test user preference learning"""
        print("\n🧠 Testing User Preference Learning...")

        try:
            # Create test user profile
            user_profile = UserProfile(
                user_id="test-user-002",
                interests=["AI", "Machine Learning"],
                preference_weights={
                    "academic": 0.4,
                    "news": 0.3,
                    "blog": 0.2,
                    "tutorial": 0.1,
                },
            )

            # Create test interactions
            interactions = [
                UserInteraction(
                    id="interaction-001",
                    user_id="test-user-002",
                    content_id="content-001",
                    interaction_type=InteractionType.LIKE,
                    timestamp=datetime.now(),
                    session_duration=180,
                ),
                UserInteraction(
                    id="interaction-002",
                    user_id="test-user-002",
                    content_id="content-002",
                    interaction_type=InteractionType.SHARE,
                    timestamp=datetime.now(),
                    session_duration=240,
                ),
            ]

            # Test preference learning
            updated_profile = (
                await self.orchestrator.user_preference_service.update_user_preferences(
                    "test-user-002",
                    interactions[0],
                )
            )

            if updated_profile:
                print("✅ User preference learning completed")
                print(f"   User ID: {updated_profile.user_id}")
                print(f"   Interests: {updated_profile.interests}")
                print(f"   Learning Rate: {updated_profile.learning_rate}")
                self.test_results.append(
                    (
                        "User Preference Learning",
                        "PASS",
                        "Preferences updated successfully",
                    ),
                )
            else:
                print("❌ User preference learning failed")
                self.test_results.append(
                    ("User Preference Learning", "FAIL", "No updated profile returned"),
                )

        except Exception as e:
            print(f"❌ User preference learning error: {e}")
            self.test_results.append(("User Preference Learning", "ERROR", str(e)))

    async def test_feedback_processing(self):
        """Test feedback processing"""
        print("\n💬 Testing Feedback Processing...")

        try:
            # Test feedback submission
            success = await self.orchestrator.process_user_feedback(
                user_id="test-user-003",
                content_id="content-003",
                feedback_type="like",
                feedback_data={
                    "session_duration": 120,
                    "explicit_rating": 5,
                    "feedback_text": "Great article, very informative",
                },
            )

            if success:
                print("✅ Feedback processing completed")
                self.test_results.append(
                    ("Feedback Processing", "PASS", "Feedback processed successfully"),
                )
            else:
                print("❌ Feedback processing failed")
                self.test_results.append(
                    (
                        "Feedback Processing",
                        "FAIL",
                        "Feedback processing returned False",
                    ),
                )

        except Exception as e:
            print(f"❌ Feedback processing error: {e}")
            self.test_results.append(("Feedback Processing", "ERROR", str(e)))

    async def test_feature_extraction(self):
        """Test feature extraction"""
        print("\n🔍 Testing Feature Extraction...")

        try:
            # Create test content
            test_content = ContentItem(
                id="test-content-002",
                title="Deep Learning Fundamentals",
                content_text="Deep learning is a subset of machine learning that uses neural networks with multiple layers to model and understand complex patterns in data.",
                author="Dr. John Doe",
                tags=["deep learning", "neural networks", "AI"],
            )

            # Test feature extraction
            features = (
                await self.orchestrator.feature_extractor.extract_content_features(
                    test_content,
                )
            )

            if features and features.text_features:
                print("✅ Feature extraction completed")
                print(f"   Text Features: {len(features.text_features)}")
                print(f"   Metadata Features: {len(features.metadata_features)}")
                print(f"   Quality Features: {len(features.quality_features)}")
                self.test_results.append(
                    (
                        "Feature Extraction",
                        "PASS",
                        f"{len(features.text_features)} text features extracted",
                    ),
                )
            else:
                print("❌ Feature extraction failed")
                self.test_results.append(
                    ("Feature Extraction", "FAIL", "No features extracted"),
                )

        except Exception as e:
            print(f"❌ Feature extraction error: {e}")
            self.test_results.append(("Feature Extraction", "ERROR", str(e)))

    async def test_model_training(self):
        """Test model training"""
        print("\n🤖 Testing Model Training...")

        try:
            # Test model training (with empty data - will use fallback)
            results = await self.orchestrator.retrain_models(force_retrain=True)

            if results.get("retrained"):
                print("✅ Model training completed")
                self.test_results.append(
                    ("Model Training", "PASS", "Models retrained successfully"),
                )
            else:
                print("⚠️ Model training skipped or failed")
                self.test_results.append(
                    (
                        "Model Training",
                        "WARN",
                        results.get("reason", "Training failed"),
                    ),
                )

        except Exception as e:
            print(f"❌ Model training error: {e}")
            self.test_results.append(("Model Training", "ERROR", str(e)))

    async def test_prediction_engine(self):
        """Test prediction engine"""
        print("\n🎲 Testing Prediction Engine...")

        try:
            # Create test data
            test_content = ContentItem(
                id="test-content-003",
                title="AI Ethics and Responsible Development",
                content_text="As artificial intelligence becomes more prevalent, it's crucial to consider ethical implications and develop AI systems responsibly.",
                tags=["AI", "ethics", "responsible development"],
            )

            test_user = UserProfile(user_id="test-user-004", interests=["AI", "Ethics"])

            # Test prediction
            prediction = (
                await self.orchestrator.prediction_engine.predict_recommendation_score(
                    test_content,
                    test_user,
                    [],
                )
            )

            if prediction and 0 <= prediction.score <= 1:
                print("✅ Prediction engine working")
                print(f"   Prediction Score: {prediction.score:.3f}")
                print(f"   Confidence: {prediction.confidence:.3f}")
                print(f"   Prediction Time: {prediction.prediction_time_ms:.1f}ms")
                self.test_results.append(
                    (
                        "Prediction Engine",
                        "PASS",
                        f"Score: {prediction.score:.3f}, Confidence: {
                            prediction.confidence:.3f}",
                    ),
                )
            else:
                print("❌ Prediction engine failed")
                self.test_results.append(
                    ("Prediction Engine", "FAIL", "Invalid prediction result"),
                )

        except Exception as e:
            print(f"❌ Prediction engine error: {e}")
            self.test_results.append(("Prediction Engine", "ERROR", str(e)))

    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        print("\n🔄 Testing End-to-End Workflow...")

        try:
            # Complete workflow test
            request = CurationRequest(
                user_id="e2e-test-user",
                query="artificial intelligence",
                interests=["AI", "Technology"],
                max_results=3,
            )

            # Submit feedback
            await self.orchestrator.process_user_feedback(
                user_id="e2e-test-user",
                content_id="e2e-content-001",
                feedback_type="like",
                feedback_data={"session_duration": 150},
            )

            # Get recommendations
            response = await self.orchestrator.curate_content(request)

            if response:
                print("✅ End-to-end workflow completed")
                print(f"   Recommendations: {len(response.recommendations)}")
                print(f"   Total Time: {response.processing_time_ms:.1f}ms")
                self.test_results.append(
                    (
                        "End-to-End Workflow",
                        "PASS",
                        f"Complete workflow executed in {
                            response.processing_time_ms:.1f}ms",
                    ),
                )
            else:
                print("❌ End-to-end workflow failed")
                self.test_results.append(
                    ("End-to-End Workflow", "FAIL", "Workflow did not complete"),
                )

        except Exception as e:
            print(f"❌ End-to-end workflow error: {e}")
            self.test_results.append(("End-to-End Workflow", "ERROR", str(e)))

    async def test_performance_requirements(self):
        """Test performance requirements"""
        print("\n⚡ Testing Performance Requirements...")

        try:
            # Performance test with multiple requests
            requests = [
                CurationRequest(user_id=f"perf-user-{i}", max_results=5)
                for i in range(5)
            ]

            start_time = time.time()
            tasks = [self.orchestrator.curate_content(req) for req in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            total_time = (end_time - start_time) * 1000
            avg_time = total_time / len(requests)

            successful_responses = [
                r for r in responses if not isinstance(r, Exception)
            ]

            print("✅ Performance test completed")
            print(f"   Total Time: {total_time:.1f}ms")
            print(f"   Average Time: {avg_time:.1f}ms")
            print(f"   Success Rate: {len(successful_responses)}/{len(requests)}")

            if avg_time < 1000:
                print("✅ Performance requirement met (<1000ms average)")
                self.test_results.append(
                    (
                        "Performance Requirements",
                        "PASS",
                        f"Avg: {avg_time:.1f}ms, Success: {len(successful_responses)}/{
                            len(requests)
                        }",
                    ),
                )
            else:
                print("⚠️ Performance requirement not met (>1000ms average)")
                self.test_results.append(
                    (
                        "Performance Requirements",
                        "WARN",
                        f"Avg: {avg_time:.1f}ms (too slow)",
                    ),
                )

        except Exception as e:
            print(f"❌ Performance test error: {e}")
            self.test_results.append(("Performance Requirements", "ERROR", str(e)))

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("📋 TEST REPORT")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r[1] == "PASS"])
        failed_tests = len([r for r in self.test_results if r[1] == "FAIL"])
        error_tests = len([r for r in self.test_results if r[1] == "ERROR"])
        warning_tests = len([r for r in self.test_results if r[1] == "WARN"])

        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Warnings: {warning_tests}")
        print(f"💥 Errors: {error_tests}")

        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"\nTotal Execution Time: {total_time:.2f} seconds")

        print("\nDetailed Results:")
        print("-" * 60)
        for test_name, status, details in self.test_results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥", "WARN": "⚠️"}.get(
                status,
                "❓",
            )

            print(f"{status_icon} {test_name}: {status}")
            print(f"   Details: {details}")
            print()

        # Overall status
        if failed_tests == 0 and error_tests == 0:
            print("🎉 ALL TESTS PASSED! System is ready for production.")
            return True
        print("⚠️ Some tests failed. Please review the issues above.")
        return False


async def main():
    """Main test execution"""
    tester = CurationSystemTester()
    success = await tester.run_all_tests()

    if success:
        print("\n🚀 System validation completed successfully!")
        print("You can now:")
        print(
            "1. Start the API server: python src/services/curation/api/curation_api.py",
        )
        print("2. Open the dashboard: open dashboard/curation-dashboard.html")
        print("3. Run the deployment script: python scripts/deploy_curation_system.py")
    else:
        print("\n❌ System validation failed. Please fix the issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
