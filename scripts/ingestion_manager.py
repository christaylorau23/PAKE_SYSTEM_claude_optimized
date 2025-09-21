#!/usr/bin/env python3
"""
PAKE+ Ingestion Manager
Web interface and management tools for the ingestion pipeline
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from ingestion_pipeline import SourceConfig, UniversalIngestionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PAKE+ Ingestion Manager",
    description="Management interface for the PAKE+ content ingestion pipeline",
    version="1.0.0",
)

# Global pipeline instance
pipeline_instance: UniversalIngestionPipeline | None = None
background_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize the ingestion pipeline on startup"""
    global pipeline_instance

    pipeline_instance = UniversalIngestionPipeline()
    await pipeline_instance.initialize()

    logger.info("Ingestion manager started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global pipeline_instance, background_task

    if background_task and not background_task.done():
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

    if pipeline_instance:
        await pipeline_instance.close()

    logger.info("Ingestion manager shut down")


def get_pipeline() -> UniversalIngestionPipeline:
    """Dependency to get the pipeline instance"""
    if pipeline_instance is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline_instance


# API Endpoints


@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "PAKE+ Ingestion Manager",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "sources": "/sources",
            "statistics": "/stats",
            "start_pipeline": "/pipeline/start",
            "stop_pipeline": "/pipeline/stop",
            "run_cycle": "/pipeline/run",
            "dashboard": "/dashboard",
        },
    }


@app.get("/sources", response_model=list[dict[str, Any]])
async def get_sources(pipeline: UniversalIngestionPipeline = Depends(get_pipeline)):
    """Get all configured sources"""
    sources_data = []

    for source in pipeline.sources:
        # Don't expose sensitive credentials
        source_dict = {
            "name": source.name,
            "type": source.type,
            "url": source.url if source.type != "email" else "[HIDDEN]",
            "interval": source.interval,
            "enabled": source.enabled,
            "metadata": source.metadata,
            "filters": source.filters,
        }
        sources_data.append(source_dict)

    return sources_data


@app.post("/sources")
async def add_source(
    source_data: dict[str, Any],
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Add a new ingestion source"""
    try:
        # Validate required fields
        required_fields = ["name", "type", "url"]
        for field in required_fields:
            if field not in source_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}",
                )

        # Create source config
        source = SourceConfig(**source_data)

        # Add to pipeline
        pipeline.sources.append(source)

        # Save to configuration file
        await save_configuration(pipeline)

        return {"message": f"Source '{source.name}' added successfully"}

    except Exception as e:
        logger.error(f"Error adding source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/sources/{source_name}")
async def update_source(
    source_name: str,
    updates: dict[str, Any],
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Update an existing source"""
    try:
        # Find the source
        source_index = None
        for i, source in enumerate(pipeline.sources):
            if source.name == source_name:
                source_index = i
                break

        if source_index is None:
            raise HTTPException(status_code=404, detail="Source not found")

        # Update source attributes
        source = pipeline.sources[source_index]
        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)

        # Save configuration
        await save_configuration(pipeline)

        return {"message": f"Source '{source_name}' updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sources/{source_name}")
