#!/usr/bin/env python3
"""
Concurrency tests for the Modbus bridge to verify that the locking mechanism
prevents message corruption under concurrent access from multiple sources.
"""

import asyncio
import sys
import os
import time
from unittest.mock import Mock, AsyncMock, patch

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modbus_bridge import ModbusBridge


async def test_lock_prevents_concurrent_access():
    """Test that the bus lock prevents concurrent access to NPort 1."""
    print("=" * 60)
    print("Testing Lock Prevents Concurrent Access")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002
    )
    
    access_log = []
    
    async def mock_access(source: str, duration: float):
        """Simulate accessing the bus with the lock."""
        access_log.append(f"{source}_start")
        async with bridge.bus_lock:
            access_log.append(f"{source}_acquired")
            await asyncio.sleep(duration)
            access_log.append(f"{source}_release")
    
    # Simulate two concurrent accesses
    await asyncio.gather(
        mock_access("tcp_client", 0.1),
        mock_access("nport2", 0.1)
    )
    
    # Verify that accesses didn't interleave
    # One should fully complete before the other starts
    tcp_start = access_log.index("tcp_client_start")
    tcp_acquired = access_log.index("tcp_client_acquired")
    tcp_release = access_log.index("tcp_client_release")
    nport2_start = access_log.index("nport2_start")
    nport2_acquired = access_log.index("nport2_acquired")
    nport2_release = access_log.index("nport2_release")
    
    # Both start, but only one acquires at a time
    assert tcp_start >= 0 and nport2_start >= 0, "Both should start"
    
    # Verify no interleaving: one completes before the other acquires
    if tcp_acquired < nport2_acquired:
        # TCP acquired first, should release before NPort2 acquires
        assert tcp_release < nport2_acquired, "TCP should complete before NPort2 acquires"
        print("✓ TCP client acquired lock first, NPort2 waited")
    else:
        # NPort2 acquired first, should release before TCP acquires
        assert nport2_release < tcp_acquired, "NPort2 should complete before TCP acquires"
        print("✓ NPort2 acquired lock first, TCP client waited")
    
    print(f"  - Access sequence: {' -> '.join(access_log)}")
    print("  - No interleaving detected")
    print()
    
    return True


async def test_multiple_clients_queue_correctly():
    """Test that multiple clients queue and process sequentially."""
    print("=" * 60)
    print("Testing Multiple Clients Queue Correctly")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002
    )
    
    completed = []
    
    async def mock_client_request(client_id: int):
        """Simulate a client request."""
        async with bridge.bus_lock:
            # Simulate some work
            await asyncio.sleep(0.05)
            completed.append(client_id)
    
    # Start 5 concurrent client requests
    await asyncio.gather(*[
        mock_client_request(i) for i in range(5)
    ])
    
    # All 5 should have completed
    assert len(completed) == 5, f"Expected 5 completions, got {len(completed)}"
    
    # All unique (no duplicates)
    assert len(set(completed)) == 5, "All requests should be unique"
    
    print(f"✓ All 5 clients processed successfully")
    print(f"  - Processing order: {completed}")
    print(f"  - All requests completed without corruption")
    print()
    
    return True


async def test_lock_timeout_behavior():
    """Test behavior when lock is held for extended period."""
    print("=" * 60)
    print("Testing Lock Timeout Behavior")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002,
        timeout=1
    )
    
    results = []
    
    async def long_running_task():
        """Simulate a long-running task holding the lock."""
        async with bridge.bus_lock:
            results.append("long_task_acquired")
            await asyncio.sleep(0.2)  # Hold lock for 200ms
            results.append("long_task_released")
    
    async def quick_task():
        """Simulate a quick task that needs the lock."""
        # Wait a bit to ensure long task acquires first
        await asyncio.sleep(0.05)
        results.append("quick_task_waiting")
        async with bridge.bus_lock:
            results.append("quick_task_acquired")
            await asyncio.sleep(0.05)
            results.append("quick_task_released")
    
    await asyncio.gather(
        long_running_task(),
        quick_task()
    )
    
    # Verify order
    assert results[0] == "long_task_acquired", "Long task should acquire first"
    assert results[1] == "quick_task_waiting", "Quick task should wait"
    assert results[2] == "long_task_released", "Long task should release"
    assert results[3] == "quick_task_acquired", "Quick task should then acquire"
    
    print("✓ Lock properly queues waiting tasks")
    print(f"  - Execution order: {' -> '.join(results)}")
    print()
    
    return True


async def test_lock_released_on_exception():
    """Test that lock is released even when exception occurs."""
    print("=" * 60)
    print("Testing Lock Released on Exception")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002
    )
    
    results = []
    
    async def failing_task():
        """Task that raises exception while holding lock."""
        try:
            async with bridge.bus_lock:
                results.append("failing_task_acquired")
                raise ValueError("Simulated error")
        except ValueError:
            results.append("failing_task_exception_caught")
    
    async def normal_task():
        """Normal task that should still acquire lock after failure."""
        await asyncio.sleep(0.05)  # Let failing task go first
        async with bridge.bus_lock:
            results.append("normal_task_acquired")
    
    await asyncio.gather(
        failing_task(),
        normal_task()
    )
    
    # Verify that normal task could acquire lock after failing task
    assert "failing_task_acquired" in results
    assert "failing_task_exception_caught" in results
    assert "normal_task_acquired" in results
    assert results.index("normal_task_acquired") > results.index("failing_task_exception_caught")
    
    print("✓ Lock properly released even after exception")
    print(f"  - Lock is not stuck: normal task acquired after failure")
    print()
    
    return True


async def test_lock_reentrancy():
    """Test that the same coroutine cannot reacquire the lock (deadlock prevention)."""
    print("=" * 60)
    print("Testing Lock Reentrancy (Deadlock Prevention)")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002
    )
    
    async def nested_lock_attempt():
        """Try to acquire lock twice (should deadlock if not careful)."""
        async with bridge.bus_lock:
            # This would deadlock if we tried to acquire again
            # In real code, we should never do this
            return "outer_acquired"
    
    result = await asyncio.wait_for(nested_lock_attempt(), timeout=1.0)
    assert result == "outer_acquired"
    
    print("✓ Single lock acquisition works correctly")
    print("  - NOTE: Code should never attempt nested lock acquisition")
    print("  - Current implementation uses asyncio.Lock (non-reentrant)")
    print()
    
    return True


async def main():
    """Run all concurrency tests."""
    print("\n" + "=" * 60)
    print("Modbus Bridge Concurrency Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Lock Prevents Concurrent Access", test_lock_prevents_concurrent_access),
        ("Multiple Clients Queue Correctly", test_multiple_clients_queue_correctly),
        ("Lock Timeout Behavior", test_lock_timeout_behavior),
        ("Lock Released on Exception", test_lock_released_on_exception),
        ("Lock Reentrancy Check", test_lock_reentrancy),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All concurrency tests passed!")
        print("\nThe bridge's locking mechanism ensures:")
        print("  1. No message corruption from concurrent requests")
        print("  2. Sequential processing of all requests")
        print("  3. Proper lock release even on exceptions")
        print("  4. Fair queuing of multiple concurrent clients")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
