# PAKE System Complexity Analysis Report
## Analysis of: src
## Minimum Complexity Threshold: 10
## Total Functions/Methods Analyzed: 188

## High Complexity Functions (Priority Refactoring Targets)

| File | Function/Method | Complexity | Rating | Line |
|------|----------------|------------|--------|------|
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService.generate_synthesis_insights | 29 | C (High) | 663 |
| src/services/wealth/trend_detection_engine.py | main_trend_detection_demo | 29 | C (High) | 1528 |
| src/services/ingestion/pubmed_service.py | PubMedService._apply_query_filters | 25 | C (High) | 452 |
| src/services/ingestion/arxiv_enhanced_service.py | ArxivEnhancedService.search_papers | 23 | C (High) | 211 |
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService.analyze_correlations | 22 | C (High) | 437 |
| src/services/secrets/migration_service.py | SecretsMigrationService._audit_kubernetes_secrets | 22 | C (High) | 310 |
| src/services/ingestion/firecrawl_service.py | FirecrawlService.scrape_url | 21 | C (High) | 241 |
| src/pake_system/core/config.py | Settings.load_secrets_from_vault | 20 | B (Moderate) | 113 |
| src/services/ingestion/pubmed_service.py | PubMedService.parse_pubmed_response | 19 | B (Moderate) | 516 |
| src/services/ml/feature_engineering.py | FeatureSelector.fit | 19 | B (Moderate) | 459 |
| src/ai-security-monitor.py | MockLLMAnalyzer._detect_security_patterns | 18 | B (Moderate) | 190 |
| src/services/ai/cognitive_analysis_engine.py | CognitiveAnalysisEngine.analyze_content | 18 | B (Moderate) | 809 |
| src/services/ingestion/rss_feed_service.py | RSSFeedService.fetch_feed | 18 | B (Moderate) | 128 |
| src/services/curation/services/feedback_processing_service.py | FeedbackProcessingService.detect_feedback_anomalies | 18 | B (Moderate) | 539 |
| src/services/analytics/correlation_engine.py | CorrelationEngine._generate_mock_metrics_data | 17 | B (Moderate) | 900 |
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService.detect_emerging_topics | 17 | B (Moderate) | 301 |
| src/services/wealth/google_trends_analyzer.py | GoogleTrendsAnalyzer._analyze_interest_data | 17 | B (Moderate) | 445 |
| src/services/curation/services/user_preference_service.py | UserPreferenceService.analyze_interest_evolution | 17 | B (Moderate) | 310 |
| src/utils/circuit_breaker.py | CircuitBreaker.call | 16 | B (Moderate) | 316 |
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService.detect_communities | 16 | B (Moderate) | 556 |
| src/services/admin/admin_dashboard_service.py | AdminDashboardService.perform_user_action | 16 | B (Moderate) | 264 |
| src/services/ml/training_pipeline.py | TrainingOrchestrator._execute_training_job | 16 | B (Moderate) | 728 |
| src/services/trends/apis/api_health_monitor.py | APIHealthMonitor.get_health_summary | 16 | B (Moderate) | 170 |
| src/services/curation/services/user_preference_service.py | UserPreferenceService._calculate_preference_stability | 16 | B (Moderate) | 1146 |
| src/api/enterprise/search_endpoints.py | perform_search | 16 | B (Moderate) | 26 |
| src/utils/metrics.py | MetricsStore.get_prometheus_metrics | 15 | B (Moderate) | 211 |
| src/utils/async_metrics.py | AsyncMetricsStore.get_prometheus_metrics_async | 15 | B (Moderate) | 350 |
| src/utils/async_metrics.py | AsyncMetricsStore.get_prometheus_metrics_sync | 15 | B (Moderate) | 481 |
| src/codemods/engineering_plan_codemods.py | ContextPassingTransformer.leave_FunctionDef | 15 | B (Moderate) | 239 |
| src/services/tenant/tenant_management_service.py | TenantManagementService.update_tenant | 15 | B (Moderate) | 314 |
| src/services/ingestion/rss_service.py | RSSFeedService.fetch_feed | 15 | B (Moderate) | 112 |
| src/services/ingestion/pubmed_service.py | PubMedService._build_esearch_query | 15 | B (Moderate) | 156 |
| src/services/ingestion/social_media_service.py | SocialMediaService._apply_content_filters | 15 | B (Moderate) | 618 |
| src/services/ingestion/rss_feed_service.py | RSSFeedService._filter_items | 15 | B (Moderate) | 446 |
| src/services/auth/multi_tenant_auth_service.py | MultiTenantAuthService.authenticate_user | 15 | B (Moderate) | 203 |
| src/services/wealth/trend_detection_engine.py | TrendDetectionEngine._determine_trend_stage | 15 | B (Moderate) | 1005 |
| src/services/wealth/trend_detection_engine.py | _classify_keyword_category | 15 | B (Moderate) | 1671 |
| src/services/secrets/vault_config.py | validate_vault_config | 15 | B (Moderate) | 399 |
| src/services/ai/content_routing_engine.py | IntelligentRouter._evaluate_rule_conditions | 14 | B (Moderate) | 326 |
| src/services/analytics/correlation_engine.py | CorrelationEngine.analyze_time_series_correlation | 14 | B (Moderate) | 415 |
| src/services/testing/migration_validator.py | MigrationValidator.validate_migrations | 14 | B (Moderate) | 150 |
| src/services/ingestion/rss_service.py | RSSFeedService._parse_rss_item | 14 | B (Moderate) | 315 |
| src/services/ingestion/orchestrator.py | IngestionOrchestrator._execute_single_source | 14 | B (Moderate) | 571 |
| src/services/security/bandit_sast_integration.py | BanditSASTIntegration._check_s603_compliance | 14 | B (Moderate) | 244 |
| src/services/auth/multi_tenant_auth_service.py | MultiTenantAuthService._validate_REDACTED_SECRET | 14 | B (Moderate) | 764 |
| src/services/wealth/trend_detection_engine.py | TrendDetectionEngine._synthesize_category_trends | 14 | B (Moderate) | 814 |
| src/services/ml/content_summarization_service.py | ContentSummarizationService._score_sentence | 14 | B (Moderate) | 361 |
| src/services/ml/training_pipeline.py | SklearnTrainer._get_model_class | 14 | B (Moderate) | 312 |
| src/services/trends/intelligence/investment_mapper.py | InvestmentMapper.get_portfolio_recommendations | 14 | B (Moderate) | 590 |
| src/services/trends/intelligence/trend_analyzer.py | TrendAnalyzer._predict_lifecycle_stage | 14 | B (Moderate) | 149 |
| src/services/curation/services/recommendation_service.py | RecommendationService._apply_diversity_reranking | 14 | B (Moderate) | 678 |
| src/pake_system/auth/security.py | validate_password_strength | 14 | B (Moderate) | 144 |
| src/pake.py | PAKECommandLineInterface._handle_logs | 13 | B (Moderate) | 384 |
| src/cosmic_demo.py | CosmicDemo.run_demo | 13 | B (Moderate) | 24 |
| src/codemods/datetime_timezone_transformer.py | ComprehensiveDTZTransformer.leave_Call | 13 | B (Moderate) | 46 |
| src/middleware/input_validation.py | RequestValidator.validate_request_data | 13 | B (Moderate) | 268 |
| src/services/ai/content_routing_engine.py | ContentRoutingEngine.route_content | 13 | B (Moderate) | 542 |
| src/services/analytics/trend_analysis_service.py | TrendAnalysisService.compare_trends | 13 | B (Moderate) | 845 |
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService.create_alerts | 13 | B (Moderate) | 882 |
| src/services/agents/supervisor_agent.py | SupervisorAgent._execute_tasks_parallel | 13 | B (Moderate) | 431 |
| src/services/ingestion/rss_service.py | RSSFeedService._parse_atom_entry | 13 | B (Moderate) | 393 |
| src/services/logging/logging_config_service.py | LoggingConfigService.validate_environment | 13 | B (Moderate) | 514 |
| src/services/wealth/automated_signal_generator.py | AutomatedSignalGenerator._classify_signal | 13 | B (Moderate) | 950 |
| src/services/user/search_history_service.py | SearchHistoryService.get_user_search_history | 13 | B (Moderate) | 144 |
| src/services/secrets/vault_service.py | VaultIntegrationService._authenticate | 13 | B (Moderate) | 132 |
| src/services/ml/knowledge_graph_service.py | KnowledgeGraphService._generate_topic_edges | 13 | B (Moderate) | 374 |
| src/domain/models/user.py | UserUpdate.apply_to_user | 13 | B (Moderate) | 314 |
| src/utils/secure_serialization.py | SecureSerializer.deserialize | 12 | B (Moderate) | 123 |
| src/utils/error_handling.py | with_retry | 12 | B (Moderate) | 364 |
| src/utils/error_handling.py | decorator | 12 | B (Moderate) | 367 |
| src/codemods/context_passing_transformer.py | ContextPassingTransformer.leave_FunctionDef | 12 | B (Moderate) | 132 |
| src/codemods/logging_refactoring_codemod.py | LogCallRefactoringTransformer._add_structlog_imports | 12 | B (Moderate) | 276 |
| src/security/tenant_isolation_enforcer.py | TenantIsolationEnforcer.validate_input_parameters | 12 | B (Moderate) | 378 |
| src/services/cognitive/prompt_evolution_system.py | PromptEvolutionSystem._mutate_organism | 12 | B (Moderate) | 693 |
| src/services/workflows/task_management.py | TaskManager._setup_default_assignment_rules | 12 | B (Moderate) | 130 |
| src/services/ai/cognitive_analysis_engine.py | ContentCategorizer.analyze_content | 12 | B (Moderate) | 719 |
| src/services/ai/query_expansion_engine.py | QueryExpansionEngine.expand_query | 12 | B (Moderate) | 756 |
| src/services/analytics/trend_analysis_service.py | TrendAnalysisService._detect_trend_type | 12 | B (Moderate) | 264 |
| src/services/admin/admin_dashboard_service.py | AdminDashboardService.perform_maintenance_operation | 12 | B (Moderate) | 647 |
| src/services/agents/pubmed_worker.py | PubMedWorker.process_task | 12 | B (Moderate) | 119 |
| src/services/agents/pubmed_worker.py | PubMedWorker._enhance_content_metadata | 12 | B (Moderate) | 267 |
| src/services/agents/cognitive_worker.py | CognitiveWorker._generate_optimization_recommendations | 12 | B (Moderate) | 539 |
| src/services/ingestion/orchestrator.py | IngestionOrchestrator.execute_ingestion_plan | 12 | B (Moderate) | 448 |
| src/services/ingestion/cached_orchestrator.py | CachedIngestionOrchestrator.execute_ingestion_plan | 12 | B (Moderate) | 153 |
| src/services/ingestion/pubmed_service.py | PubMedService.search_papers | 12 | B (Moderate) | 323 |
| src/services/ingestion/rss_feed_service.py | RSSFeedService._parse_feed_content | 12 | B (Moderate) | 260 |
| src/services/security/security_workflow.py | SecurityTriageSystem._update_metrics | 12 | B (Moderate) | 542 |
| src/services/trends/apis/api_health_monitor.py | APIHealthMonitor.get_performance_metrics | 12 | B (Moderate) | 354 |
| src/services/trends/intelligence/prediction_engine.py | PredictionEngine._predict_next_lifecycle_stage | 12 | B (Moderate) | 477 |
| src/services/curation/services/content_analysis_service.py | ContentAnalysisService._calculate_completeness_score | 12 | B (Moderate) | 408 |
| src/services/curation/services/feedback_processing_service.py | FeedbackProcessingService.generate_system_feedback_metrics | 12 | B (Moderate) | 446 |
| src/services/curation/services/recommendation_service.py | RecommendationService._filter_candidates | 12 | B (Moderate) | 232 |
| src/domain/models/content.py | ContentUpdate.apply_to_content | 12 | B (Moderate) | 390 |
| src/utils/distributed_cache.py | DistributedCache._serialize_value | 11 | B (Moderate) | 206 |
| src/utils/flaky_test_management.py | pytest_runtest_logreport | 11 | B (Moderate) | 539 |
| src/utils/error_handling.py | ErrorHandler._categorize_exception | 11 | B (Moderate) | 218 |
| src/utils/flaky_test_tracker.py | FlakyTestTracker.generate_flaky_test_report | 11 | B (Moderate) | 492 |
| src/utils/synchronization_primitives.py | AsyncLockManager.acquire_lock | 11 | B (Moderate) | 75 |
| src/utils/async_task_queue.py | AsyncTaskQueue.get_queue_stats | 11 | B (Moderate) | 445 |
| src/codemods/codemod_runner.py | CodemodRunner.execute_plan | 11 | B (Moderate) | 183 |
| src/security/tenant_isolation_enforcer.py | TenantIsolationEnforcer.monitor_authentication_patterns | 11 | B (Moderate) | 484 |
| src/services/tenant/tenant_management_service.py | TenantManagementService.create_tenant | 11 | B (Moderate) | 151 |
| src/services/cognitive/cosmic_calibration_coordinator.py | CosmicCalibrationCoordinator._make_coordination_decisions | 11 | B (Moderate) | 497 |
| src/services/ai/semantic_search_engine.py | SemanticSearchEngine.semantic_search | 11 | B (Moderate) | 666 |
| src/services/ai/cognitive_analysis_engine.py | QualityAssessor.analyze_content | 11 | B (Moderate) | 560 |
| src/services/ai/query_expansion_engine.py | SemanticExpander.generate_expansions | 11 | B (Moderate) | 531 |
| src/services/ai/adaptive_learning_engine.py | AdaptiveLearningEngine._update_user_profile | 11 | B (Moderate) | 329 |
| src/services/analytics/trend_analysis_service.py | TrendAnalysisService._detect_trend_breakpoints | 11 | B (Moderate) | 610 |
| src/services/analytics/advanced_analytics_engine.py | AdvancedAnalyticsEngine._synthesize_insights | 11 | B (Moderate) | 441 |
| src/services/analytics/predictive_analytics_service.py | PredictiveAnalyticsService.forecast_time_series | 11 | B (Moderate) | 80 |
| src/services/agents/performance_worker.py | PerformanceWorker._process_system_monitoring | 11 | B (Moderate) | 318 |
| src/services/authentication/jwt_auth_service.py | JWTAuthenticationService.validate_REDACTED_SECRET_complexity | 11 | B (Moderate) | 113 |
| src/services/observability/telemetry.py | TelemetrySystem.initialize | 11 | B (Moderate) | 126 |
| src/services/ingestion/production_orchestrator.py | ProductionIngestionOrchestrator._extract_historical_context | 11 | B (Moderate) | 245 |
| src/services/ingestion/production_orchestrator.py | ProductionIngestionOrchestrator._fallback_optimization | 11 | B (Moderate) | 328 |
| src/services/security/security_workflow.py | SecurityTriageSystem._rule_matches | 11 | B (Moderate) | 329 |
| src/services/wealth/mobile_notification_service.py | APNSProvider.send_notification | 11 | B (Moderate) | 265 |
| src/services/wealth/mobile_notification_service.py | MobileNotificationService.send_notification | 11 | B (Moderate) | 808 |
| src/services/nlp/intelligence_nlp_service.py | IntelligenceNLPService.analyze_document | 11 | B (Moderate) | 380 |
| src/services/nlp/intelligence_nlp_service.py | IntelligenceNLPService.extract_topics | 11 | B (Moderate) | 712 |
| src/services/nlp/advanced_nlp_service.py | AdvancedNLPService._extract_key_phrases | 11 | B (Moderate) | 474 |
| src/services/api/intelligence_graphql_service.py | Mutation.run_comprehensive_analysis | 11 | B (Moderate) | 634 |
| src/services/secrets/migration_service.py | SecretsMigrationService._parse_config_file | 11 | B (Moderate) | 367 |
| src/services/ml/analytics_aggregation_service.py | MLAnalyticsAggregationService._manage_research_session | 11 | B (Moderate) | 178 |
| src/services/ml/analytics_aggregation_service.py | MLAnalyticsAggregationService.generate_dashboard_metrics | 11 | B (Moderate) | 254 |
| src/services/ml/analytics_aggregation_service.py | MLAnalyticsAggregationService._identify_topic_clusters | 11 | B (Moderate) | 483 |
| src/services/realtime/websocket_manager.py | WebSocketManager._cleanup_task | 11 | B (Moderate) | 632 |
| src/services/curation/integration/curation_orchestrator.py | CurationOrchestrator._generate_reasoning | 11 | B (Moderate) | 470 |
| src/services/curation/services/content_analysis_service.py | ContentAnalysisService.classify_content_type | 11 | B (Moderate) | 640 |
| src/services/curation/services/content_analysis_service.py | ContentAnalysisService.classify_sync | 11 | B (Moderate) | 647 |
| src/services/curation/services/feedback_processing_service.py | FeedbackProcessingService._assess_feedback_quality | 11 | B (Moderate) | 614 |
| src/services/curation/ml/model_trainer.py | ModelTrainer.train_content_quality_model | 11 | B (Moderate) | 144 |
| src/pake.py | PAKECommandLineInterface._handle_health | 10 | A (Low) | 456 |
| src/run_simple_automation.py | SimpleAutomationHandler.process_file | 10 | A (Low) | 40 |
| src/utils/secure_serialization.py | SecureSerializer.serialize | 10 | A (Low) | 73 |
| src/utils/flaky_test_management.py | FlakyTestTracker.generate_report | 10 | A (Low) | 427 |
| src/utils/exceptions.py | convert_standard_exception | 10 | A (Low) | 508 |
| src/utils/security_guards.py | PromptInjectionDetector.detect | 10 | A (Low) | 177 |
| src/codemods/codemod_runner.py | CodemodRunner.generate_report | 10 | A (Low) | 253 |
| src/codemods/engineering_plan_codemods.py | ContextPassingTransformer.leave_Call | 10 | A (Low) | 332 |
| src/services/semantic/lightweight_semantic_service.py | LightweightSemanticService.add_documents | 10 | A (Low) | 113 |
| src/services/semantic/lightweight_semantic_service.py | LightweightSemanticService.get_analytics | 10 | A (Low) | 398 |
| src/services/secrets_manager/vault_client.py | PAKESecretsManager.export_all_secrets | 10 | A (Low) | 334 |
| src/services/workflows/demo_proactive_workflows.py | demonstrate_proactive_workflows | 10 | A (Low) | 64 |
| src/services/caching/redis_cache_service.py | RedisCacheService.get | 10 | A (Low) | 162 |
| src/services/caching/redis_cache_strategy.py | MultiLayeredCacheStrategy.get | 10 | A (Low) | 754 |
| src/services/business/user_service_refactored.py | UserService._validate_user_data | 10 | A (Low) | 254 |
| src/services/ai/cognitive_analysis_engine.py | SentimentAnalyzer.analyze_content | 10 | A (Low) | 286 |
| src/services/ai/query_expansion_engine.py | SynonymExpander.generate_expansions | 10 | A (Low) | 428 |
| src/services/analytics/correlation_engine.py | CorrelationEngine.analyze_correlation | 10 | A (Low) | 123 |
| src/services/analytics/correlation_engine.py | CorrelationEngine.detect_causal_relationships | 10 | A (Low) | 690 |
| src/services/analytics/insight_generation_service.py | InsightGenerationService._detect_cyclical_patterns | 10 | A (Low) | 860 |
| src/services/analytics/insight_generation_service.py | InsightGenerationService._detect_threshold_patterns | 10 | A (Low) | 901 |
| src/services/analytics/intelligence_insight_service.py | IntelligenceInsightService._process_analysis_results | 10 | A (Low) | 1026 |
| src/services/admin/admin_dashboard_service.py | AdminDashboardService.get_system_health | 10 | A (Low) | 377 |
| src/services/monitoring/analytics_platform.py | MetricsCollector.get_metrics | 10 | A (Low) | 273 |
| src/services/monitoring/analytics_platform.py | PerformanceAnalyzer._generate_recommendations | 10 | A (Low) | 711 |
| src/services/messaging/message_bus.py | MessageBus._consumer_loop | 10 | A (Low) | 422 |
| src/services/agents/cognitive_worker.py | CognitiveWorker._assess_content_quality | 10 | A (Low) | 348 |
| src/services/agents/arxiv_worker.py | ArXivWorker.process_task | 10 | A (Low) | 114 |
| src/services/agents/supervisor_agent.py | SupervisorAgent.execute_ingestion_plan | 10 | A (Low) | 205 |
| src/services/agents/supervisor_agent.py | SupervisorAgent._task_timeout_monitor | 10 | A (Low) | 742 |
| src/services/testing/migration_validator.py | main | 10 | A (Low) | 704 |
| src/services/ingestion/arxiv_enhanced_service.py | ArxivEnhancedService.parse_arxiv_response | 10 | A (Low) | 354 |
| src/services/ingestion/email_service.py | EmailIngestionService._apply_intelligent_filters | 10 | A (Low) | 445 |
| src/services/logging/logging_config_service.py | LoggingConfigService._load_from_file | 10 | A (Low) | 320 |
| src/services/security/enterprise_security_hardening.py | ThreatDetectionEngine.analyze_request | 10 | A (Low) | 324 |
| src/services/security/dast_integration.py | PAKEDASTRunner.run_scan | 10 | A (Low) | 414 |
| src/services/wealth/automated_signal_generator.py | NotificationSystem.send_alert | 10 | A (Low) | 1176 |
| src/services/wealth/data_ingestion_pipeline.py | DataIngestionPipeline._initialize_data_streams | 10 | A (Low) | 156 |
| src/services/wealth/google_trends_analyzer.py | GoogleTrendsAnalyzer._assess_risk_level | 10 | A (Low) | 925 |
| src/services/nlp/intelligence_nlp_service.py | IntelligenceNLPService.extract_key_phrases | 10 | A (Low) | 801 |
| src/services/api/production_api_gateway.py | ProductionAPIGateway.handle_request | 10 | A (Low) | 728 |
| src/services/secrets/vault_auth_manager.py | VaultAuthManager.authenticate | 10 | A (Low) | 145 |
| src/services/graph/knowledge_graph_service.py | KnowledgeGraphService._extract_entities_from_text | 10 | A (Low) | 106 |
| src/services/curation/integration/curation_orchestrator.py | CurationOrchestrator._generate_recommendations | 10 | A (Low) | 396 |
| src/services/curation/services/content_analysis_service.py | ContentAnalysisService._extract_topics | 10 | A (Low) | 548 |
| src/services/curation/services/content_analysis_service.py | ContentAnalysisService.extract_topics_sync | 10 | A (Low) | 551 |
| src/services/curation/services/recommendation_service.py | RecommendationService._collaborative_recommendations | 10 | A (Low) | 336 |
| src/services/curation/services/recommendation_service.py | RecommendationService._hybrid_recommendations | 10 | A (Low) | 556 |
| src/services/curation/services/recommendation_service.py | RecommendationService._build_user_preference_vector | 10 | A (Low) | 755 |
| src/services/curation/ml/model_trainer.py | ModelTrainer.train_user_preference_model | 10 | A (Low) | 260 |
| src/services/curation/ml/model_trainer.py | ModelTrainer.train_recommendation_model | 10 | A (Low) | 377 |
| src/services/curation/ml/feature_extractor.py | FeatureExtractor._extract_semantic_features | 10 | A (Low) | 313 |
| src/domain/models/tenant.py | TenantUpdate.apply_to | 10 | A (Low) | 183 |
| src/api/graphql/resolvers.py | Query.comprehensive_search | 10 | A (Low) | 208 |
| src/api/enterprise/search_endpoints.py | get_search_history | 10 | A (Low) | 171 |
| src/api/enterprise/search_endpoints.py | get_saved_searches | 10 | A (Low) | 352 |

## Complexity Distribution

- A (Low): 56 functions
- B (Moderate): 125 functions
- C (High): 7 functions

## Recommendations

1. **Priority 1 (C/D Rating)**: Refactor immediately - these functions are difficult to test and maintain
2. **Priority 2 (B Rating)**: Consider refactoring - monitor for future complexity growth
3. **Priority 3 (A Rating)**: Maintain current structure - good complexity levels

### Refactoring Strategies:
- Extract Method: Break down large functions into smaller, single-purpose functions
- Introduce Guard Clauses: Handle edge cases early and return
- Replace Conditional with Polymorphism: Use OOP patterns for complex conditionals
- Strategy Pattern: Encapsulate algorithms in separate classes