async def delete_source(
    source_name: str,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Delete a source"""
    try:
        # Find and remove the source
        original_count = len(pipeline.sources)
        pipeline.sources = [s for s in pipeline.sources if s.name != source_name]

        if len(pipeline.sources) == original_count:
            raise HTTPException(status_code=404, detail="Source not found")

        # Save configuration
        await save_configuration(pipeline)

        return {"message": f"Source '{source_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sources/{source_name}/enable")
async def enable_source(
    source_name: str,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Enable a source"""
    return await toggle_source(source_name, True, pipeline)


@app.post("/sources/{source_name}/disable")
async def disable_source(
    source_name: str,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Disable a source"""
    return await toggle_source(source_name, False, pipeline)


async def toggle_source(
    source_name: str,
    enabled: bool,
    pipeline: UniversalIngestionPipeline,
):
    """Toggle source enabled/disabled state"""
    try:
        # Find the source
        source_found = False
        for source in pipeline.sources:
            if source.name == source_name:
                source.enabled = enabled
                source_found = True
                break

        if not source_found:
            raise HTTPException(status_code=404, detail="Source not found")

        # Save configuration
        await save_configuration(pipeline)

        action = "enabled" if enabled else "disabled"
        return {"message": f"Source '{source_name}' {action} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_statistics(pipeline: UniversalIngestionPipeline = Depends(get_pipeline)):
    """Get ingestion statistics"""
    try:
        stats = pipeline.get_ingestion_statistics()

        # Add real-time pipeline status
        stats["pipeline_status"] = {
            "running": background_task is not None and not background_task.done(),
            "sources_configured": len(pipeline.sources),
            "sources_enabled": len([s for s in pipeline.sources if s.enabled]),
            "last_check": datetime.utcnow().isoformat(),
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline/start")
async def start_pipeline(
    background_tasks: BackgroundTasks,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Start the continuous ingestion pipeline"""
    global background_task

    if background_task and not background_task.done():
        raise HTTPException(status_code=400, detail="Pipeline is already running")

    # Start the pipeline in the background
    background_task = asyncio.create_task(pipeline.run_continuous())

    return {"message": "Ingestion pipeline started"}


@app.post("/pipeline/stop")
async def stop_pipeline():
    """Stop the continuous ingestion pipeline"""
    global background_task

    if not background_task or background_task.done():
        raise HTTPException(status_code=400, detail="Pipeline is not running")

    # Cancel the background task
    background_task.cancel()

    try:
        await background_task
    except asyncio.CancelledError:
        pass

    background_task = None

    return {"message": "Ingestion pipeline stopped"}


@app.post("/pipeline/run")
async def run_single_cycle(
    background_tasks: BackgroundTasks,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Run a single ingestion cycle"""

    async def run_cycle():
        try:
            processed = await pipeline.run_single_cycle()
            logger.info(f"Single cycle completed, processed {processed} items")
        except Exception as e:
            logger.error(f"Error in single cycle: {e}")

    background_tasks.add_task(run_cycle)

    return {"message": "Single ingestion cycle started"}


@app.get("/pipeline/status")
async def get_pipeline_status():
    """Get current pipeline status"""
    global background_task

    is_running = background_task is not None and not background_task.done()

    status = {
        "running": is_running,
        "task_id": id(background_task) if background_task else None,
        "uptime": None,  # Could add uptime tracking if needed
    }

    return status


@app.post("/sources/{source_name}/test")
async def test_source(
    source_name: str,
    pipeline: UniversalIngestionPipeline = Depends(get_pipeline),
):
    """Test a specific source without full ingestion"""
    try:
        # Find the source
        source = None
        for s in pipeline.sources:
            if s.name == source_name:
                source = s
                break

        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Test the source
        items = []

        if source.type == "rss":
            items = await pipeline.ingest_rss_feeds(source)
        elif source.type == "email":
            items = await pipeline.ingest_email(source)
        elif source.type == "web":
            items = await pipeline.ingest_web_content(source)
        elif source.type == "file":
            items = await pipeline.process_file_source(source)

        # Return summary without processing items
        return {
            "source_name": source_name,
            "items_found": len(items),
            "test_successful": True,
            "sample_titles": [item.title for item in items[:5]],  # First 5 titles
        }

    except Exception as e:
        logger.error(f"Error testing source {source_name}: {e}")
        return {
            "source_name": source_name,
            "items_found": 0,
            "test_successful": False,
            "error": str(e),
        }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple web dashboard for monitoring"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PAKE+ Ingestion Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1, h2 { color: #333; }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .status.running { background: #d4edda; color: #155724; }
            .status.stopped { background: #f8d7da; color: #721c24; }
            button { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #007bff; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-info { background: #17a2b8; color: white; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f8f9fa; }
            .enabled { color: #28a745; font-weight: bold; }
            .disabled { color: #dc3545; }
            #stats, #sources { margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PAKE+ Ingestion Dashboard</h1>

            <div id="pipeline-status" class="status stopped">
                <strong>Status:</strong> <span id="status-text">Loading...</span>
            </div>

            <div>
                <button class="btn-success" onclick="startPipeline()">Start Pipeline</button>
                <button class="btn-danger" onclick="stopPipeline()">Stop Pipeline</button>
                <button class="btn-info" onclick="runCycle()">Run Single Cycle</button>
                <button class="btn-primary" onclick="refreshData()">Refresh</button>
            </div>

            <div id="stats">
                <h2>Statistics</h2>
                <div id="stats-content">Loading statistics...</div>
            </div>

            <div id="sources">
                <h2>Sources</h2>
                <div id="sources-content">Loading sources...</div>
            </div>
        </div>

        <script>
            async function fetchStatus() {
                try {
                    const response = await fetch('/pipeline/status');
                    const status = await response.json();

                    const statusEl = document.getElementById('pipeline-status');
                    const statusText = document.getElementById('status-text');

                    if (status.running) {
                        statusEl.className = 'status running';
                        statusText.textContent = 'Running';
                    } else {
                        statusEl.className = 'status stopped';
                        statusText.textContent = 'Stopped';
                    }
                } catch (error) {
                    console.error('Error fetching status:', error);
                }
            }

            async function fetchStats() {
                try {
                    const response = await fetch('/stats');
                    const stats = await response.json();

                    document.getElementById('stats-content').innerHTML = `
                        <p><strong>Total Items:</strong> ${stats.total_items}</p>
                        <p><strong>Processed Items:</strong> ${stats.processed_items}</p>
                        <p><strong>Sources Configured:</strong> ${stats.sources_configured}</p>
                        <p><strong>Sources Enabled:</strong> ${stats.sources_enabled}</p>
                    `;
                } catch (error) {
                    document.getElementById('stats-content').innerHTML = 'Error loading statistics';
                    console.error('Error fetching stats:', error);
                }
            }

            async function fetchSources() {
                try {
                    const response = await fetch('/sources');
                    const sources = await response.json();

                    let html = '<table><tr><th>Name</th><th>Type</th><th>Status</th><th>Interval (s)</th><th>Actions</th></tr>';

                    sources.forEach(source => {
                        const statusClass = source.enabled ? 'enabled' : 'disabled';
                        const statusText = source.enabled ? 'Enabled' : 'Disabled';
                        const actionButton = source.enabled
                            ? `<button class="btn-danger" onclick="toggleSource('${source.name}', false)">Disable</button>`
                            : `<button class="btn-success" onclick="toggleSource('${source.name}', true)">Enable</button>`;

                        html += `
                            <tr>
                                <td>${source.name}</td>
                                <td>${source.type}</td>
                                <td class="${statusClass}">${statusText}</td>
                                <td>${source.interval}</td>
                                <td>
                                    ${actionButton}
                                    <button class="btn-info" onclick="testSource('${source.name}')">Test</button>
                                </td>
                            </tr>
                        `;
                    });

                    html += '</table>';
                    document.getElementById('sources-content').innerHTML = html;
                } catch (error) {
                    document.getElementById('sources-content').innerHTML = 'Error loading sources';
                    console.error('Error fetching sources:', error);
                }
            }

            async function startPipeline() {
                try {
                    const response = await fetch('/pipeline/start', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    fetchStatus();
                } catch (error) {
                    alert('Error starting pipeline');
                    console.error(error);
                }
            }

            async function stopPipeline() {
                try {
                    const response = await fetch('/pipeline/stop', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    fetchStatus();
                } catch (error) {
                    alert('Error stopping pipeline');
                    console.error(error);
                }
            }

            async function runCycle() {
                try {
                    const response = await fetch('/pipeline/run', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                } catch (error) {
                    alert('Error running cycle');
                    console.error(error);
                }
            }

            async function toggleSource(sourceName, enable) {
                const action = enable ? 'enable' : 'disable';
                try {
                    const response = await fetch(`/sources/${sourceName}/${action}`, { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    fetchSources();
                } catch (error) {
                    alert(`Error ${action}ing source`);
                    console.error(error);
                }
            }

            async function testSource(sourceName) {
                try {
                    const response = await fetch(`/sources/${sourceName}/test`, { method: 'POST' });
                    const result = await response.json();

                    if (result.test_successful) {
                        alert(`Test successful! Found ${result.items_found} items.`);
                    } else {
                        alert(`Test failed: ${result.error}`);
                    }
                } catch (error) {
                    alert('Error testing source');
                    console.error(error);
                }
            }

            function refreshData() {
                fetchStatus();
                fetchStats();
                fetchSources();
            }

            // Initial load and refresh every 30 seconds
            refreshData();
            setInterval(refreshData, 30000);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


async def save_configuration(pipeline: UniversalIngestionPipeline):
    """Save current configuration to file"""
    try:
        config_data = {"sources": []}

        for source in pipeline.sources:
            source_dict = {
                "name": source.name,
                "type": source.type,
                "url": source.url,
                "interval": source.interval,
                "enabled": source.enabled,
                "metadata": source.metadata,
                "filters": source.filters,
            }

            # Only include credentials if they exist (be careful with sensitive data)
            if source.credentials:
                source_dict["credentials"] = source.credentials

            config_data["sources"].append(source_dict)

        with open(pipeline.config_path, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info("Configuration saved successfully")

    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
