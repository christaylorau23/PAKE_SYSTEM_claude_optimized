#!/usr/bin/env python3
"""PAKE System - n8n Workflow Manager
Provides a Python interface for triggering and managing n8n automation workflows.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class WorkflowRequest:
    """Represents a workflow execution request."""

    workflow_type: str
    payload: dict[str, Any]
    priority: str = "normal"
    timeout: int = 300  # 5 minutes default
    callback_url: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class WorkflowResult:
    """Represents a workflow execution result."""

    request_id: str
    workflow_type: str
    status: WorkflowStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time: float | None = None
    created_at: datetime = None
    completed_at: datetime | None = None


class N8nWorkflowManager:
    """Manages n8n workflow execution and monitoring for the PAKE system.
    Provides high-level interface for triggering automation workflows.
    """

    def __init__(self, n8n_base_url: str = None, auth_credentials: tuple = None):
        """Initialize the workflow manager.

        Args:
            n8n_base_url: Base URL for n8n instance (default: from env)
            auth_credentials: Tuple of (username, REDACTED_SECRET) for basic auth
        """
        self.base_url = n8n_base_url or os.getenv(
            "N8N_BASE_URL",
            "http://localhost:5678",
        )
        # SECURITY: Fail-fast approach - no hardcoded fallbacks
        n8n_user = os.getenv("N8N_USER")
        n8n_REDACTED_SECRET = os.getenv("N8N_PASSWORD")

        if not n8n_user or not n8n_REDACTED_SECRET:
            raise ValueError(
                "The N8N_USER and N8N_PASSWORD environment variables are not set. "
                "Please configure them before running the application. "
                "This is a security requirement."
            )

        self.auth = auth_credentials or (n8n_user, n8n_REDACTED_SECRET)

        # Workflow endpoint mappings
        self.workflow_endpoints = {
            "content_generation": "/webhook/trigger-content-generation",
            "social_media_publishing": "/webhook/trigger-social-media-publishing",
            "ai_processing": "/webhook/trigger-ai-processing",
            "knowledge_processing": "/webhook/trigger-knowledge-processing",
        }

        # Active workflow tracking
        self.active_workflows: dict[str, WorkflowResult] = {}

    async def trigger_content_generation(
        self,
        topic: str,
        content_type: str = "blog_post",
        target_audience: str = "general",
        tone: str = "professional",
        keywords: list[str] = None,
        callback_url: str = None,
    ) -> WorkflowResult:
        """Trigger content generation workflow.

        Args:
            topic: Content topic/subject
            content_type: Type of content ('blog_post', 'social_media', 'email_newsletter', 'product_description')
            target_audience: Target audience description
            tone: Content tone ('professional', 'casual', 'friendly', 'authoritative')
            keywords: List of keywords to incorporate
            callback_url: Optional callback URL for results

        Returns:
            WorkflowResult object with execution details
        """
        payload = {
            "topic": topic,
            "contentType": content_type,
            "targetAudience": target_audience,
            "tone": tone,
            "keywords": keywords or [],
            "callback_url": callback_url,
        }

        request = WorkflowRequest(
            workflow_type="content_generation",
            payload=payload,
            callback_url=callback_url,
        )

        return await self._execute_workflow(request)

    async def trigger_social_media_publishing(
        self,
        content_id: str,
        content: str,
        platforms: list[str] = None,
        content_type: str = "social_media",
        auto_publish: bool = True,
        scheduled_time: str = None,
    ) -> WorkflowResult:
        """Trigger social media publishing workflow.

        Args:
            content_id: Unique content identifier
            content: Content to publish
            platforms: List of platforms ('twitter', 'linkedin', 'facebook', 'instagram')
            content_type: Type of content being published
            auto_publish: Whether to auto-publish or queue for review
            scheduled_time: Optional scheduled publishing time (ISO format)

        Returns:
            WorkflowResult object with execution details
        """
        payload = {
            "content_id": content_id,
            "content": content,
            "platforms": platforms or ["twitter", "linkedin", "facebook"],
            "contentType": content_type,
            "auto_publish": auto_publish,
            "scheduled_time": scheduled_time,
        }

        request = WorkflowRequest(
            workflow_type="social_media_publishing",
            payload=payload,
        )

        return await self._execute_workflow(request)

    async def trigger_ai_processing(
        self,
        processing_type: str,
        input_data: str,
        options: dict[str, Any] = None,
        priority: str = "normal",
        callback_url: str = None,
    ) -> WorkflowResult:
        """Trigger AI processing workflow.

        Args:
            processing_type: Type of AI processing ('text_analysis', 'text_generation', 'code_generation',
                           'image_analysis', 'voice_synthesis', 'video_generation')
            input_data: Input data for processing
            options: Additional processing options
            priority: Processing priority ('low', 'normal', 'high', 'urgent')
            callback_url: Optional callback URL for results

        Returns:
            WorkflowResult object with execution details
        """
        payload = {
            "processing_type": processing_type,
            "input_data": input_data,
            "options": options or {},
            "priority": priority,
            "callback_url": callback_url,
        }

        request = WorkflowRequest(
            workflow_type="ai_processing",
            payload=payload,
            priority=priority,
            callback_url=callback_url,
        )

        return await self._execute_workflow(request)

    async def trigger_knowledge_processing(
        self,
        document_type: str,
        source: str,
        metadata: dict[str, Any] = None,
        auto_index: bool = True,
        confidence_threshold: float = 0.7,
    ) -> WorkflowResult:
        """Trigger knowledge processing workflow.

        Args:
            document_type: Type of document ('pdf', 'markdown', 'text', 'url', 'code')
            source: Source path, URL, or content
            metadata: Document metadata (title, author, tags, etc.)
            auto_index: Whether to automatically index if confidence is high
            confidence_threshold: Minimum confidence for auto-indexing

        Returns:
            WorkflowResult object with execution details
        """
        payload = {
            "document_type": document_type,
            "source": source,
            "metadata": metadata or {},
            "auto_index": auto_index,
            "confidence_threshold": confidence_threshold,
        }

        request = WorkflowRequest(workflow_type="knowledge_processing", payload=payload)

        return await self._execute_workflow(request)

    async def _execute_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        """Execute a workflow request.

        Args:
            request: WorkflowRequest object

        Returns:
            WorkflowResult object
        """
        request_id = (
            f"{request.workflow_type}_{int(datetime.now().timestamp())}_{id(request)}"
        )

        # Create workflow result tracking
        workflow_result = WorkflowResult(
            request_id=request_id,
            workflow_type=request.workflow_type,
            status=WorkflowStatus.PENDING,
            created_at=datetime.now(),
        )

        self.active_workflows[request_id] = workflow_result

        try:
            # Get workflow endpoint
            endpoint = self.workflow_endpoints.get(request.workflow_type)
            if not endpoint:
                raise ValueError(f"Unknown workflow type: {request.workflow_type}")

            url = f"{self.base_url}{endpoint}"

            # Execute workflow
            async with aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.auth[0], self.auth[1]),
            ) as session:
                workflow_result.status = WorkflowStatus.RUNNING
                start_time = datetime.now()

                logger.info(
                    f"Triggering workflow {request.workflow_type} with request ID {
                        request_id
                    }",
                )

                async with session.post(
                    url,
                    json=request.payload,
                    timeout=aiohttp.ClientTimeout(total=request.timeout),
                ) as response:
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()

                    workflow_result.execution_time = execution_time
                    workflow_result.completed_at = end_time

                    if response.status == 200:
                        result_data = await response.json()
                        workflow_result.status = WorkflowStatus.SUCCESS
                        workflow_result.result = result_data

                        logger.info(
                            f"Workflow {
                                request.workflow_type
                            } completed successfully in {execution_time:.2f}s",
                        )
                    else:
                        error_text = await response.text()
                        workflow_result.status = WorkflowStatus.FAILED
                        workflow_result.error = f"HTTP {response.status}: {error_text}"

                        logger.error(
                            f"Workflow {request.workflow_type} failed: {
                                workflow_result.error
                            }",
                        )

        except TimeoutError:
            workflow_result.status = WorkflowStatus.TIMEOUT
            workflow_result.error = (
                f"Workflow timed out after {request.timeout} seconds"
            )
            workflow_result.completed_at = datetime.now()

            logger.error(f"Workflow {request.workflow_type} timed out")

        except Exception as e:
            workflow_result.status = WorkflowStatus.FAILED
            workflow_result.error = str(e)
            workflow_result.completed_at = datetime.now()

            logger.error(f"Workflow {request.workflow_type} failed with exception: {e}")

        return workflow_result

    async def get_workflow_status(self, request_id: str) -> WorkflowResult | None:
        """Get status of a workflow execution.

        Args:
            request_id: Workflow request ID

        Returns:
            WorkflowResult object or None if not found
        """
        return self.active_workflows.get(request_id)

    async def list_active_workflows(self) -> list[WorkflowResult]:
        """List all active/tracked workflows.

        Returns:
            List of WorkflowResult objects
        """
        return list(self.active_workflows.values())

    async def cancel_workflow(self, request_id: str) -> bool:
        """Cancel a running workflow (if supported by n8n).

        Args:
            request_id: Workflow request ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        workflow = self.active_workflows.get(request_id)
        if not workflow or workflow.status not in [
            WorkflowStatus.PENDING,
            WorkflowStatus.RUNNING,
        ]:
            return False

        try:
            # Note: n8n doesn't have a direct cancel API, so this is a placeholder
            # In practice, you might need to implement this through n8n's API or
            # database
            workflow.status = WorkflowStatus.FAILED
            workflow.error = "Workflow cancelled by user"
            workflow.completed_at = datetime.now()

            logger.info(f"Workflow {request_id} marked as cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow {request_id}: {e}")
            return False

    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """Clean up completed workflow tracking data.

        Args:
            max_age_hours: Maximum age in hours for completed workflows to keep
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        to_remove = []
        for request_id, workflow in self.active_workflows.items():
            if (
                workflow.status
                in [
                    WorkflowStatus.SUCCESS,
                    WorkflowStatus.FAILED,
                    WorkflowStatus.TIMEOUT,
                ]
                and workflow.completed_at
                and workflow.completed_at.timestamp() < cutoff_time
            ):
                to_remove.append(request_id)

        for request_id in to_remove:
            del self.active_workflows[request_id]

        logger.info(f"Cleaned up {len(to_remove)} completed workflows")


# Example usage and testing functions
async def example_content_generation():
    """Example of using the content generation workflow."""
    manager = N8nWorkflowManager()

    result = await manager.trigger_content_generation(
        topic="The Future of AI in Enterprise Automation",
        content_type="blog_post",
        target_audience="technology professionals",
        tone="professional",
        keywords=[
            "AI",
            "automation",
            "enterprise",
            "efficiency",
            "digital transformation",
        ],
    )

    print(f"Content Generation Result: {result.status}")
    if result.result:
        print(f"Generated content ID: {result.result.get('content_id')}")

    return result


async def example_ai_processing():
    """Example of using the AI processing workflow."""
    manager = N8nWorkflowManager()

    result = await manager.trigger_ai_processing(
        processing_type="text_analysis",
        input_data="Analyze the sentiment and key themes in this business document: Our company has shown remarkable growth this quarter with a 23% increase in revenue and positive customer feedback across all product lines.",
        priority="high",
    )

    print(f"AI Processing Result: {result.status}")
    if result.result:
        print(f"Analysis result: {result.result}")

    return result


async def example_knowledge_processing():
    """Example of using the knowledge processing workflow."""
    manager = N8nWorkflowManager()

    result = await manager.trigger_knowledge_processing(
        document_type="text",
        source="This is a sample document about machine learning algorithms. It covers supervised learning, unsupervised learning, and reinforcement learning approaches used in modern AI systems.",
        metadata={
            "title": "Machine Learning Algorithms Overview",
            "author": "AI Research Team",
            "tags": ["machine-learning", "AI", "algorithms"],
            "category": "Technical Documentation",
        },
    )

    print(f"Knowledge Processing Result: {result.status}")
    if result.result:
        print(
            f"Document processed with confidence: {
                result.result.get('processing_result', {}).get('confidence_score')
            }",
        )

    return result


if __name__ == "__main__":
    """
    Run example workflow executions for testing.
    """

    async def run_examples():
        print("🚀 PAKE System - n8n Workflow Manager Examples")
        print("=" * 50)

        # Example 1: Content Generation
        print("\n1. Testing Content Generation Workflow...")
        content_result = await example_content_generation()

        # Example 2: AI Processing
        print("\n2. Testing AI Processing Workflow...")
        ai_result = await example_ai_processing()

        # Example 3: Knowledge Processing
        print("\n3. Testing Knowledge Processing Workflow...")
        knowledge_result = await example_knowledge_processing()

        print("\n✅ All workflow examples completed!")
        print(f"Content Generation: {content_result.status}")
        print(f"AI Processing: {ai_result.status}")
        print(f"Knowledge Processing: {knowledge_result.status}")

    # Run the examples
    asyncio.run(run_examples())
