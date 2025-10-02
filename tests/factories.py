"""
Test Data Factories using factory_boy

Provides factories for generating realistic test data for all domain models.
Follows the Factory pattern to create complex object graphs with minimal boilerplate.

Usage:
    user = UserFactory()
    user = UserFactory(username="specific_user")
    users = UserFactory.create_batch(5)
"""

from datetime import UTC

import factory
from factory import Faker, LazyAttribute, Sequence

# ============================================================================
# Authentication Factories
# ============================================================================


class UserFactory(factory.Factory):
    """Factory for creating User instances"""

    class Meta:
        model = dict  # Using dict since User is a Pydantic model

    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = Faker("name")
    disabled = False


class UserInDBFactory(factory.Factory):
    """Factory for creating UserInDB instances with hashed passwords"""

    class Meta:
        model = dict

    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    full_name = Faker("name")
    disabled = False
    # Default bcrypt hash for "password123"
    hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


class AdminUserFactory(UserInDBFactory):
    """Factory for creating admin users"""

    username = Sequence(lambda n: f"admin{n}")
    role = "admin"
    disabled = False


class DisabledUserFactory(UserInDBFactory):
    """Factory for creating disabled users"""

    disabled = True


# ============================================================================
# Search/Content Factories
# ============================================================================


class SearchQueryFactory(factory.Factory):
    """Factory for search query test data"""

    class Meta:
        model = dict

    query = Faker("sentence", nb_words=3)
    sources = ["web", "arxiv", "pubmed"]
    max_results = 10
    enable_ml_enhancement = True
    filters = None


class SearchResultFactory(factory.Factory):
    """Factory for search result test data"""

    class Meta:
        model = dict

    id = Sequence(lambda n: f"result-{n}")
    title = Faker("sentence", nb_words=6)
    content = Faker("paragraph", nb_sentences=3)
    source = factory.Iterator(["arxiv", "pubmed", "web"])
    url = Faker("url")
    score = Faker("pyfloat", min_value=0.5, max_value=1.0)
    published_at = Faker("date_time_this_year", tzinfo=UTC)


# ============================================================================
# Database/Repository Factories
# ============================================================================


class TenantFactory(factory.Factory):
    """Factory for tenant test data"""

    class Meta:
        model = dict

    tenant_id = Sequence(lambda n: f"tenant-{n}")
    name = Faker("company")
    display_name = Faker("company")
    domain = Faker("domain_name")
    plan = "basic"
    is_active = True
    created_at = Faker("date_time_this_year", tzinfo=UTC)


class SessionFactory(factory.Factory):
    """Factory for session test data"""

    class Meta:
        model = dict

    session_id = Sequence(lambda n: f"sess_{n:032x}")
    tenant_id = "default"
    user_id = Sequence(lambda n: f"user-{n}")
    username = Sequence(lambda n: f"user{n}")
    role = "user"
    permissions = ["search:read", "search:write"]
    created_at = Faker("date_time_this_year", tzinfo=UTC)
    last_activity = Faker("date_time_this_hour", tzinfo=UTC)
    expires_at = Faker("date_time_this_month", tzinfo=UTC)


# ============================================================================
# API Request/Response Factories
# ============================================================================


class LoginRequestFactory(factory.Factory):
    """Factory for login request test data"""

    class Meta:
        model = dict

    username = Sequence(lambda n: f"user{n}")
    password = "password123"
    remember_me = False
    mfa_token = None


class TokenResponseFactory(factory.Factory):
    """Factory for token response test data"""

    class Meta:
        model = dict

    access_token = Sequence(lambda n: f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test{n}")
    token_type = "bearer"


# ============================================================================
# Batch Creation Helpers
# ============================================================================


def create_test_users(count: int = 5, **kwargs):
    """Create a batch of test users"""
    return [UserFactory(**kwargs) for _ in range(count)]


def create_test_search_results(count: int = 10, **kwargs):
    """Create a batch of test search results"""
    return [SearchResultFactory(**kwargs) for _ in range(count)]


def create_test_tenants(count: int = 3, **kwargs):
    """Create a batch of test tenants"""
    return [TenantFactory(**kwargs) for _ in range(count)]


# ============================================================================
# Specialized Factories for Testing Scenarios
# ============================================================================


class ExpiredSessionFactory(SessionFactory):
    """Factory for expired session test data"""

    expires_at = Faker(
        "date_time_between", start_date="-1d", end_date="-1h", tzinfo=UTC
    )


class PremiumTenantFactory(TenantFactory):
    """Factory for premium tenant test data"""

    plan = "premium"


class InactiveTenantFactory(TenantFactory):
    """Factory for inactive tenant test data"""

    is_active = False


# ============================================================================
# Factory Configuration
# ============================================================================

# Configure Faker locale if needed
factory.Faker._DEFAULT_LOCALE = "en_US"
