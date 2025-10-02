#!/usr/bin/env python3
"""
PAKE System - Vercel API Entry Point
Simplified FastAPI application for Vercel deployment
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from datetime import datetime

# Create FastAPI app
app = FastAPI(
    title="PAKE System API",
    description="Enterprise Knowledge Management & AI Research Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
    timestamp: str

class SystemInfo(BaseModel):
    name: str
    version: str
    description: str
    features: list[str]

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Main landing page"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PAKE System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .feature { margin: 20px 0; padding: 15px; background: #ecf0f1; border-radius: 5px; }
            .api-link { display: inline-block; margin: 10px; padding: 10px 20px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; }
            .api-link:hover { background: #2980b9; }
            .status { text-align: center; margin: 20px 0; }
            .status.online { color: #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 PAKE System</h1>
            <div class="status online">
                <h2>✅ System Online</h2>
                <p>Enterprise Knowledge Management & AI Research Platform</p>
            </div>

            <div class="feature">
                <h3>🔧 Available Features</h3>
                <ul>
                    <li>Multi-tenant Architecture</li>
                    <li>AI-Powered Research</li>
                    <li>Knowledge Management</li>
                    <li>Real-time Analytics</li>
                    <li>Enterprise Security</li>
                </ul>
            </div>

            <div class="feature">
                <h3>📚 API Documentation</h3>
                <a href="/docs" class="api-link">📖 Swagger UI</a>
                <a href="/redoc" class="api-link">📋 ReDoc</a>
                <a href="/health" class="api-link">❤️ Health Check</a>
                <a href="/system" class="api-link">ℹ️ System Info</a>
            </div>

            <div class="feature">
                <h3>🔗 Quick Links</h3>
                <p>Explore the PAKE System API endpoints:</p>
                <ul>
                    <li><strong>GET /health</strong> - System health status</li>
                    <li><strong>GET /system</strong> - System information</li>
                    <li><strong>GET /docs</strong> - Interactive API documentation</li>
                    <li><strong>POST /api/v1/search</strong> - Knowledge search</li>
                    <li><strong>POST /api/v1/analyze</strong> - AI analysis</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="PAKE System is running successfully",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.get("/system", response_model=SystemInfo)
async def system_info():
    """System information endpoint"""
    return SystemInfo(
        name="PAKE System",
        version="1.0.0",
        description="Enterprise Knowledge Management & AI Research Platform",
        features=[
            "Multi-tenant Architecture",
            "AI-Powered Research",
            "Knowledge Management",
            "Real-time Analytics",
            "Enterprise Security",
            "RESTful API",
            "GraphQL Support",
            "WebSocket Real-time Updates"
        ]
    )

@app.get("/api/v1/search")
async def search_knowledge(query: str = "", limit: int = 10):
    """Knowledge search endpoint"""
    results = [
        {
            "id": f"result_{i}",
            "title": f"Search Result {i}",
            "content": f"This is a mock search result for query: '{query}'",
            "relevance": 0.9 - (i * 0.1),
            "source": "PAKE System Knowledge Base"
        }
        for i in range(min(limit, 5))
    ]

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/analyze")
async def analyze_content(data: dict):
    """AI content analysis endpoint"""
    content = data.get("content", "")

    analysis = {
        "sentiment": "positive",
        "topics": ["AI", "Knowledge Management", "Enterprise"],
        "summary": f"Analysis of content: {content[:100]}...",
        "confidence": 0.85,
        "recommendations": [
            "Consider adding more technical details",
            "Include examples for better understanding"
        ]
    }

    return {
        "analysis": analysis,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/services")
async def list_services():
    """List available PAKE System services"""
    services = [
        {
            "name": "Knowledge Management",
            "status": "active",
            "endpoints": ["/api/v1/search", "/api/v1/analyze"]
        },
        {
            "name": "AI Research Engine",
            "status": "active",
            "endpoints": ["/api/v1/research", "/api/v1/insights"]
        },
        {
            "name": "Multi-tenant Auth",
            "status": "active",
            "endpoints": ["/api/v1/auth", "/api/v1/tenants"]
        },
        {
            "name": "Analytics Dashboard",
            "status": "active",
            "endpoints": ["/api/v1/metrics", "/api/v1/reports"]
        }
    ]

    return {
        "services": services,
        "total": len(services),
        "status": "operational"
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "message": "The requested resource does not exist"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )

# Vercel handler
def handler(request):
    return app(request.scope, request.receive, request.send)