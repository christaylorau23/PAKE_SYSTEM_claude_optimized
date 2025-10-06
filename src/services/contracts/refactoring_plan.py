#!/usr/bin/env python3
"""PAKE System - Phased Refactoring Plan (Phase 3 Architectural Health)
Comprehensive plan for decoupling services and implementing formal contracts.

This module provides:
1. Detailed refactoring roadmap with phases
2. Migration strategies for existing code
3. Validation and testing approaches
4. Rollback and monitoring procedures
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RefactoringPhase(Enum):
    """Refactoring phase enumeration."""

    PREPARATION = "preparation"
    INTERFACE_IMPLEMENTATION = "interface_implementation"
    SERVICE_DECOUPLING = "service_decoupling"
    CONTRACT_MIGRATION = "contract_migration"
    VALIDATION = "validation"
    PRODUCTION_DEPLOYMENT = "production_deployment"


class RefactoringStatus(Enum):
    """Refactoring task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ServiceCouplingLevel(Enum):
    """Service coupling assessment levels."""

    TIGHTLY_COUPLED = "tightly_coupled"  # Direct instantiation, shared state
    MODERATELY_COUPLED = "moderately_coupled"  # Interface dependencies
    LOOSELY_COUPLED = "loosely_coupled"  # Event-driven, async
    DECOUPLED = "decoupled"  # Independent services


@dataclass
class ServiceDependency:
    """Service dependency mapping."""

    service_name: str
    dependent_service: str
    dependency_type: str  # "direct_instantiation", "interface", "event", "api"
    coupling_level: ServiceCouplingLevel
    refactoring_priority: int  # 1 = highest priority
    estimated_effort_hours: int
    risk_level: str  # "low", "medium", "high", "critical"


@dataclass
class RefactoringTask:
    """Individual refactoring task."""

    task_id: str
    phase: RefactoringPhase
    service_name: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: RefactoringStatus = RefactoringStatus.PENDING
    assigned_developer: str | None = None
    estimated_hours: int = 0
    actual_hours: int = 0
    start_date: datetime | None = None
    completion_date: datetime | None = None
    validation_criteria: list[str] = field(default_factory=list)
    rollback_plan: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class RefactoringMilestone:
    """Refactoring milestone checkpoint."""

    milestone_id: str
    phase: RefactoringPhase
    name: str
    description: str
    success_criteria: list[str]
    validation_tests: list[str]
    rollback_procedures: list[str]
    estimated_completion_date: datetime
    actual_completion_date: datetime | None = None
    status: RefactoringStatus = RefactoringStatus.PENDING


