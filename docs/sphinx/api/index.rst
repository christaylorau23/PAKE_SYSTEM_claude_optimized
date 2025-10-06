API Reference
=============

The PAKE System provides a comprehensive REST API for all system operations. This section contains the complete API reference documentation, automatically generated from the codebase docstrings.

.. toctree::
   :maxdepth: 2
   :caption: API Documentation:

   authentication
   data_ingestion
   analytics
   configuration
   monitoring
   admin

Overview
--------

The PAKE System API is built on FastAPI and provides:

* **RESTful Design**: Standard REST API patterns and conventions
* **Automatic Documentation**: Interactive API documentation with Swagger UI
* **Type Safety**: Comprehensive type annotations and validation
* **Authentication**: JWT-based authentication with role-based authorization
* **Rate Limiting**: Built-in rate limiting and request throttling
* **Error Handling**: Consistent error responses with detailed information

Base URL
~~~~~~~~

All API endpoints are prefixed with ``/api/v1``:

.. code-block:: text

    https://your-domain.com/api/v1/

Authentication
~~~~~~~~~~~~~~

Most API endpoints require authentication. Include the JWT token in the Authorization header:

.. code-block:: text

    Authorization: Bearer <your-jwt-token>

Response Format
~~~~~~~~~~~~~~~

All API responses follow a consistent format:

.. code-block:: json

    {
        "success": true,
        "data": { ... },
        "error": null,
        "timestamp": "2025-01-03T10:30:00Z"
    }

Error Responses
~~~~~~~~~~~~~~~

Error responses include detailed error information:

.. code-block:: json

    {
        "success": false,
        "data": null,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": {
                "field": "email",
                "reason": "Invalid email format"
            }
        },
        "timestamp": "2025-01-03T10:30:00Z"
    }

Rate Limiting
~~~~~~~~~~~~~

API endpoints are rate-limited to ensure fair usage:

* **Authentication endpoints**: 5 requests per minute
* **Data ingestion**: 100 requests per minute
* **Analytics endpoints**: 50 requests per minute
* **Configuration endpoints**: 20 requests per minute

Rate limit headers are included in responses:

.. code-block:: text

    X-RateLimit-Limit: 100
    X-RateLimit-Remaining: 95
    X-RateLimit-Reset: 1641234567

Status Codes
~~~~~~~~~~~~

The API uses standard HTTP status codes:

* **200 OK**: Request successful
* **201 Created**: Resource created successfully
* **400 Bad Request**: Invalid request data
* **401 Unauthorized**: Authentication required
* **403 Forbidden**: Insufficient permissions
* **404 Not Found**: Resource not found
* **429 Too Many Requests**: Rate limit exceeded
* **500 Internal Server Error**: Server error

API Endpoints
-------------

Authentication Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.authentication.jwt_auth_service
   :members:

Data Ingestion Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.ingestion.production_orchestrator
   :members:

Analytics Endpoints
~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.analytics.intelligence_insight_service
   :members:

Configuration Endpoints
~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.pake_system.core.config
   :members:

Monitoring Endpoints
~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.monitoring.enterprise_monitoring_service
   :members:

Admin Endpoints
~~~~~~~~~~~~~~~

.. automodule:: src.api.enterprise.tenant_endpoints
   :members:

Data Models
-----------

The API uses Pydantic models for request and response validation. All models are automatically documented and validated.

Authentication Models
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.authentication.models
   :members:

Data Ingestion Models
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.services.ingestion.models
   :members:

Analytics Models
~~~~~~~~~~~~~~~~

.. automodule:: src.services.analytics.models
   :members:

Configuration Models
~~~~~~~~~~~~~~~~~~~~

.. automodule:: src.pake_system.core.models
   :members:

Monitoring Models
~~~~~~~~~~~~~~~~~

.. automodule:: src.services.monitoring.models
   :members:

SDK and Client Libraries
-------------------------

The PAKE System provides client libraries for popular programming languages:

Python SDK
~~~~~~~~~~

.. code-block:: python

    from pake_sdk import PAKEClient
    
    client = PAKEClient(
        base_url="https://your-domain.com/api/v1",
        api_key="your-api-key"
    )
    
    # Authenticate
    token = await client.auth.login("username", "password")
    
    # Ingest data
    result = await client.data.ingest({
        "source": "api",
        "data": {"key": "value"}
    })
    
    # Get analytics
    analytics = await client.analytics.get_trends()

JavaScript SDK
~~~~~~~~~~~~~~

.. code-block:: javascript

    import { PAKEClient } from '@pake/sdk';
    
    const client = new PAKEClient({
        baseUrl: 'https://your-domain.com/api/v1',
        apiKey: 'your-api-key'
    });
    
    // Authenticate
    const token = await client.auth.login('username', 'password');
    
    // Ingest data
    const result = await client.data.ingest({
        source: 'api',
        data: { key: 'value' }
    });
    
    // Get analytics
    const analytics = await client.analytics.getTrends();

Webhooks
--------

The PAKE System supports webhooks for real-time notifications:

Webhook Events
~~~~~~~~~~~~~~

* **data.ingested**: Data successfully ingested
* **analysis.completed**: Analysis completed
* **trend.detected**: New trend detected
* **alert.triggered**: Alert triggered
* **user.created**: User account created

Webhook Payload
~~~~~~~~~~~~~~~

Webhook payloads include event metadata and data:

.. code-block:: json

    {
        "event": "data.ingested",
        "timestamp": "2025-01-03T10:30:00Z",
        "data": {
            "source": "api",
            "record_count": 100,
            "processing_time": 1.5
        },
        "webhook_id": "wh_1234567890"
    }

Webhook Security
~~~~~~~~~~~~~~~~

Webhooks are secured with HMAC signatures:

.. code-block:: text

    X-PAKE-Signature: sha256=abc123def456...

Testing
-------

The API includes comprehensive testing endpoints for development and debugging:

Health Check
~~~~~~~~~~~~

.. code-block:: text

    GET /api/v1/health

Returns system health status:

.. code-block:: json

    {
        "status": "healthy",
        "timestamp": "2025-01-03T10:30:00Z",
        "services": {
            "database": "healthy",
            "cache": "healthy",
            "queue": "healthy"
        }
    }

Metrics Endpoint
~~~~~~~~~~~~~~~~

.. code-block:: text

    GET /api/v1/metrics

Returns system metrics (requires admin authentication):

.. code-block:: json

    {
        "requests_per_second": 150,
        "active_users": 25,
        "data_ingestion_rate": 1000,
        "cache_hit_rate": 0.95
    }

Interactive Documentation
-------------------------

The API provides interactive documentation through Swagger UI:

* **Swagger UI**: ``https://your-domain.com/docs``
* **ReDoc**: ``https://your-domain.com/redoc``
* **OpenAPI Schema**: ``https://your-domain.com/openapi.json``

The interactive documentation allows you to:

* Browse all available endpoints
* Test API calls directly from the browser
* View request/response examples
* Download API schemas

This API reference provides comprehensive documentation for all PAKE System API endpoints. For additional information, refer to the interactive documentation or contact the development team.
