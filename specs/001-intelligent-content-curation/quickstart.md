# Quickstart Guide: Intelligent Content Curation

**Feature**: 001-intelligent-content-curation  
**Date**: 2025-01-23  
**Status**: Complete

## Overview

This quickstart guide provides step-by-step instructions for testing and validating the Intelligent Content Curation system. It covers user scenarios, integration tests, and performance validation.

## Prerequisites

### System Requirements
- Python 3.12+
- Redis server running on localhost:6379
- PostgreSQL database (optional for full testing)
- 4GB+ RAM available
- Docker (for containerized testing)

### Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install ML dependencies
pip install scikit-learn numpy pandas nltk

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

## Quick Start (5 minutes)

### 1. Start the System
```bash
# Start the curation API server
python src/services/curation/api/curation_api.py

# In another terminal, start Redis (if not running)
redis-server
```

### 2. Health Check
```bash
# Verify system is running
curl http://localhost:8001/health

# Expected response:
{
  "services_healthy": {
    "content_analysis": true,
    "recommendation": true,
    "user_preference": true,
    "feedback_processing": true
  },
  "models_loaded": {
    "content_quality": true,
    "user_preference": true,
    "recommendation": true
  },
  "cache_status": {
    "total_predictions": 0,
    "cached_predictions": 0,
    "cache_hit_rate": 0.0,
    "cache_size": 0
  },
  "performance_metrics": {
    "avg_prediction_time_ms": 0.0,
    "avg_response_time_ms": 0.0,
    "requests_per_second": 0.0
  },
  "last_updated": "2025-01-23T10:30:00Z"
}
```

### 3. Get Your First Recommendations
```bash
# Request personalized recommendations
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-001",
    "query": "machine learning",
    "interests": ["AI", "ML", "Data Science"],
    "max_results": 5,
    "include_explanations": true
  }'

# Expected response:
{
  "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
  "user_id": "test-user-001",
  "recommendations": [
    {
      "id": "rec-123e4567-e89b-12d3-a456-426614174001",
      "content_id": "content-789",
      "user_id": "test-user-001",
      "relevance_score": 0.92,
      "confidence_score": 0.88,
      "reasoning": "Matches your interests in AI and ML, high-quality content from authoritative source",
      "created_at": "2025-01-23T10:30:00Z"
    }
  ],
  "total_content_analyzed": 150,
  "processing_time_ms": 245.5,
  "cache_hit_rate": 0.0,
  "model_confidence": 0.88,
  "created_at": "2025-01-23T10:30:00Z"
}
```

## User Scenarios Testing

### Scenario 1: New User Onboarding
**Objective**: Test system behavior with a completely new user

**Steps**:
1. **Create new user profile**:
```bash
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "new-user-001",
    "interests": ["AI", "Machine Learning"],
    "max_results": 10
  }'
```

2. **Verify cold-start handling**:
   - System should provide recommendations based on interests
   - Recommendations should include explanations
   - Response time should be <1000ms

3. **Expected behavior**:
   - Recommendations generated successfully
   - Explanations provided for recommendations
   - System creates user profile automatically

### Scenario 2: Content Discovery and Recommendation
**Objective**: Test content discovery and personalized recommendation generation

**Steps**:
1. **Request recommendations with specific query**:
```bash
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-002",
    "query": "deep learning healthcare",
    "interests": ["AI", "Healthcare", "ML"],
    "content_types": ["article", "paper"],
    "max_results": 15,
    "freshness_days": 30,
    "min_quality_score": 0.7
  }'
```

2. **Verify recommendation quality**:
   - All recommendations should have relevance_score > 0.5
   - All recommendations should have confidence_score > 0.3
   - Recommendations should match specified content types
   - Content should be within freshness_days limit

3. **Expected behavior**:
   - High-quality recommendations generated
   - Filtering by content type and freshness works
   - Quality score filtering applied correctly

### Scenario 3: User Feedback Processing
**Objective**: Test user feedback collection and learning

**Steps**:
1. **Submit positive feedback**:
```bash
curl -X POST "http://localhost:8001/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-002",
    "content_id": "content-789",
    "feedback_type": "like",
    "feedback_data": {
      "session_duration": 180,
      "explicit_rating": 5,
      "feedback_text": "Excellent article, very informative"
    }
  }'
```

2. **Submit negative feedback**:
```bash
curl -X POST "http://localhost:8001/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-002",
    "content_id": "content-790",
    "feedback_type": "dislike",
    "feedback_data": {
      "session_duration": 30,
      "explicit_rating": 2,
      "feedback_text": "Not relevant to my interests"
    }
  }'
```

3. **Verify feedback processing**:
   - Both feedback submissions should return success
   - System should process feedback for learning
   - User preferences should be updated

4. **Expected behavior**:
   - Feedback processed successfully
   - User profile updated with new preferences
   - Future recommendations influenced by feedback

### Scenario 4: User Preference Learning
**Objective**: Test adaptive preference learning over time

**Steps**:
1. **Get initial recommendations**:
```bash
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "learning-user-001",
    "interests": ["Technology"],
    "max_results": 10
  }'
```

2. **Submit multiple feedback interactions**:
```bash
# Like AI-related content
curl -X POST "http://localhost:8001/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "learning-user-001",
    "content_id": "ai-content-001",
    "feedback_type": "like",
    "feedback_data": {"session_duration": 300}
  }'

# Share ML-related content
curl -X POST "http://localhost:8001/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "learning-user-001",
    "content_id": "ml-content-001",
    "feedback_type": "share",
    "feedback_data": {"session_duration": 240}
  }'
```