class PAKERefactoringPlan:
    """Comprehensive refactoring plan for PAKE System service decoupling."""

    def __init__(self) -> None:
        self.service_dependencies: list[ServiceDependency] = []
        self.refactoring_tasks: list[RefactoringTask] = []
        self.milestones: list[RefactoringMilestone] = []
        self._initialize_dependencies()
        self._create_refactoring_phases()
        self._generate_tasks()

    def _initialize_dependencies(self) -> None:
        """Initialize service dependency mapping based on current architecture."""
        self.service_dependencies = [
            # Critical tight coupling issues
            ServiceDependency(
                service_name="AuthenticationService",
                dependent_service="UserService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=1,
                estimated_effort_hours=16,
                risk_level="critical",
            ),
            ServiceDependency(
                service_name="IntelligenceCoreService",
                dependent_service="VectorDatabaseService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=1,
                estimated_effort_hours=20,
                risk_level="critical",
            ),
            ServiceDependency(
                service_name="IntelligenceCoreService",
                dependent_service="IntelligenceNLPService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=1,
                estimated_effort_hours=12,
                risk_level="high",
            ),
            ServiceDependency(
                service_name="IngestionOrchestrator",
                dependent_service="IngestionPlanBuilder",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=2,
                estimated_effort_hours=8,
                risk_level="medium",
            ),
            ServiceDependency(
                service_name="IngestionOrchestrator",
                dependent_service="SourceExecutor",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=2,
                estimated_effort_hours=8,
                risk_level="medium",
            ),
            # TypeScript bridge coupling
            ServiceDependency(
                service_name="TypeScriptBridge",
                dependent_service="PythonBackend",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=1,
                estimated_effort_hours=24,
                risk_level="critical",
            ),
            # Service mesh coupling
            ServiceDependency(
                service_name="ServiceMesh",
                dependent_service="AuthService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=2,
                estimated_effort_hours=12,
                risk_level="medium",
            ),
            ServiceDependency(
                service_name="ServiceMesh",
                dependent_service="DataService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=2,
                estimated_effort_hours=12,
                risk_level="medium",
            ),
            ServiceDependency(
                service_name="ServiceMesh",
                dependent_service="AIService",
                dependency_type="direct_instantiation",
                coupling_level=ServiceCouplingLevel.TIGHTLY_COUPLED,
                refactoring_priority=2,
                estimated_effort_hours=12,
                risk_level="medium",
            ),
        ]

    def _create_refactoring_phases(self) -> None:
        """Create refactoring phases and milestones."""
        self.milestones = [
            RefactoringMilestone(
                milestone_id="phase1_preparation",
                phase=RefactoringPhase.PREPARATION,
                name="Preparation and Assessment",
                description="Complete dependency analysis and prepare refactoring environment",
                success_criteria=[
                    "All service dependencies mapped and prioritized",
                    "Refactoring environment setup complete",
                    "Backup and rollback procedures tested",
                    "Team training on new contract patterns completed",
                ],
                validation_tests=[
                    "Dependency analysis validation",
                    "Environment setup verification",
                    "Rollback procedure testing",
                ],
                rollback_procedures=[
                    "Restore from backup",
                    "Revert environment changes",
                    "Reset team training materials",
                ],
                estimated_completion_date=datetime(2025, 2, 15, tzinfo=UTC),
            ),
            RefactoringMilestone(
                milestone_id="phase2_interfaces",
                phase=RefactoringPhase.INTERFACE_IMPLEMENTATION,
                name="Interface Implementation",
                description="Implement formal service contracts and interfaces",
                success_criteria=[
                    "All service contracts defined and registered",
                    "Interface implementations created for critical services",
                    "Contract validation and testing framework operational",
                    "Service registry updated with new contracts",
                ],
                validation_tests=[
                    "Contract schema validation",
                    "Interface implementation testing",
                    "Service registry integration testing",
                ],
                rollback_procedures=[
                    "Disable new interfaces",
                    "Revert to legacy communication patterns",
                    "Restore original service configurations",
                ],
                estimated_completion_date=datetime(2025, 3, 1, tzinfo=UTC),
            ),
            RefactoringMilestone(
                milestone_id="phase3_decoupling",
                phase=RefactoringPhase.SERVICE_DECOUPLING,
                name="Service Decoupling",
                description="Replace direct instantiations with contract-based communication",
                success_criteria=[
                    "Critical service dependencies refactored",
                    "Direct instantiations eliminated from high-priority services",
                    "Contract-based communication operational",
                    "Service independence validated",
                ],
                validation_tests=[
                    "Service independence testing",
                    "Contract communication validation",
                    "Performance impact assessment",
                    "Error handling verification",
                ],
                rollback_procedures=[
                    "Restore direct instantiations",
                    "Disable contract-based communication",
                    "Revert service configurations",
                ],
                estimated_completion_date=datetime(2025, 3, 15, tzinfo=UTC),
            ),
            RefactoringMilestone(
                milestone_id="phase4_migration",
                phase=RefactoringPhase.CONTRACT_MIGRATION,
                name="Contract Migration",
                description="Migrate remaining services to contract-based architecture",
                success_criteria=[
                    "All services using contract-based communication",
                    "Legacy communication patterns removed",
                    "Service mesh fully operational",
                    "Monitoring and observability enhanced",
                ],
                validation_tests=[
                    "End-to-end contract testing",
                    "Service mesh validation",
                    "Performance benchmarking",
                    "Security validation",
                ],
                rollback_procedures=[
                    "Restore legacy communication",
                    "Disable service mesh",
                    "Revert monitoring changes",
                ],
                estimated_completion_date=datetime(2025, 4, 1, tzinfo=UTC),
            ),
            RefactoringMilestone(
                milestone_id="phase5_validation",
                phase=RefactoringPhase.VALIDATION,
                name="Validation and Testing",
                description="Comprehensive validation of refactored architecture",
                success_criteria=[
                    "All tests passing with new architecture",
                    "Performance benchmarks met or exceeded",
                    "Security validation completed",
                    "Documentation updated",
                ],
                validation_tests=[
                    "Comprehensive test suite execution",
                    "Performance load testing",
                    "Security penetration testing",
                    "Documentation review",
                ],
                rollback_procedures=[
                    "Full system rollback",
                    "Restore original architecture",
                    "Revert all changes",
                ],
                estimated_completion_date=datetime(2025, 4, 15, tzinfo=UTC),
            ),
            RefactoringMilestone(
                milestone_id="phase6_production",
                phase=RefactoringPhase.PRODUCTION_DEPLOYMENT,
                name="Production Deployment",
                description="Deploy refactored architecture to production",
                success_criteria=[
                    "Production deployment successful",
                    "Zero-downtime migration completed",
                    "Performance monitoring operational",
                    "Team trained on new architecture",
                ],
                validation_tests=[
                    "Production deployment validation",
                    "Zero-downtime verification",
                    "Performance monitoring validation",
                    "Team competency assessment",
                ],
                rollback_procedures=[
                    "Production rollback procedures",
                    "Emergency response protocols",
                    "Data integrity verification",
                ],
                estimated_completion_date=datetime(2025, 5, 1, tzinfo=UTC),
            ),
        ]

    def _generate_tasks(self) -> None:
        """Generate detailed refactoring tasks."""
        self.refactoring_tasks = [
            # Phase 1: Preparation
            RefactoringTask(
                task_id="prep_001",
                phase=RefactoringPhase.PREPARATION,
                service_name="System",
                description="Complete comprehensive dependency analysis",
                estimated_hours=8,
                validation_criteria=[
                    "All service dependencies documented",
                    "Coupling levels assessed",
                    "Risk levels assigned",
                ],
            ),
            RefactoringTask(
                task_id="prep_002",
                phase=RefactoringPhase.PREPARATION,
                service_name="System",
                description="Setup refactoring development environment",
                estimated_hours=4,
                validation_criteria=[
                    "Separate refactoring branch created",
                    "Testing environment configured",
                    "Backup procedures tested",
                ],
            ),
            RefactoringTask(
                task_id="prep_003",
                phase=RefactoringPhase.PREPARATION,
                service_name="System",
                description="Train team on contract-based architecture",
                estimated_hours=16,
                validation_criteria=[
                    "Team training completed",
                    "Architecture documentation reviewed",
                    "Contract patterns understood",
                ],
            ),
            # Phase 2: Interface Implementation
            RefactoringTask(
                task_id="int_001",
                phase=RefactoringPhase.INTERFACE_IMPLEMENTATION,
                service_name="AuthenticationService",
                description="Implement AuthenticationServiceContract",
                dependencies=["prep_001", "prep_002"],
                estimated_hours=12,
                validation_criteria=[
                    "Contract schema validated",
                    "Interface implementation tested",
                    "Backward compatibility maintained",
                ],
            ),
            RefactoringTask(
                task_id="int_002",
                phase=RefactoringPhase.INTERFACE_IMPLEMENTATION,
                service_name="DataService",
                description="Implement DataServiceContract",
                dependencies=["prep_001", "prep_002"],
                estimated_hours=16,
                validation_criteria=[
                    "Contract schema validated",
                    "Query operations tested",
                    "Performance benchmarks met",
                ],
            ),
            RefactoringTask(
                task_id="int_003",
                phase=RefactoringPhase.INTERFACE_IMPLEMENTATION,
                service_name="AIService",
                description="Implement AIServiceContract",
                dependencies=["prep_001", "prep_002"],
                estimated_hours=20,
                validation_criteria=[
                    "Contract schema validated",
                    "AI operations tested",
                    "Model integration verified",
                ],
            ),
            RefactoringTask(
                task_id="int_004",
                phase=RefactoringPhase.INTERFACE_IMPLEMENTATION,
                service_name="EventStreamingService",
                description="Implement EventStreamingContract",
                dependencies=["prep_001", "prep_002"],
                estimated_hours=12,
                validation_criteria=[
                    "Event schema validated",
                    "Streaming operations tested",
                    "Message delivery verified",
                ],
            ),
            # Phase 3: Service Decoupling
            RefactoringTask(
                task_id="dec_001",
                phase=RefactoringPhase.SERVICE_DECOUPLING,
                service_name="AuthenticationService",
                description="Refactor AuthenticationService to use contracts",
                dependencies=["int_001"],
                estimated_hours=16,
                validation_criteria=[
                    "Direct instantiations removed",
                    "Contract-based communication operational",
                    "Authentication flow tested",
                ],
            ),
            RefactoringTask(
                task_id="dec_002",
                phase=RefactoringPhase.SERVICE_DECOUPLING,
                service_name="IntelligenceCoreService",
                description="Refactor IntelligenceCoreService dependencies",
                dependencies=["int_002", "int_003"],
                estimated_hours=20,
                validation_criteria=[
                    "Vector database coupling removed",
                    "NLP service coupling removed",
                    "Intelligence operations tested",
                ],
            ),
            RefactoringTask(
                task_id="dec_003",
                phase=RefactoringPhase.SERVICE_DECOUPLING,
                service_name="IngestionOrchestrator",
                description="Refactor IngestionOrchestrator dependencies",
                dependencies=["int_002"],
                estimated_hours=8,
                validation_criteria=[
                    "Plan builder coupling removed",
                    "Source executor coupling removed",
                    "Ingestion flow tested",
                ],
            ),
            RefactoringTask(
                task_id="dec_004",
                phase=RefactoringPhase.SERVICE_DECOUPLING,
                service_name="TypeScriptBridge",
                description="Refactor TypeScript bridge coupling",
                dependencies=["int_001", "int_002", "int_003"],
                estimated_hours=24,
                validation_criteria=[
                    "Python backend coupling removed",
                    "API-based communication operational",
                    "Frontend-backend integration tested",
                ],
            ),
            # Phase 4: Contract Migration
            RefactoringTask(
                task_id="mig_001",
                phase=RefactoringPhase.CONTRACT_MIGRATION,
                service_name="ServiceMesh",
                description="Migrate ServiceMesh to contract-based architecture",
                dependencies=["dec_001", "dec_002", "dec_003"],
                estimated_hours=12,
                validation_criteria=[
                    "Service mesh contracts implemented",
                    "Service discovery operational",
                    "Load balancing tested",
                ],
            ),
            RefactoringTask(
                task_id="mig_002",
                phase=RefactoringPhase.CONTRACT_MIGRATION,
                service_name="AllServices",
                description="Migrate remaining services to contracts",
                dependencies=["mig_001"],
                estimated_hours=32,
                validation_criteria=[
                    "All services using contracts",
                    "Legacy patterns removed",
                    "System integration tested",
                ],
            ),
            # Phase 5: Validation
            RefactoringTask(
                task_id="val_001",
                phase=RefactoringPhase.VALIDATION,
                service_name="System",
                description="Execute comprehensive test suite",
                dependencies=["mig_002"],
                estimated_hours=16,
                validation_criteria=[
                    "All unit tests passing",
                    "Integration tests passing",
                    "End-to-end tests passing",
                ],
            ),
            RefactoringTask(
                task_id="val_002",
                phase=RefactoringPhase.VALIDATION,
                service_name="System",
                description="Performance and security validation",
                dependencies=["val_001"],
                estimated_hours=12,
                validation_criteria=[
                    "Performance benchmarks met",
                    "Security vulnerabilities addressed",
                    "Load testing completed",
                ],
            ),
            # Phase 6: Production Deployment
            RefactoringTask(
                task_id="prod_001",
                phase=RefactoringPhase.PRODUCTION_DEPLOYMENT,
                service_name="System",
                description="Deploy to staging environment",
                dependencies=["val_002"],
                estimated_hours=8,
                validation_criteria=[
                    "Staging deployment successful",
                    "Staging tests passing",
                    "Performance monitoring operational",
                ],
            ),
            RefactoringTask(
                task_id="prod_002",
                phase=RefactoringPhase.PRODUCTION_DEPLOYMENT,
                service_name="System",
                description="Deploy to production with zero downtime",
                dependencies=["prod_001"],
                estimated_hours=12,
                validation_criteria=[
                    "Production deployment successful",
                    "Zero downtime achieved",
                    "Production monitoring operational",
                ],
            ),
        ]

    def get_critical_path(self) -> list[RefactoringTask]:
        """Get critical path tasks for refactoring."""
        critical_tasks = []

        # Find tasks with highest priority and dependencies
        for task in self.refactoring_tasks:
            if task.phase in [
                RefactoringPhase.INTERFACE_IMPLEMENTATION,
                RefactoringPhase.SERVICE_DECOUPLING,
            ] and task.service_name in [
                "AuthenticationService",
                "IntelligenceCoreService",
                "TypeScriptBridge",
            ]:
                critical_tasks.append(task)

        return sorted(critical_tasks, key=lambda t: t.estimated_hours, reverse=True)

    def get_risk_assessment(self) -> dict[str, list[ServiceDependency]]:
        """Get risk assessment by level."""
        risk_levels = {"critical": [], "high": [], "medium": [], "low": []}

        for dep in self.service_dependencies:
            risk_levels[dep.risk_level].append(dep)

        return risk_levels

    def estimate_total_effort(self) -> dict[str, int]:
        """Estimate total effort by phase."""
        effort_by_phase = {}

        for phase in RefactoringPhase:
            phase_tasks = [t for t in self.refactoring_tasks if t.phase == phase]
            total_hours = sum(task.estimated_hours for task in phase_tasks)
            effort_by_phase[phase.value] = total_hours

        return effort_by_phase

    def generate_implementation_guide(self) -> str:
        """Generate implementation guide for developers."""
        return """
# PAKE System Refactoring Implementation Guide

## Overview
This guide provides step-by-step instructions for implementing the service decoupling refactoring.

## Phase 1: Preparation (Week 1-2)

### 1.1 Dependency Analysis
```bash
# Run dependency analysis script
python scripts/analyze_service_dependencies.py

# Review generated dependency report
cat reports/service_dependencies.json
```

### 1.2 Environment Setup
```bash
# Create refactoring branch
git checkout -b feature/service-decoupling-refactor

# Setup testing environment
python scripts/setup_refactoring_env.py

# Test backup procedures
python scripts/test_backup_procedures.py
```

## Phase 2: Interface Implementation (Week 3-4)

### 2.1 Contract Implementation
```python
# Example: Implementing AuthenticationServiceContract
from src.services.contracts.service_contracts import AuthenticationServiceContract

class ConcreteAuthenticationService(AuthenticationServiceContract):
    async def execute(self, request: ContractRequest[AuthenticationRequest]) -> ContractResponse[AuthenticationResponse]:
        # Implementation here
```

### 2.2 Contract Registration
```python
# Register contracts in service registry
from src.services.contracts.service_contracts import contract_registry

contract_registry.register_contract(ConcreteAuthenticationService())
```

## Phase 3: Service Decoupling (Week 5-6)

### 3.1 Replace Direct Instantiations
```python
# Before (tightly coupled)
class UserService:
    def __init__(self) -> None:
        self.auth_service = AuthenticationService()  # Direct instantiation

# After (loosely coupled)
class UserService:
    def __init__(self) -> None:
        self.auth_contract = auth_contract  # Contract-based
```

### 3.2 Update Service Factory
```python
# Update DI container to use contracts
def configure_services(container: DIContainer) -> DIContainer:
    # Register contracts instead of concrete implementations
    container.register_transient(AuthenticationServiceContract, ConcreteAuthenticationService)
    return container
```

## Phase 4: Contract Migration (Week 7-8)

### 4.1 Service Mesh Integration
```python
# Update service mesh to use contracts
class ServiceMesh:
    def __init__(self) -> None:
        self.contract_registry = contract_registry

    async def route_request(self) -> None:
        contract = self.contract_registry.get_contract(service_name)
        return await contract.execute(request)
```

## Phase 5: Validation (Week 9)

### 5.1 Test Execution
```bash
# Run comprehensive test suite
python -m pytest tests/ -v --cov=src/services

# Run integration tests
python -m pytest tests/integration/ -v

# Run performance tests
python scripts/run_performance_tests.py
```

### 5.2 Security Validation
```bash
# Run security tests
python scripts/run_security_tests.py

# Run DAST scans
python scripts/run_dast_scans.py
```

## Phase 6: Production Deployment (Week 10)

### 6.1 Staging Deployment
```bash
# Deploy to staging
python scripts/deploy_to_staging.py

# Validate staging deployment
python scripts/validate_staging_deployment.py
```

### 6.2 Production Deployment
```bash
# Deploy to production with zero downtime
python scripts/deploy_to_production.py --zero-downtime

# Monitor production deployment
python scripts/monitor_production_deployment.py
```

## Validation Checklist

### Contract Implementation
- [ ] All service contracts defined and registered
- [ ] Contract schemas validated
- [ ] Interface implementations tested
- [ ] Backward compatibility maintained

### Service Decoupling
- [ ] Direct instantiations removed
- [ ] Contract-based communication operational
- [ ] Service independence validated
- [ ] Performance impact assessed

### System Integration
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Security validation completed
- [ ] Documentation updated

## Rollback Procedures

### Emergency Rollback
```bash
# Execute emergency rollback
python scripts/emergency_rollback.py

# Restore from backup
python scripts/restore_from_backup.py

# Validate rollback
python scripts/validate_rollback.py
```

## Monitoring and Observability

### Contract Metrics
- Request/response times
- Success/failure rates
- Contract version usage
- Service dependency health

### Performance Monitoring
- Service response times
- Resource utilization
- Error rates
- Throughput metrics

## Best Practices

1. **Incremental Refactoring**: Refactor one service at a time
2. **Comprehensive Testing**: Test each change thoroughly
3. **Monitoring**: Monitor system health continuously
4. **Documentation**: Update documentation with each change
5. **Team Communication**: Keep team informed of progress

## Troubleshooting

### Common Issues
1. **Contract Validation Failures**: Check schema definitions
2. **Service Discovery Issues**: Verify service registry
3. **Performance Degradation**: Monitor resource usage
4. **Integration Failures**: Check contract implementations

### Debug Commands
```bash
# Debug contract registry
python scripts/debug_contract_registry.py

# Debug service dependencies
python scripts/debug_service_dependencies.py

# Debug performance issues
python scripts/debug_performance.py
```
"""


