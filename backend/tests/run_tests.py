"""
Test runner script for API testing.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔧 {description}...")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run API tests for Insight-Flow")
    parser.add_argument("--type", choices=["unit", "integration", "all"], default="all",
                       help="Type of tests to run")
    parser.add_argument("--module", choices=["auth", "users", "projects", "tasks", "analytics", "notifications"],
                       help="Specific module to test")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-n", type=int, default=1, help="Number of parallel processes")
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    print("🚀 Starting API Test Runner")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Install test dependencies if needed
    if not run_command("pip install pytest pytest-cov pytest-asyncio pytest-mock", 
                    "Installing test dependencies"):
        sys.exit(1)
    
    # Build test command
    test_command = "pytest"
    
    # Add test type
    if args.type == "unit":
        test_command += " -m 'not integration'"
    elif args.type == "integration":
        test_command += " -m integration"
    
    # Add specific module
    if args.module:
        test_command += f" tests/test_{args.module}.py"
    else:
        test_command += " tests/"
    
    # Add options
    if args.coverage:
        test_command += " --cov=. --cov-report=html --cov-report=term-missing"
    
    if args.verbose:
        test_command += " -v"
    
    if args.parallel > 1:
        test_command += f" -n {args.parallel}"
    
    # Add pytest configuration
    test_command += " -c tests/pytest.ini"
    
    # Run tests
    success = run_command(test_command, f"Running {args.type} tests")
    
    if success:
        print("\n🎉 All tests completed successfully!")
        
        # Show coverage report if generated
        if args.coverage and Path("htmlcov/index.html").exists():
            print("\n📊 Coverage report generated: htmlcov/index.html")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

def run_specific_tests():
    """Run specific test scenarios."""
    print("\n🧪 Running specific test scenarios...")
    
    # Test 1: Basic API connectivity
    print("\n1️⃣ Testing basic API connectivity...")
    if run_command("curl -f http://localhost:8000/ || echo 'API not running'", 
                 "API connectivity check"):
        print("✅ API is running")
    else:
        print("❌ API is not running. Please start the API server first.")
        return False
    
    # Test 2: Authentication flow
    print("\n2️⃣ Testing authentication flow...")
    auth_command = "python -c \"import httpx; r=httpx.post('http://localhost:8000/auth/login', json={'email': 'test@example.com', 'password': 'test'}); print('✅ Auth endpoint accessible' if r.status_code in [200, 401] else '❌ Auth endpoint error')\""
    run_command(auth_command, "Authentication flow test")
    
    # Test 3: Database connectivity
    print("\n3️⃣ Testing database connectivity...")
    db_command = "python -c \"from database import engine; print('✅ Database connected' if engine else '❌ Database connection failed')\""
    run_command(db_command, "Database connectivity test")
    
    return True

def run_performance_tests():
    """Run performance-related tests."""
    print("\n⚡ Running performance tests...")
    
    # Test with multiple concurrent requests
    perf_command = "python -c \"import concurrent.futures, httpx, time; start=time.time(); with concurrent.futures.ThreadPoolExecutor(10) as e: list(e.submit(lambda: httpx.get('http://localhost:8000/').status_code, _) for _ in range(10)); print(f'✅ Performance test completed in {time.time()-start:.2f}s')\""
    run_command(perf_command, "Performance test")

def check_environment():
    """Check if testing environment is properly set up."""
    print("\n🔍 Checking testing environment...")
    
    checks = [
        ("Python version", "python --version"),
        ("Pip version", "pip --version"),
        ("Test dependencies", "pip list | grep pytest"),
        ("Environment variables", "echo $TEST_ENV || echo 'TEST_ENV not set'"),
    ]
    
    for check_name, command in checks:
        run_command(command, f"Checking {check_name}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments, run interactive mode
        print("🎯 Interactive Test Runner")
        print("Choose an option:")
        print("1. Run all tests")
        print("2. Run unit tests only")
        print("3. Run integration tests only")
        print("4. Run specific module tests")
        print("5. Run specific test scenarios")
        print("6. Run performance tests")
        print("7. Check environment")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == "1":
            main()
        elif choice == "2":
            sys.argv.extend(["--type", "unit"])
            main()
        elif choice == "3":
            sys.argv.extend(["--type", "integration"])
            main()
        elif choice == "4":
            modules = ["auth", "users", "projects", "tasks", "analytics", "notifications"]
            print(f"Available modules: {', '.join(modules)}")
            module = input("Enter module name: ").strip()
            if module in modules:
                sys.argv.extend(["--module", module])
                main()
            else:
                print("❌ Invalid module")
        elif choice == "5":
            run_specific_tests()
        elif choice == "6":
            run_performance_tests()
        elif choice == "7":
            check_environment()
        elif choice == "8":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")
    else:
        main()