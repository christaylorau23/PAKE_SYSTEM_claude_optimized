# Intelligent Content Curation System

## Overview

The Intelligent Content Curation System is a comprehensive ML-powered platform that automatically discovers, analyzes, and recommends relevant content to users based on their interests, behavior patterns, and preferences. Built as an extension to the PAKE System, it provides enterprise-grade content curation capabilities with sub-second response times.

## Architecture

### Core Components

```
src/services/curation/
├── models/                    # Data models and schemas
│   ├── content_item.py        # Content representation
│   ├── user_profile.py        # User preferences and behavior
│   ├── user_interaction.py    # User engagement tracking
│   ├── recommendation.py      # Recommendation results
│   ├── content_source.py      # Content source management
│   └── topic_category.py      # Topic classification
├── services/                  # Core business logic
│   ├── content_analysis_service.py      # Content quality analysis
│   ├── recommendation_service.py        # Recommendation generation
│   ├── user_preference_service.py      # User preference learning
│   └── feedback_processing_service.py  # Feedback processing
├── ml/                        # Machine learning pipeline
│   ├── feature_extractor.py   # Feature extraction
│   ├── model_trainer.py       # Model training
│   └── prediction_engine.py   # Real-time predictions
├── integration/               # System integration
│   └── curation_orchestrator.py # Main orchestrator
└── api/                       # REST API
    └── curation_api.py        # HTTP endpoints
```

## Features

### 🧠 Intelligent Content Analysis

- **Quality Assessment**: ML-powered content quality scoring
- **Credibility Analysis**: Source authority and reliability evaluation
- **Sentiment Analysis**: Content sentiment and tone detection
- **Readability Scoring**: Content accessibility and complexity analysis
- **Topic Classification**: Automatic content categorization

### 🎯 Personalized Recommendations

- **User Preference Learning**: Adaptive preference modeling
- **Behavioral Analysis**: Interaction pattern recognition
- **Collaborative Filtering**: User similarity-based recommendations
- **Content-Based Filtering**: Feature-based content matching
- **Hybrid Approaches**: Combined recommendation strategies

### 📊 Advanced ML Pipeline

- **Feature Engineering**: Comprehensive feature extraction
- **Model Training**: Multiple algorithm support (Random Forest, Gradient Boosting, Neural Networks)
- **Ensemble Methods**: Model combination for improved accuracy
- **Real-time Prediction**: Cached predictions with fallback strategies
- **Continuous Learning**: Model retraining and adaptation

### 🚀 Performance & Scalability

- **Sub-second Response**: Optimized for real-time recommendations
- **Intelligent Caching**: Multi-level caching with TTL management
- **Batch Processing**: Efficient bulk operations
- **Async Operations**: Non-blocking I/O throughout
- **Resource Management**: Memory and CPU optimization

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install ML dependencies
pip install scikit-learn numpy pandas nltk

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 2. Basic Usage

```python
from src.services.curation.integration.curation_orchestrator import CurationOrchestrator, CurationRequest

# Initialize the system
orchestrator = CurationOrchestrator()
await orchestrator.initialize()

# Create a curation request
request = CurationRequest(
    user_id="user123",
    query="machine learning",
    interests=["AI", "ML", "Data Science"],
    max_results=10,
    include_explanations=True
)

# Get personalized recommendations
response = await orchestrator.curate_content(request)

# Process results
for recommendation in response.recommendations:
    print(f"Content: {recommendation.content_id}")
    print(f"Relevance: {recommendation.relevance_score:.3f}")
    print(f"Reasoning: {recommendation.reasoning}")
    print("---")
```

### 3. API Usage

```bash
# Start the API server
python src/services/curation/api/curation_api.py

# Get recommendations via API
curl -X POST "http://localhost:8001/curate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "query": "machine learning",
    "interests": ["AI", "ML"],
    "max_results": 10
  }'

# Submit user feedback
curl -X POST "http://localhost:8001/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "content_id": "content456",
    "feedback_type": "like",
    "feedback_data": {"session_duration": 120}
  }'
```

## API Reference

### Endpoints

#### `POST /curate`

Get personalized content recommendations.

**Request Body:**

```json
{
  "user_id": "string",
  "query": "string (optional)",
  "interests": ["string"],
  "content_types": ["string"],
  "max_results": 20,
  "include_explanations": true,
  "freshness_days": 30,
  "min_quality_score": 0.3
}
```

**Response:**

```json
{
  "request_id": "uuid",
  "user_id": "string",
  "recommendations": [
    {
      "id": "uuid",
      "content_id": "string",
      "user_id": "string",
      "relevance_score": 0.85,
      "confidence_score": 0.92,
      "reasoning": "Matches your interests in AI and ML",
      "created_at": "2025-01-23T10:30:00Z"
    }
  ],
  "total_content_analyzed": 150,
  "processing_time_ms": 245.5,
  "cache_hit_rate": 0.75,
  "model_confidence": 0.88,
  "created_at": "2025-01-23T10:30:00Z"
}
```

#### `POST /feedback`

Submit user feedback for learning.

**Request Body:**

```json
{
  "user_id": "string",
  "content_id": "string",
  "feedback_type": "like|dislike|share|save|view|click|dismiss",
  "feedback_data": {
    "session_duration": 120,
    "context": {}
  }
}
```

#### `GET /recommendations/{user_id}`

Get recommendations for a specific user.

#### `GET /health`

Get system health status.

#### `POST /retrain`

Retrain ML models with latest data.

## Configuration

### Environment Variables

