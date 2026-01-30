#!/usr/bin/env python3
"""
Simple test/demo script to verify the Modbus bridge configuration and basic functionality.
This does not require actual Moxa NPort devices to run - it just validates the code structure.
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modbus_bridge import ModbusBridge, load_config


async def test_bridge_initialization():
    """Test that the bridge can be initialized with valid configuration."""
    print("=" * 60)
    print("Testing Modbus Bridge Initialization")
    print("=" * 60)
    
    # Test with default configuration
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002,
        listen_host='0.0.0.0',
        listen_port=5020,
        timeout=3
    )
    
    print("✓ Bridge instance created successfully")
    print(f"  - NPort 1: {bridge.nport1_host}:{bridge.nport1_port}")
    print(f"  - NPort 2: {bridge.nport2_host}:{bridge.nport2_port}")
    print(f"  - TCP Server: {bridge.listen_host}:{bridge.listen_port}")
    print(f"  - Timeout: {bridge.timeout}s")
    print(f"  - Bus lock: {bridge.bus_lock}")
    print()
    
    return True


def test_config_loading():
    """Test configuration loading from environment variables."""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    
    # Set test environment variables
    os.environ['NPORT1_HOST'] = '10.0.0.10'
    os.environ['NPORT1_PORT'] = '5001'
    os.environ['NPORT2_HOST'] = '10.0.0.20'
    os.environ['NPORT2_PORT'] = '5002'
    os.environ['LISTEN_HOST'] = '127.0.0.1'
    os.environ['LISTEN_PORT'] = '6000'
    os.environ['MODBUS_TIMEOUT'] = '5'
    
    config = load_config()
    
    assert config['nport1_host'] == '10.0.0.10', "NPort1 host mismatch"
    assert config['nport1_port'] == 5001, "NPort1 port mismatch"
    assert config['nport2_host'] == '10.0.0.20', "NPort2 host mismatch"
    assert config['nport2_port'] == 5002, "NPort2 port mismatch"
    assert config['listen_host'] == '127.0.0.1', "Listen host mismatch"
    assert config['listen_port'] == 6000, "Listen port mismatch"
    assert config['timeout'] == 5, "Timeout mismatch"
    
    print("✓ Configuration loaded correctly from environment variables")
    print(f"  - All values match expected values")
    print()
    
    # Clean up environment
    for key in ['NPORT1_HOST', 'NPORT1_PORT', 'NPORT2_HOST', 'NPORT2_PORT', 
                'LISTEN_HOST', 'LISTEN_PORT', 'MODBUS_TIMEOUT']:
        if key in os.environ:
            del os.environ[key]
    
    return True


def test_config_defaults():
    """Test that default configuration values are used when env vars are not set."""
    print("=" * 60)
    print("Testing Default Configuration")
    print("=" * 60)
    
    config = load_config()
    
    assert config['nport1_host'] == '192.168.1.100', "Default NPort1 host incorrect"
    assert config['nport1_port'] == 4001, "Default NPort1 port incorrect"
    assert config['nport2_host'] == '192.168.1.101', "Default NPort2 host incorrect"
    assert config['nport2_port'] == 4002, "Default NPort2 port incorrect"
    assert config['listen_host'] == '0.0.0.0', "Default listen host incorrect"
    assert config['listen_port'] == 5020, "Default listen port incorrect"
    assert config['timeout'] == 3, "Default timeout incorrect"
    
    print("✓ Default configuration values are correct")
    print(f"  - All defaults match expected values")
    print()
    
    return True


def test_config_validation():
    """Test that invalid configuration values are handled properly."""
    print("=" * 60)
    print("Testing Configuration Validation")
    print("=" * 60)
    
    # Test invalid port number
    os.environ['NPORT1_PORT'] = 'invalid'
    
    try:
        config = load_config()
        print("✗ Should have raised ValueError for invalid port")
        return False
    except SystemExit:
        print("✓ Invalid configuration properly rejected")
        print("  - ValueError caught and handled correctly")
    finally:
        if 'NPORT1_PORT' in os.environ:
            del os.environ['NPORT1_PORT']
    
    print()
    return True


async def test_lock_mechanism():
    """Test that the locking mechanism works correctly."""
    print("=" * 60)
    print("Testing Bus Lock Mechanism")
    print("=" * 60)
    
    bridge = ModbusBridge(
        nport1_host='192.168.1.100',
        nport1_port=4001,
        nport2_host='192.168.1.101',
        nport2_port=4002
    )
    
    # Test acquiring and releasing the lock
    async with bridge.bus_lock:
        print("✓ Lock acquired successfully")
        # Lock is held here
        
    print("✓ Lock released successfully")
    print("  - Lock mechanism is working correctly")
    print()
    
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Modbus Bridge Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        ("Configuration Defaults", test_config_defaults),
        ("Configuration Loading", test_config_loading),
        ("Configuration Validation", test_config_validation),
        ("Bridge Initialization", test_bridge_initialization),
        ("Lock Mechanism", test_lock_mechanism),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}\n")
    
    print("=" * 60)
    print("Test Results")
    print("=" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All tests passed! The bridge is properly configured.\n")
        print("NOTE: These tests validate the code structure and configuration.")
        print("To test actual Modbus communication, you need:")
        print("  1. Moxa NPort devices connected and configured")
        print("  2. Proper network connectivity to the NPort devices")
        print("  3. A solar inverter connected to NPort 1")
        print("  4. An external system connected to NPort 2 (optional)")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