3. **Get updated recommendations**:
```bash
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "learning-user-001",
    "max_results": 10
  }'
```

4. **Verify preference learning**:
   - Recommendations should show preference for AI/ML content
   - User profile should reflect learned preferences
   - Recommendation explanations should mention learned interests

5. **Expected behavior**:
   - System learns user preferences from interactions
   - Future recommendations align with learned preferences
   - User profile updated with new interests

## Integration Tests

### Test 1: API Contract Validation
**Objective**: Validate all API endpoints against OpenAPI specification

**Steps**:
1. **Run contract tests**:
```bash
python -m pytest tests/contract/ -v
```

2. **Verify all endpoints**:
   - POST /curate - Content recommendation
   - POST /feedback - User feedback submission
   - GET /recommendations/{user_id} - User recommendations
   - GET /health - System health check
   - POST /retrain - Model retraining
   - GET /stats - Performance statistics

3. **Expected results**:
   - All contract tests pass
   - API responses match OpenAPI specification
   - Error handling works correctly

### Test 2: End-to-End Workflow
**Objective**: Test complete user journey from onboarding to personalized recommendations

**Steps**:
1. **Run integration tests**:
```bash
python -m pytest tests/integration/ -v
```

2. **Verify complete workflow**:
   - User profile creation
   - Content discovery and analysis
   - Recommendation generation
   - Feedback processing
   - Preference learning
   - Model retraining

3. **Expected results**:
   - Complete workflow executes successfully
   - All components integrate properly
   - Data flows correctly between services

### Test 3: Performance Validation
**Objective**: Validate system meets performance requirements

**Steps**:
1. **Run performance tests**:
```bash
python -m pytest tests/performance/ -v
```

2. **Verify performance metrics**:
   - Response time < 1000ms for recommendations
   - Cache hit rate > 50% after warmup
   - Memory usage < 500MB per service
   - CPU usage < 80% under load

3. **Expected results**:
   - All performance tests pass
   - System meets sub-second response requirements
   - Caching improves performance over time

## Performance Testing

### Load Testing
**Objective**: Test system under realistic load conditions

**Steps**:
1. **Generate load test**:
```bash
# Install locust for load testing
pip install locust

# Run load test
locust -f tests/performance/load_test.py --host=http://localhost:8001
```

2. **Test scenarios**:
   - 100 concurrent users
   - 1000 requests per minute
   - Mixed recommendation and feedback requests

3. **Monitor metrics**:
   - Response time percentiles (p50, p95, p99)
   - Error rate
   - Memory and CPU usage
   - Cache hit rate

4. **Expected results**:
   - p95 response time < 500ms
   - Error rate < 1%
   - System remains stable under load

### Stress Testing
**Objective**: Test system limits and failure modes

**Steps**:
1. **Run stress test**:
```bash
python tests/performance/stress_test.py
```

2. **Test scenarios**:
   - Gradual load increase to 500 concurrent users
   - Memory pressure testing
   - Database connection exhaustion
   - Cache eviction testing

3. **Verify graceful degradation**:
   - System handles overload gracefully
   - Error responses are informative
   - Recovery after load reduction

## Troubleshooting

### Common Issues

#### 1. System Not Starting
**Symptoms**: API server fails to start
**Solutions**:
```bash
# Check Redis connection
redis-cli ping

# Check Python dependencies
pip list | grep -E "(fastapi|scikit-learn|redis)"

# Check port availability
netstat -tulpn | grep 8001
```

#### 2. Slow Recommendations
**Symptoms**: Response times > 1000ms
**Solutions**:
```bash
# Check cache status
curl http://localhost:8001/stats

# Warm up cache
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "warmup", "max_results": 1}'

# Check Redis performance
redis-cli --latency
```

#### 3. Poor Recommendation Quality
**Symptoms**: Low relevance scores or irrelevant content
**Solutions**:
```bash
# Retrain models
curl -X POST "http://localhost:8001/retrain?force=true"

# Check model status
curl http://localhost:8001/health

# Verify user profile
curl http://localhost:8001/user/test-user-001/profile
```

### Debug Mode
**Enable debug logging**:
```bash
# Set environment variable
export CURATION_DEBUG=true

# Restart API server
python src/services/curation/api/curation_api.py
```

## Validation Checklist

### Functional Validation
- [ ] New user onboarding works
- [ ] Content discovery and recommendation generation
- [ ] User feedback processing and learning
- [ ] Preference adaptation over time
- [ ] All API endpoints respond correctly
- [ ] Error handling works properly

### Performance Validation
- [ ] Response times < 1000ms
- [ ] Cache hit rate > 50% after warmup
- [ ] Memory usage < 500MB per service
- [ ] System handles 100+ concurrent users
- [ ] Graceful degradation under load

### Integration Validation
- [ ] All services communicate properly
- [ ] Data flows correctly between components
- [ ] External dependencies (Redis, database) work
- [ ] PAKE system integration functions
- [ ] Health checks report accurate status

### Security Validation
- [ ] Authentication and authorization work
- [ ] Input validation prevents attacks
- [ ] Sensitive data is protected
- [ ] Audit logging captures events
- [ ] Rate limiting prevents abuse

## Next Steps

After completing the quickstart validation:

1. **Production Deployment**: Use Docker containers and Kubernetes
2. **Monitoring Setup**: Configure Prometheus and Grafana
3. **Alerting**: Set up alerts for performance degradation
4. **Scaling**: Configure horizontal scaling based on load
5. **Backup**: Implement data backup and recovery procedures

---

*Quickstart guide completed: 2025-01-23*  
*Ready for production deployment*