```bash
# Model configuration
CURATION_MODEL_DIR=models/
CURATION_CACHE_SIZE=10000
CURATION_CACHE_TTL_HOURS=1

# API configuration
CURATION_API_HOST=0.0.0.0
CURATION_API_PORT=8001

# Database configuration (if using external DB)
CURATION_DB_URL=postgresql://user:pass@localhost/curation
CURATION_REDIS_URL=redis://localhost:6379/1

# Performance tuning
CURATION_MAX_BATCH_SIZE=100
CURATION_PREDICTION_TIMEOUT=5.0
CURATION_FEATURE_CACHE_SIZE=5000
```

### Model Configuration

```python
# Customize model parameters
model_configs = {
    'content_quality': ModelConfig(
        model_type='regression',
        hyperparameters={
            'RandomForest': {'n_estimators': 200, 'max_depth': 15},
            'GradientBoosting': {'n_estimators': 200, 'learning_rate': 0.05}
        },
        cross_validation_folds=5
    )
}
```

## Testing

### Run Tests

```bash
# Run all tests
python -m pytest tests/test_curation_system.py -v

# Run specific test categories
python -m pytest tests/test_curation_system.py::TestContentAnalysisService -v
python -m pytest tests/test_curation_system.py::TestMLPipeline -v
python -m pytest tests/test_curation_system.py::TestCurationOrchestrator -v

# Run with coverage
python -m pytest tests/test_curation_system.py --cov=src/services/curation --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component testing
- **Performance Tests**: Response time validation
- **ML Tests**: Model accuracy and prediction testing
- **API Tests**: HTTP endpoint testing

## Performance Optimization

### Caching Strategy

```python
# Multi-level caching
L1_CACHE = "in-memory"  # Fastest access
L2_CACHE = "Redis"      # Distributed caching
L3_CACHE = "Database"   # Persistent storage

# Cache invalidation
- Content features: 24 hours TTL
- User preferences: 1 hour TTL
- Recommendations: 30 minutes TTL
- Model predictions: 1 hour TTL
```

### Batch Processing

```python
# Efficient batch operations
await feature_extractor.batch_extract_features(contents, users, interactions)
await prediction_engine.predict_batch_recommendations(contents, user_profile, interactions)
await analysis_service.analyze_content_batch(contents)
```

### Performance Monitoring

```python
# Get performance statistics
stats = prediction_engine.get_performance_stats()
print(f"Average prediction time: {stats['avg_prediction_time_ms']:.2f}ms")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
print(f"Total predictions: {stats['total_predictions']}")
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/

EXPOSE 8001
CMD ["python", "src/services/curation/api/curation_api.py"]
```

### Production Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  curation-api:
    build: .
    ports:
      - '8001:8001'
    environment:
      - CURATION_CACHE_SIZE=50000
      - CURATION_CACHE_TTL_HOURS=2
      - CURATION_MAX_BATCH_SIZE=200
    volumes:
      - ./models:/app/models
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    ports:
      - '6379:6379'

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=curation
      - POSTGRES_USER=curation
      - POSTGRES_PASSWORD=curation_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Health Monitoring

```bash
# Health check endpoint
curl http://localhost:8001/health

# Performance metrics
curl http://localhost:8001/stats

# Model status
curl http://localhost:8001/models/status
```

## Integration with PAKE System

### Existing System Integration

```python
# Integrate with existing PAKE services
from src.services.ingestion.orchestrator import Orchestrator

class CurationOrchestrator:
    def __init__(self):
        self.pake_orchestrator = Orchestrator()

    async def _search_content(self, query: str):
        # Use existing PAKE search capabilities
        results = await self.pake_orchestrator.research_topic(query)
        return self._convert_to_content_items(results)
```

### Database Integration

```python
# Use existing PAKE database
from src.services.database.database_service import DatabaseService

class CurationOrchestrator:
    def __init__(self):
        self.db_service = DatabaseService()

    async def _get_training_data(self):
        # Query existing PAKE database
        contents = await self.db_service.get_content_with_interactions()
        users = await self.db_service.get_users_with_profiles()
        interactions = await self.db_service.get_user_interactions()
        return contents, users, interactions
```

## Troubleshooting

### Common Issues

#### 1. Model Loading Errors

```bash
# Check model files exist
ls -la models/
# Expected: content_quality_model.pkl, user_preference_model.pkl, recommendation_model.pkl

# Retrain models if missing
curl -X POST http://localhost:8001/retrain
```

#### 2. Performance Issues

```python
# Check cache performance
stats = prediction_engine.get_performance_stats()
if stats['cache_hit_rate'] < 0.5:
    # Increase cache size or TTL
    prediction_engine.cache_size = 20000
    prediction_engine.cache_ttl_hours = 2
```

#### 3. Memory Issues

```python
# Reduce batch sizes
CURATION_MAX_BATCH_SIZE = 50
CURATION_FEATURE_CACHE_SIZE = 2000
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Debug specific components
feature_extractor.debug_mode = True
prediction_engine.debug_mode = True
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd PAKE_SYSTEM_claude_optimized

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v
```

### Code Standards

- **Type Hints**: All functions must have type annotations
- **Async/Await**: Use async patterns for I/O operations
- **Error Handling**: Comprehensive exception handling
- **Testing**: 100% test coverage requirement
- **Documentation**: Docstrings for all public methods

### Pull Request Process

1. Create feature branch
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit pull request

## License

This project is part of the PAKE System and follows the same licensing terms.

## Support

For issues and questions:

- Create GitHub issues for bugs
- Use discussions for feature requests
- Check documentation for common questions
- Review test cases for usage examples
