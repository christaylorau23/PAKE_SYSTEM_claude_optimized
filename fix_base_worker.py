#!/usr/bin/env python3
"""Fix F821 errors in base_worker.py"""

import re

def fix_base_worker():
    """Fix F821 errors in base_worker.py"""
    
    file_path = "/home/chris/PAKE_SYSTEM_claude_optimized/src/services/agents/base_worker.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix function signatures based on the F821 errors found
    fixes = [
        # _handle_task_message method
        (
            r'async def _handle_task_message\(self\) -> None:\n        """Handle task message from supervisor."""\n        if message\.target != self\.worker_id:',
            'async def _handle_task_message(self, message: Any) -> None:\n        """Handle task message from supervisor."""\n        if message.target != self.worker_id:'
        ),
        
        # _execute_task method
        (
            r'async def _execute_task\(self\) -> None:\n        """Execute task based on message content."""',
            'async def _execute_task(self, message: Any) -> None:\n        """Execute task based on message content."""'
        ),
        
        # _handle_system_event method
        (
            r'async def _handle_system_event\(self\) -> None:\n        """Handle system event message."""',
            'async def _handle_system_event(self, event: Any) -> None:\n        """Handle system event message."""'
        ),
        
        # _handle_health_check_request method
        (
            r'async def _handle_health_check_request\(self\) -> None:\n        """Handle health check request."""',
            'async def _handle_health_check_request(self, request: Any) -> None:\n        """Handle health check request."""'
        ),
        
        # _send_registration method
        (
            r'async def _send_registration\(self\) -> None:\n        """Send registration message to supervisor."""',
            'async def _send_registration(self, worker_type: str, capabilities: List[WorkerCapability]) -> None:\n        """Send registration message to supervisor."""'
        ),
        
        # _heartbeat_loop method
        (
            r'async def _heartbeat_loop\(self\) -> None:\n        """Send periodic heartbeat messages."""',
            'async def _heartbeat_loop(self, execution_time: float) -> None:\n        """Send periodic heartbeat messages."""'
        ),
        
        # Constructor method
        (
            r'def __init__\(self\) -> None:\n        """Initialize base worker agent."""\n        self\.worker_id = worker_id or f"worker_{uuid\.uuid4\(\)\.hex\[:8\]}"\n        self\.message_bus = message_bus',
            'def __init__(self, worker_id: str | None = None, message_bus: Any | None = None, name: str | None = None, description: str | None = None, capabilities: List[WorkerCapability] | None = None, input_types: List[str] | None = None, output_types: List[str] | None = None, metrics: Dict[str, Any] | None = None) -> None:\n        """Initialize base worker agent."""\n        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"\n        self.message_bus = message_bus'
        ),
    ]
    
    # Apply fixes
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed base_worker.py")

if __name__ == "__main__":
    fix_base_worker()
