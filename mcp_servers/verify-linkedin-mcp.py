"""
LinkedIn MCP Server Verification Script

Tests if the LinkedIn MCP server is properly installed and can connect.
"""

import subprocess
import sys
import json
import os
from pathlib import Path


def check_node():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
            return True
        else:
            print("❌ Node.js not found")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False


def check_npm():
    """Check if npm is installed."""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm: {result.stdout.strip()}")
            return True
        else:
            print("❌ npm not found")
            return False
    except FileNotFoundError:
        print("❌ npm not found")
        return False


def check_dependencies():
    """Check if npm dependencies are installed."""
    mcp_path = Path(__file__).parent / 'linkedin-mcp'
    node_modules = mcp_path / 'node_modules'
    
    if node_modules.exists():
        print(f"✅ Dependencies installed: {node_modules}")
        return True
    else:
        print(f"❌ Dependencies not found: {node_modules}")
        print("   Run: npm install")
        return False


def install_dependencies():
    """Install npm dependencies."""
    mcp_path = Path(__file__).parent / 'linkedin-mcp'
    print(f"Installing dependencies in {mcp_path}...")
    
    try:
        result = subprocess.run(
            ['npm', 'install'],
            cwd=str(mcp_path),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False


def test_server_startup():
    """Test if the server can start (briefly)."""
    mcp_path = Path(__file__).parent / 'linkedin-mcp'
    
    print("Testing server startup (3 second test)...")
    
    try:
        # Start server briefly
        proc = subprocess.Popen(
            ['node', 'index.js'],
            cwd=str(mcp_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, 'HEADLESS': 'true'}
        )
        
        # Wait 3 seconds
        import time
        time.sleep(3)
        
        # Check if still running
        if proc.poll() is None:
            print("✅ Server started successfully")
            proc.terminate()
            proc.wait(timeout=5)
            return True
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Server crashed: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("LinkedIn MCP Server - Verification")
    print("=" * 60)
    print()
    
    checks = [
        ("Node.js", check_node),
        ("npm", check_npm),
        ("Dependencies", check_dependencies),
    ]
    
    results = []
    for name, check in checks:
        print(f"Checking {name}...")
        result = check()
        results.append((name, result))
        print()
    
    # Summary
    print("=" * 60)
    print("Summary:")
    all_passed = all(r[1] for r in results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print()
    
    if all_passed:
        print("✅ All checks passed!")
        print()
        print("To start the LinkedIn MCP server:")
        print("  cd mcp_servers/linkedin-mcp")
        print("  node index.js")
        print()
        print("Or use the batch file:")
        print("  mcp_servers\\linkedin-mcp\\start-server.bat")
    else:
        print("❌ Some checks failed!")
        print()
        print("To fix:")
        if not check_node() or not check_npm():
            print("  1. Install Node.js from https://nodejs.org/")
        if not check_dependencies():
            print("  2. Run: cd mcp_servers/linkedin-mcp && npm install")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
