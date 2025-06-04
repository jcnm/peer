#!/usr/bin/env python3
"""
Test script to verify that CommandType.QUIT properly terminates the program.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from peer.core.daemon import get_daemon
from peer.core.api import CoreRequest, CommandType, ResponseType, InterfaceType
from peer.core.protocol import CoreProtocol
import threading
import time

def test_quit_command():
    """Test that quit command sets shutdown flags and returns QUIT response."""
    print("🧪 Testing quit command functionality...")
    
    # Get daemon instance
    daemon = get_daemon()
    
    # Test initial state
    print(f"Initial shutdown state: {daemon.should_shutdown()}")
    assert not daemon.should_shutdown(), "Daemon should not be in shutdown state initially"
    
    # Create quit request
    request = CoreProtocol.create_request(
        command=CommandType.QUIT,
        interface_type=InterfaceType.SUI,
        parameters={},
        context={"test": True}
    )
    
    # Execute quit command
    print("📤 Sending quit command...")
    response = daemon.execute_command(request)
    
    # Verify response
    print(f"📥 Response type: {response.type}")
    print(f"📥 Response message: {response.message}")
    print(f"📥 Response data: {response.data}")
    
    assert response.type == ResponseType.QUIT, f"Expected QUIT response, got {response.type}"
    assert response.data.get('quit') is True, "Response should indicate quit"
    assert response.data.get('shutdown') is True, "Response should indicate shutdown"
    
    # Verify shutdown state
    print(f"Post-quit shutdown state: {daemon.should_shutdown()}")
    assert daemon.should_shutdown(), "Daemon should be in shutdown state after quit"
    
    # Verify shutdown event is set
    assert daemon.get_shutdown_event().is_set(), "Shutdown event should be set"
    
    print("✅ Quit command test passed!")
    return True

def test_shutdown_event_monitoring():
    """Test monitoring the shutdown event."""
    print("🧪 Testing shutdown event monitoring...")
    
    # Get daemon instance
    daemon = get_daemon()
    
    # Reset for clean test
    daemon._should_shutdown = False
    daemon.shutdown_event.clear()
    
    def monitor_shutdown():
        """Monitor shutdown event in separate thread."""
        print("👀 Monitoring shutdown event...")
        daemon.get_shutdown_event().wait(timeout=5)
        if daemon.get_shutdown_event().is_set():
            print("🔔 Shutdown event detected!")
            return True
        else:
            print("⏰ Timeout waiting for shutdown event")
            return False
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_shutdown)
    monitor_thread.start()
    
    # Wait a moment, then trigger quit
    time.sleep(1)
    
    request = CoreProtocol.create_request(
        command=CommandType.QUIT,
        interface_type=InterfaceType.SUI,
        parameters={},
        context={"test": True}
    )
    
    response = daemon.execute_command(request)
    
    # Wait for monitor thread
    monitor_thread.join(timeout=2)
    
    assert response.type == ResponseType.QUIT, "Should get QUIT response"
    assert daemon.should_shutdown(), "Should be in shutdown state"
    
    print("✅ Shutdown event monitoring test passed!")
    return True

if __name__ == "__main__":
    try:
        print("🚀 Starting CommandType.QUIT tests...")
        
        # Run tests
        test_quit_command()
        test_shutdown_event_monitoring()
        
        print("🎉 All tests passed! CommandType.QUIT now properly handles shutdown.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)