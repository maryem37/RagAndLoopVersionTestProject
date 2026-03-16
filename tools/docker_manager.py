"""
Docker Manager Tool
Manages Docker Compose services for test execution
"""

import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from config.settings import get_settings


class DockerManager:
    """
    Manages Docker Compose lifecycle for backend services
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.compose_file = self.settings.paths.backend_dir / "docker-compose.test.yml"
        
        if not self.compose_file.exists():
            logger.error(f"❌ docker-compose.test.yml not found at {self.compose_file}")
            raise FileNotFoundError(f"Missing docker-compose.test.yml")
        
        logger.info(f"📋 Docker Compose file: {self.compose_file}")
    
    def check_docker_available(self) -> bool:
        """Check if Docker and Docker Compose are available"""
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error("❌ Docker is not installed or not running")
                return False
            
            logger.info(f"✅ Docker: {result.stdout.strip()}")
            
            # Check Docker Compose
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.error("❌ Docker Compose is not installed")
                return False
            
            logger.info(f"✅ Docker Compose: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Docker check failed: {e}")
            return False
    
    def start_services(self) -> bool:
        """Start backend services using Docker Compose"""
        logger.info("🚀 Starting backend services with Docker Compose...")
        
        try:
            # Pull images first
            logger.info("📥 Pulling Docker images...")
            pull_result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "pull"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.compose_file.parent)
            )
            
            if pull_result.returncode != 0:
                logger.warning(f"⚠️ Image pull warning: {pull_result.stderr}")
            
            # Start services
            logger.info("🔨 Building and starting services...")
            start_result = subprocess.run(
                [
                    "docker-compose", "-f", str(self.compose_file),
                    "up", "-d", "--build",
                    "auth-db", "leave-db", "auth-service", "leave-service"
                ],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.compose_file.parent)
            )
            
            if start_result.returncode != 0:
                logger.error(f"❌ Failed to start services: {start_result.stderr}")
                return False
            
            logger.success("✅ Services started successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Service startup timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to start services: {e}")
            return False
    
    def wait_for_services_healthy(self, timeout: int = 120) -> bool:
        """Wait for all services to become healthy"""
        logger.info(f"⏳ Waiting for services to be healthy (timeout: {timeout}s)...")
        
        services = ["auth-db", "leave-db", "auth-service", "leave-service"]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check service health
                result = subprocess.run(
                    ["docker-compose", "-f", str(self.compose_file), "ps", "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.compose_file.parent)
                )
                
                if result.returncode == 0:
                    # Parse JSON output
                    lines = result.stdout.strip().split('\n')
                    healthy_count = 0
                    
                    for line in lines:
                        if line.strip():
                            try:
                                service_info = json.loads(line)
                                service_name = service_info.get('Service', '')
                                health = service_info.get('Health', '').lower()
                                state = service_info.get('State', '').lower()
                                
                                if service_name in services:
                                    if health == 'healthy' or (state == 'running' and service_name.endswith('-db')):
                                        healthy_count += 1
                                        logger.debug(f"   ✓ {service_name}: healthy")
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"   Healthy services: {healthy_count}/{len(services)}")
                    
                    if healthy_count == len(services):
                        logger.success("✅ All services are healthy!")
                        return True
                
                time.sleep(5)
                
            except Exception as e:
                logger.warning(f"⚠️ Health check error: {e}")
                time.sleep(5)
        
        logger.error(f"❌ Services did not become healthy within {timeout}s")
        
        # Show logs for debugging
        self.show_service_logs()
        
        return False
    
    def run_tests(self, test_dir: Path) -> Dict:
        """Run tests in Docker container"""
        logger.info("🧪 Executing tests in Docker...")
        
        try:
            # Run test-runner service
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "run", "--rm", "test-runner"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.compose_file.parent)
            )
            
            output = result.stdout + result.stderr
            
            # Parse test results
            return self._parse_test_results(output, result.returncode)
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Test execution timed out")
            return {
                "success": False,
                "exit_code": -1,
                "failures": "Test execution timed out after 5 minutes"
            }
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "failures": str(e)
            }
    
    def get_test_reports(self) -> List[Path]:
        """Retrieve test reports from Docker volume"""
        reports = []
        
        reports_dir = self.settings.paths.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Reports are copied by test-runner to /tests/reports
        # which is mounted to ../test-automation-langgraph/output/tests/reports
        
        if reports_dir.exists():
            for report_file in reports_dir.rglob("*.html"):
                reports.append(report_file)
                logger.info(f"📊 Report: {report_file}")
        
        return reports
    
    def cleanup(self):
        """Stop and remove all Docker containers"""
        logger.info("🧹 Stopping and removing Docker services...")
        
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
                capture_output=True,
                timeout=60,
                cwd=str(self.compose_file.parent)
            )
            logger.success("✅ Docker cleanup complete")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def _parse_test_results(self, output: str, exit_code: int) -> Dict:
        """Parse Maven test output"""
        results = {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "tests_run": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "failures": []
        }
        
        # Parse Maven output
        import re
        
        # Look for "Tests run: X, Failures: Y, Errors: Z, Skipped: W"
        pattern = r'Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)'
        match = re.search(pattern, output)
        
        if match:
            results["tests_run"] = int(match.group(1))
            failures = int(match.group(2))
            errors = int(match.group(3))
            results["tests_failed"] = failures + errors
            results["tests_skipped"] = int(match.group(4))
        
        # Extract failure messages
        failure_pattern = r'<<< FAILURE!.*?(?=\n\n|\Z)'
        failures = re.findall(failure_pattern, output, re.DOTALL)
        results["failures"] = failures[:5]  # Limit to 5
        
        return results
    
    def show_service_logs(self):
        """Show logs for debugging"""
        logger.info("📋 Showing service logs for debugging...")
        
        services = ["auth-service", "leave-service"]
        
        for service in services:
            try:
                result = subprocess.run(
                    ["docker-compose", "-f", str(self.compose_file), "logs", "--tail=50", service],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.compose_file.parent)
                )
                
                logger.info(f"\n{'='*60}\n{service} logs:\n{'='*60}")
                logger.info(result.stdout[-1000:])  # Last 1000 chars
                
            except Exception as e:
                logger.warning(f"⚠️ Could not get logs for {service}: {e}")