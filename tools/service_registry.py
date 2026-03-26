"""
tools/service_registry.py
─────────────────────────
Dynamic service registry that loads from services_matrix.yaml
Provides a single source of truth for all microservices configuration
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


class Service:
    """Represents a single microservice"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.enabled = config.get('enabled', True)
        self.port = config.get('port')
        self.db = config.get('db', {})
        self.java_package = config.get('java_package')
        self.test_runner_class = config.get('test_runner_class')
        self.pom_location = config.get('pom_location', 'output/tests')
        self.dependencies = config.get('dependencies', [])
        self.swagger_spec = config.get('swagger_spec')
        self.swagger_url = config.get('swagger_url')
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def get_base_url(self) -> str:
        """Get service base URL"""
        return f"http://127.0.0.1:{self.port}"
    
    def __repr__(self):
        return f"Service({self.name}, port={self.port}, enabled={self.enabled})"


class ServiceRegistry:
    """Manages all microservices configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "services_matrix.yaml"
        
        self.config_path = config_path
        self.services: Dict[str, Service] = {}
        self.global_config: Dict = {}
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"services_matrix.yaml not found at {self.config_path}")
        
        self._load_matrix()
        logger.info(f"✅ ServiceRegistry loaded with {len(self.get_enabled_services())} enabled services")
    
    def _load_matrix(self) -> None:
        """Load services from YAML matrix"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.global_config = config.get('global', {})
            
            # Load all services
            for service_name, service_config in config.get('services', {}).items():
                self.services[service_name] = Service(service_name, service_config)
            
            logger.info(f"📋 Loaded {len(self.services)} total services from matrix")
        except Exception as e:
            logger.error(f"❌ Failed to load services_matrix.yaml: {e}")
            raise
    
    def get_service(self, name: str) -> Optional[Service]:
        """Get a specific service by name"""
        return self.services.get(name)
    
    def get_all_services(self) -> List[Service]:
        """Get all services (enabled and disabled)"""
        return list(self.services.values())
    
    def get_enabled_services(self) -> List[Service]:
        """Get only enabled services"""
        return [s for s in self.services.values() if s.is_enabled()]
    
    def get_service_names(self, enabled_only: bool = True) -> List[str]:
        """Get list of service names"""
        services = self.get_enabled_services() if enabled_only else self.get_all_services()
        return [s.name for s in services]
    
    def get_execution_order(self, services_to_consider: Optional[List[str]] = None) -> List[str]:
        """
        Get services in dependency order (respecting dependencies)
        Services with no dependencies come first
        """
        if services_to_consider:
            enabled_services = [s for s in self.get_all_services() if s.name in services_to_consider]
        else:
            enabled_services = self.get_enabled_services()

        remaining = {s.name for s in enabled_services}
        order = []
        
        while remaining:
            # Find services with no remaining dependencies
            ready = [
                name for name in remaining
                if all(dep not in remaining for dep in self.services[name].dependencies)
            ]
            
            if not ready:
                # If nothing is ready, there must be a circular dependency
                # or a dependency on a service that wasn't requested.
                all_deps = {name: self.services[name].dependencies for name in remaining}
                logger.warning(f"⚠️ Circular dependency or missing dependency detected in: {all_deps}")
                # To prevent an infinite loop, just add the rest alphabetically and break
                order.extend(sorted(list(remaining)))
                break
            
            order.extend(sorted(ready))  # Sort for deterministic order
            remaining -= set(ready)
        
        logger.info(f"📊 Execution order: {' → '.join(order)}")
        return order
    
    def get_service_config(self, service_name: str) -> Dict:
        """Get full configuration for a service"""
        service = self.get_service(service_name)
        if not service:
            raise ValueError(f"Service '{service_name}' not found")
        
        return {
            'name': service.name,
            'port': service.port,
            'base_url': service.get_base_url(),
            'db': service.db,
            'java_package': service.java_package,
            'test_runner_class': service.test_runner_class,
            'pom_location': service.pom_location,
            'dependencies': service.dependencies,
            'enabled': service.enabled,
        }
    
    def can_run_parallel(self, service_a: str, service_b: str) -> bool:
        """Check if two services can run tests in parallel"""
        svc_a = self.get_service(service_a)
        svc_b = self.get_service(service_b)
        
        if not svc_a or not svc_b:
            return False
        
        # Services can run in parallel if neither depends on the other
        return (
            service_b not in svc_a.dependencies and
            service_a not in svc_b.dependencies
        )
    
    def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get all services this service depends on"""
        service = self.get_service(service_name)
        return service.dependencies if service else []
    
    def get_service_dependents(self, service_name: str) -> List[str]:
        """Get all services that depend on this service"""
        dependents = []
        for service in self.get_enabled_services():
            if service_name in service.dependencies:
                dependents.append(service.name)
        return dependents
    
    def get_impact_scope(self, changed_service: str) -> List[str]:
        """
        Get all services that need retesting if changed_service was modified
        Includes the service itself + all services that depend on it
        """
        impact = [changed_service]
        to_check = [changed_service]
        
        while to_check:
            current = to_check.pop()
            dependents = self.get_service_dependents(current)
            for dep in dependents:
                if dep not in impact:
                    impact.append(dep)
                    to_check.append(dep)
        
        return impact
    
    def validate_configuration(self) -> bool:
        """Validate the configuration is valid"""
        enabled = self.get_enabled_services()
        
        if not enabled:
            logger.warning("⚠️ No services enabled in configuration")
            return False
        
        # Check for duplicate ports
        ports = {}
        for service in enabled:
            if service.port in ports:
                logger.error(
                    f"❌ Port conflict: {service.name} and {ports[service.port]} "
                    f"both use port {service.port}"
                )
                return False
            ports[service.port] = service.name
        
        # Check for missing dependencies
        service_names = {s.name for s in enabled}
        for service in enabled:
            for dep in service.dependencies:
                if dep not in service_names:
                    logger.error(
                        f"❌ Service '{service.name}' depends on '{dep}' "
                        f"which is not configured or enabled"
                    )
                    return False
        
        logger.info("✅ Configuration validation passed")
        return True
    
    def print_summary(self) -> None:
        """Print a summary of the services configuration"""
        logger.info("\n" + "="*80)
        logger.info("📋 SERVICE REGISTRY SUMMARY")
        logger.info("="*80)
        
        enabled = self.get_enabled_services()
        logger.info(f"\n✅ Enabled Services: {len(enabled)}")
        for service in enabled:
            logger.info(f"  • {service.name:20} port={service.port:5} "
                       f"db={service.db.get('type', 'N/A'):8} "
                       f"deps={service.dependencies if service.dependencies else 'none'}")
        
        disabled = [s for s in self.get_all_services() if not s.is_enabled()]
        if disabled:
            logger.info(f"\n⏸️  Disabled Services: {len(disabled)}")
            for service in disabled:
                logger.info(f"  • {service.name:20} (set enabled=true to use)")
        
        logger.info("\n" + "="*80 + "\n")


# Global registry instance
_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get or create the global service registry"""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry
