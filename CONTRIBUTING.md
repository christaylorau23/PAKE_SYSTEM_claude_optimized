# 🤝 Contributing to PAKE System

We welcome contributions to the PAKE System! This document provides guidelines for contributing to our enterprise AI-powered knowledge management platform.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Standards](#documentation-standards)
- [Submitting Contributions](#submitting-contributions)
- [Release Process](#release-process)

## 🤝 Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@pake-system.com](mailto:conduct@pake-system.com).

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**: Required for backend services
- **Node.js 22.18.0+**: Required for TypeScript bridge
- **Redis 7+**: Required for enterprise caching
- **PostgreSQL 15+**: Required for database operations
- **Docker**: Required for containerized deployment
- **Kubernetes**: Required for production orchestration

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR-USERNAME/pake-system.git
   cd pake-system
   ```

2. **Environment Setup**
   ```bash
   # Python environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-phase7.txt

   # Node.js dependencies
   cd src/bridge
   npm install
   cd ../..

   # Environment configuration
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis

   # Run database migrations
   python scripts/setup_database.py
   ```

4. **Start Development Services**
   ```bash
   # Start backend (Terminal 1)
   python mcp_server_standalone.py

   # Start bridge (Terminal 2)
   cd src/bridge && npm start
   ```

5. **Verify Setup**
   ```bash
   # Run system health check
   python scripts/test_production_pipeline.py

   # Run full test suite
   python -m pytest tests/ -v
   ```

## 🔄 Development Workflow

### Branching Strategy

We use **Git Flow** with the following branch structure:

- `main`: Production-ready releases only
- `develop`: Development integration branch
- `feature/`: New features (`feature/semantic-search-enhancement`)
- `hotfix/`: Production fixes (`hotfix/authentication-bug`)
- `release/`: Release preparation (`release/v10.2.0`)

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write Tests First** (TDD approach)
   ```bash
   # Create test file
   touch tests/test_your_feature.py
   # Write failing tests first
   python -m pytest tests/test_your_feature.py -v
   ```

2. **Implement Feature**
   - Follow existing code patterns
   - Add comprehensive documentation
   - Ensure backward compatibility

3. **Validate Changes**
   ```bash
   # Run all tests
   python -m pytest tests/ -v

   # Check code quality
   python -m black src/ --check
   python -m flake8 src/
   python -m mypy src/

   # Test performance impact
   python scripts/benchmark_performance.py
   ```

### Commit Guidelines

We follow [Conventional Commits](https://conventionalcommits.org/) specification:

```bash
# Feature commits
git commit -m "feat: add semantic search enhancement to search API"

# Bug fixes
git commit -m "fix: resolve authentication token expiration issue"

# Documentation
git commit -m "docs: update API documentation with ML endpoints"

# Performance improvements
git commit -m "perf: optimize database queries in search orchestrator"

# Breaking changes
git commit -m "feat!: redesign search API response format

BREAKING CHANGE: search API now returns enhanced metadata structure"
```

### Commit Types

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without functionality changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, tooling)

## 📝 Coding Standards

### Python Code Standards

#### Code Style
- **Formatter**: Black with 88-character line length
- **Linter**: Flake8 with enterprise configuration
- **Type Checker**: MyPy with strict mode
- **Import Sorting**: isort with black compatibility

```python
# ✅ Good: Type-annotated function with docstring
async def enhance_search_results(
    query: str,
    results: List[Dict[str, Any]],
    enhance_semantic: bool = True
) -> Tuple[List[SearchEnhancement], SearchAnalytics]:
    """Enhance search results with semantic analysis.

    Args:
        query: User search query
        results: Raw search results from sources
        enhance_semantic: Enable semantic enhancement

    Returns:
        Tuple of enhanced results and analytics

    Raises:
        ValueError: If query is empty
        ServiceUnavailableError: If ML services are down
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")

    # Implementation here
    pass
```

#### Data Structures
```python
# ✅ Use dataclasses for immutable data
@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str
    relevance_score: float
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

# ✅ Use enums for constants
class SearchSource(str, Enum):
    WEB = "web"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    GMAIL = "gmail"
```

#### Error Handling
```python
# ✅ Custom exception hierarchy
class PAKEError(Exception):
    """Base exception for PAKE system."""
    pass

class SearchServiceError(PAKEError):
    """Exception for search service issues."""
    pass

class AuthenticationError(PAKEError):
    """Exception for authentication issues."""
    pass

# ✅ Proper exception handling
async def process_search(query: str) -> SearchResult:
    try:
        result = await search_service.search(query)
        return result
    except httpx.TimeoutError as e:
        logger.error(f"Search timeout for query: {query}", exc_info=True)
        raise SearchServiceError(f"Search service timeout: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error in search: {e}", exc_info=True)
        raise SearchServiceError(f"Search failed: {e}") from e
```

### TypeScript Code Standards

#### Code Style
- **Formatter**: Prettier with 2-space indentation
- **Linter**: ESLint with TypeScript and enterprise rules
- **Type Checker**: TypeScript strict mode

```typescript
// ✅ Good: Strict typing with comprehensive interfaces
interface SearchRequest {
  readonly query: string;
  readonly sources: readonly SearchSource[];
  readonly maxResults: number;
  readonly enhanceML?: boolean;
}

interface SearchResponse<T = SearchResult[]> {
  readonly success: boolean;
  readonly data: T | null;
  readonly error: string | null;
  readonly metadata: {
    readonly totalResults: number;
    readonly processingTimeMs: number;
    readonly sourcesUsed: readonly string[];
  };
}

// ✅ Proper error handling with types
const executeSearch = async (request: SearchRequest): Promise<SearchResponse> => {
  try {
    const response = await apiClient.post('/search', request);
    return createSuccessResponse(response.data);
  } catch (error) {
    logger.error('Search API error:', error);
    return createErrorResponse(
      error instanceof Error ? error.message : 'Unknown search error'
    );
  }
};
```

#### React/UI Components
```typescript
// ✅ Functional components with proper typing
interface SearchDashboardProps {
  readonly initialQuery?: string;
  readonly onSearchComplete?: (results: SearchResult[]) => void;
}

export const SearchDashboard: React.FC<SearchDashboardProps> = ({
  initialQuery = '',
  onSearchComplete
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = useCallback(async (searchQuery: string) => {
    setIsLoading(true);
    try {
      const response = await executeSearch({ query: searchQuery, sources: ['web', 'arxiv'], maxResults: 10 });
      if (response.success && response.data) {
        setResults(response.data);
        onSearchComplete?.(response.data);
      }
    } finally {
      setIsLoading(false);
    }
  }, [onSearchComplete]);

  return (
    <div className="search-dashboard">
      {/* Component implementation */}
    </div>
  );
};
```

### Configuration and Environment

#### Environment Variables
```python
# ✅ Proper environment configuration
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    firecrawl_api_key: str = Field(..., env="FIRECRAWL_API_KEY")
    pubmed_email: str = Field(..., env="PUBMED_EMAIL")

    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")

    # Performance Configuration
    cache_ttl_seconds: int = Field(300, env="CACHE_TTL_SECONDS")
    max_concurrent_searches: int = Field(10, env="MAX_CONCURRENT_SEARCHES")

    # Feature Flags
    enable_ml_enhancement: bool = Field(True, env="ENABLE_ML_ENHANCEMENT")
    enable_semantic_search: bool = Field(True, env="ENABLE_SEMANTIC_SEARCH")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── services/           # Service unit tests
│   ├── utils/              # Utility function tests
│   └── models/             # Data model tests
├── integration/            # Integration tests
│   ├── api/                # API endpoint tests
│   ├── database/           # Database integration tests
│   └── external/           # External API integration tests
├── e2e/                    # End-to-end tests
│   ├── workflows/          # Complete workflow tests
│   └── performance/        # Performance and load tests
└── fixtures/               # Test data and fixtures
```

### Test Standards

#### Unit Tests
```python
# ✅ Comprehensive unit test example
import pytest
from unittest.mock import AsyncMock, patch
from src.services.ml.semantic_search_service import SemanticSearchService

class TestSemanticSearchService:
    @pytest.fixture
    def search_service(self):
        return SemanticSearchService()

    @pytest.fixture
    def sample_results(self):
        return [
            {
                "title": "Machine Learning Basics",
                "content": "Introduction to machine learning concepts...",
                "url": "https://example.com/ml-basics",
                "source": "web"
            }
        ]

    @pytest.mark.asyncio
    async def test_enhance_search_results_success(self, search_service, sample_results):
        """Test successful search result enhancement."""
        query = "machine learning"

        enhancements, analytics = await search_service.enhance_search_results(
            query, sample_results
        )

        assert len(enhancements) == 1
        assert enhancements[0].relevance_score > 0
        assert analytics.total_results_processed == 1
        assert analytics.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_enhance_search_results_empty_query(self, search_service):
        """Test enhancement with empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await search_service.enhance_search_results("", [])

    @pytest.mark.asyncio
    @patch('src.services.ml.semantic_search_service.logger')
    async def test_enhance_search_results_handles_errors(self, mock_logger, search_service):
        """Test error handling in search enhancement."""
        # Test error scenarios and logging
        pass
```

#### Integration Tests
```python
# ✅ API integration test example
import pytest
import httpx
from fastapi.testclient import TestClient
from src.main import app

class TestSearchAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_search_endpoint_success(self, client):
        """Test successful search API call."""
        response = client.post("/search", json={
            "query": "artificial intelligence",
            "sources": ["web", "arxiv"],
            "max_results": 5,
            "enhance_ml": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) <= 5
        assert "ml_enhancements" in data

    def test_search_endpoint_validation(self, client):
        """Test API validation."""
        response = client.post("/search", json={
            "query": "",  # Invalid empty query
            "sources": ["invalid_source"],  # Invalid source
        })

        assert response.status_code == 422
```

### Performance Testing

```python
# ✅ Performance test example
import pytest
import time
from src.scripts.benchmark_performance import benchmark_search_pipeline

class TestPerformance:
    @pytest.mark.performance
    async def test_search_performance_under_load(self):
        """Test search performance under concurrent load."""
        concurrent_requests = 10
        max_acceptable_time = 2.0  # seconds

        start_time = time.time()
        results = await benchmark_search_pipeline(
            query="test query",
            concurrent_requests=concurrent_requests
        )
        execution_time = time.time() - start_time

        assert execution_time < max_acceptable_time
        assert len(results) == concurrent_requests
        assert all(r.success for r in results)
```

### Test Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Services**: 95% coverage required
- **New Features**: 100% coverage required
- **Integration Tests**: All API endpoints must have tests
- **Performance Tests**: All critical paths must have performance tests

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/unit/ -v                 # Unit tests only
python -m pytest tests/integration/ -v          # Integration tests only
python -m pytest -m performance                 # Performance tests only

# Coverage reporting
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Parallel test execution
python -m pytest tests/ -n auto

# Test specific functionality
python -m pytest tests/test_semantic_search.py -v -k "test_enhance_search"
```

## 📚 Documentation Standards

### Code Documentation

#### Python Docstrings
```python
def calculate_relevance_score(
    query: str,
    content: str,
    algorithm: str = "tfidf"
) -> float:
    """Calculate relevance score between query and content.

    Uses TF-IDF or other algorithms to determine how relevant
    the content is to the user's search query.

    Args:
        query: User search query string
        content: Content text to score against query
        algorithm: Scoring algorithm ("tfidf", "cosine", "jaccard")

    Returns:
        Relevance score between 0.0 and 1.0, where 1.0 is perfect match

    Raises:
        ValueError: If algorithm is not supported
        RuntimeError: If scoring calculation fails

    Example:
        >>> score = calculate_relevance_score("machine learning", "ML tutorial")
        >>> assert 0.0 <= score <= 1.0

    Note:
        TF-IDF algorithm is recommended for general text scoring.
        Cosine similarity works better for longer documents.
    """
```

#### TypeScript Documentation
```typescript
/**
 * Enhanced search client for PAKE system API integration.
 *
 * Provides type-safe methods for executing searches across multiple sources
 * with ML enhancement capabilities and comprehensive error handling.
 *
 * @example
 * ```typescript
 * const client = new SearchClient('http://localhost:8000');
 * const results = await client.search({
 *   query: 'artificial intelligence',
 *   sources: ['web', 'arxiv'],
 *   enhanceML: true
 * });
 * ```
 */
export class SearchClient {
  /**
   * Execute multi-source search with optional ML enhancement.
   *
   * @param request - Search parameters and configuration
   * @returns Promise resolving to search results with metadata
   * @throws SearchClientError when API request fails
   * @throws ValidationError when request parameters are invalid
   */
  public async search(request: SearchRequest): Promise<SearchResponse> {
    // Implementation
  }
}
```

### API Documentation

All API endpoints must be documented using OpenAPI/Swagger specification:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class SearchRequest(BaseModel):
    """Search request model with validation."""
    query: str = Field(..., description="Search query string", min_length=1)
    sources: List[SearchSource] = Field(
        default=["web"],
        description="List of search sources to query"
    )
    max_results: int = Field(
        default=10,
        description="Maximum results per source",
        ge=1,
        le=100
    )

@app.post("/search",
         response_model=SearchResponse,
         summary="Multi-source search with ML enhancement",
         description="Execute search across multiple sources with optional ML enhancement")
async def search_endpoint(request: SearchRequest):
    """
    Execute multi-source search with AI enhancement.

    This endpoint orchestrates searches across web, academic, and biomedical sources
    with optional semantic enhancement and content summarization.

    - **query**: Search terms (required, non-empty string)
    - **sources**: Array of source types ("web", "arxiv", "pubmed")
    - **max_results**: Results per source (1-100, default: 10)
    - **enhance_ml**: Enable AI enhancement (default: true)

    Returns comprehensive search results with relevance scoring and analytics.
    """
```

### README Guidelines

Each service directory should have a README.md with:

1. **Purpose and Scope**: What the service does
2. **Installation**: How to set up and configure
3. **Usage Examples**: Code examples and API usage
4. **Configuration**: Environment variables and settings
5. **API Reference**: Endpoint documentation
6. **Performance**: Benchmarks and optimization notes
7. **Troubleshooting**: Common issues and solutions

## 🚀 Submitting Contributions

### Pull Request Process

1. **Pre-submission Checklist**
   ```bash
   # Ensure all tests pass
   python -m pytest tests/ -v

   # Check code quality
   python -m black src/ --check
   python -m flake8 src/
   python -m mypy src/

   # Update documentation
   # - Add docstrings to new functions
   # - Update README if needed
   # - Add changelog entry

   # Performance validation
   python scripts/benchmark_performance.py
   ```

2. **Create Pull Request**
   - Use descriptive title following conventional commits
   - Fill out the PR template completely
   - Link related issues using "Fixes #123"
   - Add appropriate labels (feature, bugfix, documentation)

3. **Pull Request Template**
   ```markdown
   ## Description
   Brief description of changes and motivation.

   ## Type of Change
   - [ ] Bug fix (non-breaking change that fixes an issue)
   - [ ] New feature (non-breaking change that adds functionality)
   - [ ] Breaking change (fix or feature that causes existing functionality to change)
   - [ ] Documentation update
   - [ ] Performance improvement
   - [ ] Refactoring (no functional changes)

   ## Testing
   - [ ] Unit tests added/updated
   - [ ] Integration tests added/updated
   - [ ] Performance tests added/updated (if applicable)
   - [ ] Manual testing completed

   ## Documentation
   - [ ] Code comments added/updated
   - [ ] API documentation updated
   - [ ] README updated (if needed)
   - [ ] CHANGELOG entry added

   ## Performance Impact
   - [ ] No performance impact
   - [ ] Performance improved
   - [ ] Performance regression (explain below)

   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Self-review completed
   - [ ] Tests pass locally
   - [ ] No new linting errors
   - [ ] Breaking changes documented
   ```

### Review Process

1. **Automated Checks**
   - CI/CD pipeline runs all tests
   - Code quality checks (linting, formatting)
   - Security vulnerability scanning
   - Performance regression testing

2. **Human Review**
   - Code review by at least 2 maintainers
   - Architecture review for significant changes
   - Security review for authentication/data handling
   - Performance review for critical paths

3. **Approval Requirements**
   - All automated checks pass
   - 2 approving reviews from maintainers
   - No unresolved conversations
   - Up-to-date with target branch

## 🔄 Release Process

### Version Management

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (X.Y.0): New features (backward compatible)
- **PATCH** (X.Y.Z): Bug fixes (backward compatible)

### Release Workflow

1. **Release Planning**
   ```bash
   # Create release branch
   git checkout develop
   git pull origin develop
   git checkout -b release/v10.2.0
   ```

2. **Release Preparation**
   - Update version numbers
   - Update CHANGELOG.md
   - Run full test suite
   - Update documentation
   - Performance validation

3. **Release Finalization**
   ```bash
   # Merge to main
   git checkout main
   git merge release/v10.2.0
   git tag v10.2.0
   git push origin main --tags

   # Back-merge to develop
   git checkout develop
   git merge main
   git push origin develop
   ```

4. **Post-Release**
   - Deploy to production
   - Monitor system health
   - Update deployment documentation
   - Announce release

## 🎯 Areas for Contribution

### High Priority

- **Performance Optimization**: Database queries, caching strategies
- **ML Enhancement**: Semantic search improvements, better summarization
- **Enterprise Features**: SSO integration, multi-tenancy support
- **Mobile Support**: React Native or PWA development

### Medium Priority

- **Extended Integrations**: Social media APIs, news sources
- **Advanced Analytics**: Business intelligence, trend analysis
- **Developer Tools**: CLI tools, IDE extensions
- **Internationalization**: Multi-language support

### Documentation

- **User Guides**: Step-by-step tutorials
- **API Examples**: Real-world usage patterns
- **Deployment Guides**: Cloud platform specifics
- **Troubleshooting**: Common issues and solutions

## 🆘 Getting Help

### Communication Channels

- **GitHub Discussions**: General questions and feature requests
- **GitHub Issues**: Bug reports and specific problems
- **Developer Email**: dev@pake-system.com
- **Documentation**: [docs/](docs/) directory

### Before Asking for Help

1. Check existing documentation
2. Search GitHub issues
3. Review troubleshooting guides
4. Try the development setup steps

### What to Include in Questions

- **Environment**: OS, Python version, Node.js version
- **Error Messages**: Full stack traces
- **Steps to Reproduce**: Minimal example
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens

---

## 🏆 Recognition

Contributors are recognized in:

- **CONTRIBUTORS.md**: All contributors listed
- **GitHub Releases**: Major contributors highlighted
- **Documentation**: Significant contributions credited
- **Annual Report**: Top contributors featured

---

Thank you for contributing to PAKE System! 🎉

Your contributions help make AI-powered knowledge management accessible and powerful for researchers worldwide.

---

<div align="center">

**Questions?** 🤔 **[Open a Discussion](https://github.com/your-org/pake-system/discussions)** | **[Report a Bug](https://github.com/your-org/pake-system/issues)** | **[Request a Feature](https://github.com/your-org/pake-system/issues)**

</div>