# Create global refactoring plan instance
refactoring_plan = PAKERefactoringPlan()


def get_refactoring_plan() -> PAKERefactoringPlan:
    """Get the global refactoring plan instance."""
    return refactoring_plan


def print_refactoring_summary() -> None:
    """Print refactoring plan summary."""
    plan = get_refactoring_plan()

    print("=== PAKE System Refactoring Plan Summary ===")
    print(f"Total Dependencies: {len(plan.service_dependencies)}")
    print(f"Total Tasks: {len(plan.refactoring_tasks)}")
    print(f"Total Milestones: {len(plan.milestones)}")

    print("\n=== Effort Estimation by Phase ===")
    effort_by_phase = plan.estimate_total_effort()
    for phase, hours in effort_by_phase.items():
        print(f"{phase}: {hours} hours")

    print("\n=== Risk Assessment ===")
    risk_assessment = plan.get_risk_assessment()
    for risk_level, dependencies in risk_assessment.items():
        print(f"{risk_level.upper()}: {len(dependencies)} dependencies")

    print("\n=== Critical Path Tasks ===")
    critical_tasks = plan.get_critical_path()
    for task in critical_tasks:
        print(f"- {task.service_name}: {task.description} ({task.estimated_hours}h)")


if __name__ == "__main__":
    print_refactoring_summary()
