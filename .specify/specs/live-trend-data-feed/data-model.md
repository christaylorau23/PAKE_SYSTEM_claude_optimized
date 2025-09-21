# Data Model: Live Trend Data Feed

## Core Entity Definitions

### TrendSignal
**Purpose**: Unified representation of trend data from any platform
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `platform`: Source platform (google_trends, youtube, twitter, tiktok)
- `keyword`: Trend topic or search term
- `timestamp`: When trend data was captured
- `region`: Geographic region (US, GB, Global, etc.)
- `interest_score`: Normalized trend strength (0.0 to 1.0)
- `engagement_metrics`: Platform-specific engagement data
- `metadata`: Additional platform-specific information

**Relationships**:
- One TrendSignal belongs to one Platform
- Multiple TrendSignals can form one TrendCorrelation
- TrendSignal can generate multiple InvestmentOpportunities

**Validation Rules**:
- `interest_score` must be between 0.0 and 1.0
- `timestamp` must not be in the future
- `platform` must be from predefined enum
- `region` must be valid ISO country code or "Global"

### TrendCorrelation
**Purpose**: Cross-platform trend relationships with confidence scoring
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `trend_signals`: List of related TrendSignal IDs
- `correlation_strength`: How strongly trends correlate (0.0 to 1.0)
- `confidence_score`: Statistical confidence in correlation (0.0 to 1.0)
- `time_window`: Time period for correlation analysis
- `geographic_overlap`: Regions where trends overlap
- `momentum_score`: Rate of trend growth (-1.0 to 1.0)

**Relationships**:
- TrendCorrelation aggregates multiple TrendSignals
- One TrendCorrelation can generate multiple InvestmentOpportunities
- TrendCorrelations can form hierarchical relationships

**State Transitions**:
- ANALYZING → CORRELATED → VALIDATED → INVESTMENT_MAPPED

### InvestmentOpportunity
**Purpose**: Investment vehicles mapped from trend intelligence
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `trend_correlation_id`: Source correlation analysis
- `symbol`: Investment symbol (stock ticker, crypto symbol, etc.)
- `asset_class`: Investment type (stock, etf, crypto, commodity)
- `relevance_score`: How relevant to trend (0.0 to 1.0)
- `risk_assessment`: Risk level (low, medium, high)
- `timing_signal`: Investment timing recommendation
- `confidence_interval`: Statistical confidence bounds
- `market_sector`: Industry or market segment

**Relationships**:
- InvestmentOpportunity derived from TrendCorrelation
- Multiple opportunities can target same asset from different trends
- Historical performance tracking for validation

**Validation Rules**:
- `relevance_score` must be above 0.3 threshold
- `symbol` must be valid market identifier
- `timing_signal` must include entry and exit recommendations

### TrendStream
**Purpose**: Real-time data pipeline management and monitoring
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `platform`: Data source platform
- `status`: Stream health status (active, degraded, failed)
- `last_update`: Timestamp of most recent data
- `throughput_rate`: Messages processed per second
- `error_count`: Number of recent errors
- `rate_limit_status`: Current API rate limit status

**Relationships**:
- TrendStream produces TrendSignals
- Multiple streams can be aggregated for correlation
- Stream health affects correlation confidence

**State Transitions**:
- INITIALIZING → ACTIVE → DEGRADED → FAILED → RECOVERING

### GeographicTrendData
**Purpose**: Regional trend analysis and market penetration tracking
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `trend_signal_id`: Associated trend signal
- `country_code`: ISO country code
- `region_type`: Geographic granularity (country, state, city)
- `adoption_rate`: Trend adoption percentage in region
- `penetration_velocity`: Rate of regional spread
- `demographic_profile`: Age/gender distribution data
- `market_readiness_score`: Investment opportunity readiness (0.0 to 1.0)

**Relationships**:
- GeographicTrendData extends TrendSignal with location context
- Multiple geographic data points create regional patterns
- Geographic analysis influences InvestmentOpportunity timing

### APIRateLimitTracker
**Purpose**: External API usage monitoring and optimization
**Key Attributes**:
- `id`: Unique identifier (UUID)
- `api_platform`: External API being tracked
- `current_usage`: Current period API usage count
- `usage_limit`: Maximum allowed API calls per period
- `reset_time`: When usage counter resets
- `cost_per_request`: API call cost for optimization
- `priority_queue`: Request prioritization logic

**Relationships**:
- APIRateLimitTracker manages TrendStream data collection
- Rate limiting affects TrendSignal collection frequency
- Cost optimization influences correlation analysis depth

**State Transitions**:
- NORMAL → WARNING → THROTTLED → BLOCKED → RESET

## Data Flow Architecture

### Stream Processing Flow
```
External APIs → APIRateLimitTracker → TrendStream → TrendSignal → TrendCorrelation → InvestmentOpportunity
```

### Geographic Analysis Flow
```
TrendSignal → GeographicTrendData → Regional Correlation → Market Penetration Analysis
```

### Investment Intelligence Flow
```
TrendCorrelation + GeographicTrendData → InvestmentOpportunity → Portfolio Recommendations
```

## Data Validation Framework

### Input Validation
- All timestamps validated against reasonable bounds
- Geographic codes validated against ISO standards
- Scores and metrics validated against defined ranges
- Platform identifiers validated against supported platforms

### Business Logic Validation
- Correlation calculations validated for statistical significance
- Investment opportunities validated for market availability
- Geographic data validated for regional consistency
- Rate limiting validated for cost optimization

### Data Quality Assurance
- Duplicate detection across platforms and time periods
- Anomaly detection for unusual trend patterns
- Confidence scoring for data reliability assessment
- Historical validation against known trend outcomes

This data model provides the foundation for reliable, scalable trend intelligence with comprehensive validation and relationship management across multiple external data sources.