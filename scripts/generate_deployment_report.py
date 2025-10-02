#!/usr/bin/env python3
"""
PAKE System - Deployment Report Generator
Generate comprehensive deployment reports for CI/CD pipeline
"""

import json
import sys
import argparse
import time
from datetime import datetime
from typing import Dict, Any


class DeploymentReportGenerator:
    """Generate comprehensive deployment reports"""
    
    def __init__(self):
        self.report = {
            "deployment_info": {},
            "quality_gates": {},
            "performance_metrics": {},
            "security_status": {},
            "recommendations": [],
            "generated_at": datetime.now().isoformat()
        }
    
    def add_deployment_info(self, image_tag: str, environment: str, deployed_by: str, deployment_time: str):
        """Add deployment information"""
        self.report["deployment_info"] = {
            "image_tag": image_tag,
            "environment": environment,
            "deployed_by": deployed_by,
            "deployment_time": deployment_time,
            "deployment_id": f"{environment}-{image_tag[:8]}-{int(time.time())}"
        }
    
    def add_quality_gates(self, ci_results: Dict[str, Any]):
        """Add CI quality gate results"""
        self.report["quality_gates"] = {
            "lint_and_format": ci_results.get("lint_and_format", {}),
            "static_analysis": ci_results.get("static_analysis", {}),
            "security_scan": ci_results.get("security_scan", {}),
            "unit_tests": ci_results.get("unit_tests", {}),
            "integration_tests": ci_results.get("integration_tests", {}),
            "e2e_tests": ci_results.get("e2e_tests", {}),
            "test_coverage": ci_results.get("test_coverage", {}),
            "overall_status": "passed" if all(
                gate.get("status") == "passed" for gate in ci_results.values()
            ) else "failed"
        }
    
    def add_performance_metrics(self, performance_data: Dict[str, Any]):
        """Add performance metrics"""
        self.report["performance_metrics"] = {
            "response_times": performance_data.get("response_times", {}),
            "throughput": performance_data.get("throughput", {}),
            "resource_usage": performance_data.get("resource_usage", {}),
            "database_performance": performance_data.get("database_performance", {}),
            "overall_performance_score": self._calculate_performance_score(performance_data)
        }
    
    def add_security_status(self, security_data: Dict[str, Any]):
        """Add security status"""
        self.report["security_status"] = {
            "vulnerability_scan": security_data.get("vulnerability_scan", {}),
            "security_tests": security_data.get("security_tests", {}),
            "compliance_check": security_data.get("compliance_check", {}),
            "overall_security_score": self._calculate_security_score(security_data)
        }
    
    def _calculate_performance_score(self, performance_data: Dict[str, Any]) -> int:
        """Calculate overall performance score (0-100)"""
        # Simplified scoring logic
        score = 100
        
        # Deduct points for slow response times
        response_times = performance_data.get("response_times", {})
        avg_response_time = response_times.get("avg_response_time_ms", 0)
        if avg_response_time > 1000:
            score -= 20
        elif avg_response_time > 500:
            score -= 10
        
        # Deduct points for low throughput
        throughput = performance_data.get("throughput", {})
        req_per_sec = throughput.get("throughput_req_per_sec", 0)
        if req_per_sec < 10:
            score -= 15
        elif req_per_sec < 20:
            score -= 5
        
        return max(0, score)
    
    def _calculate_security_score(self, security_data: Dict[str, Any]) -> int:
        """Calculate overall security score (0-100)"""
        # Simplified scoring logic
        score = 100
        
        # Deduct points for critical vulnerabilities
        vuln_scan = security_data.get("vulnerability_scan", {})
        critical_vulns = vuln_scan.get("critical_vulnerabilities", 0)
        score -= critical_vulns * 20
        
        # Deduct points for failed security tests
        security_tests = security_data.get("security_tests", {})
        failed_tests = security_tests.get("failed_tests", 0)
        score -= failed_tests * 10
        
        return max(0, score)
    
    def generate_recommendations(self):
        """Generate recommendations based on the deployment data"""
        recommendations = []
        
        # Quality gate recommendations
        quality_gates = self.report.get("quality_gates", {})
        if quality_gates.get("overall_status") == "failed":
            recommendations.append({
                "category": "Quality",
                "priority": "High",
                "recommendation": "Address failed quality gates before next deployment",
                "action": "Review CI/CD pipeline failures and fix issues"
            })
        
        # Performance recommendations
        performance_score = self.report.get("performance_metrics", {}).get("overall_performance_score", 100)
        if performance_score < 80:
            recommendations.append({
                "category": "Performance",
                "priority": "Medium",
                "recommendation": "Optimize application performance",
                "action": "Review slow endpoints and optimize database queries"
            })
        
        # Security recommendations
        security_score = self.report.get("security_status", {}).get("overall_security_score", 100)
        if security_score < 90:
            recommendations.append({
                "category": "Security",
                "priority": "High",
                "recommendation": "Address security vulnerabilities",
                "action": "Update dependencies and fix security issues"
            })
        
        self.report["recommendations"] = recommendations
    
    def generate_summary(self) -> str:
        """Generate a human-readable summary"""
        deployment_info = self.report["deployment_info"]
        quality_gates = self.report["quality_gates"]
        performance_score = self.report["performance_metrics"].get("overall_performance_score", 0)
        security_score = self.report["security_status"].get("overall_security_score", 0)
        
        summary = f"""
# PAKE System Deployment Report

## Deployment Information
- **Environment**: {deployment_info.get('environment', 'Unknown')}
- **Image Tag**: {deployment_info.get('image_tag', 'Unknown')}
- **Deployed By**: {deployment_info.get('deployed_by', 'Unknown')}
- **Deployment Time**: {deployment_info.get('deployment_time', 'Unknown')}
- **Deployment ID**: {deployment_info.get('deployment_id', 'Unknown')}

## Quality Gates Status
- **Overall Status**: {quality_gates.get('overall_status', 'Unknown').upper()}
- **Lint & Format**: {quality_gates.get('lint_and_format', {}).get('status', 'Unknown')}
- **Static Analysis**: {quality_gates.get('static_analysis', {}).get('status', 'Unknown')}
- **Security Scan**: {quality_gates.get('security_scan', {}).get('status', 'Unknown')}
- **Test Coverage**: {quality_gates.get('test_coverage', {}).get('status', 'Unknown')}

## Performance Metrics
- **Performance Score**: {performance_score}/100
- **Status**: {'✅ Good' if performance_score >= 80 else '⚠️ Needs Improvement' if performance_score >= 60 else '❌ Poor'}

## Security Status
- **Security Score**: {security_score}/100
- **Status**: {'✅ Secure' if security_score >= 90 else '⚠️ Needs Attention' if security_score >= 70 else '❌ Vulnerable'}

## Recommendations
"""
        
        for rec in self.report.get("recommendations", []):
            priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(rec.get("priority", ""), "⚪")
            summary += f"- {priority_emoji} **{rec.get('category', 'General')}**: {rec.get('recommendation', '')}\n"
        
        return summary
    
    def save_report(self, filename: str):
        """Save the complete report to file"""
        with open(filename, 'w') as f:
            json.dump(self.report, f, indent=2)
        print(f"📄 Deployment report saved to {filename}")
    
    def print_summary(self):
        """Print the summary to console"""
        print(self.generate_summary())


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="PAKE System Deployment Report Generator")
    parser.add_argument("--image-tag", required=True, help="Docker image tag")
    parser.add_argument("--environment", required=True, help="Deployment environment")
    parser.add_argument("--deployed-by", required=True, help="User who deployed")
    parser.add_argument("--deployment-time", required=True, help="Deployment timestamp")
    parser.add_argument("--output", default="deployment_report.json", help="Output file")
    parser.add_argument("--ci-results", help="CI results JSON file")
    parser.add_argument("--performance-data", help="Performance data JSON file")
    parser.add_argument("--security-data", help="Security data JSON file")
    
    args = parser.parse_args()
    
    generator = DeploymentReportGenerator()
    
    # Add deployment information
    generator.add_deployment_info(
        args.image_tag,
        args.environment,
        args.deployed_by,
        args.deployment_time
    )
    
    # Load and add CI results if provided
    if args.ci_results:
        try:
            with open(args.ci_results, 'r') as f:
                ci_results = json.load(f)
            generator.add_quality_gates(ci_results)
        except Exception as e:
            print(f"Warning: Could not load CI results: {e}")
    
    # Load and add performance data if provided
    if args.performance_data:
        try:
            with open(args.performance_data, 'r') as f:
                performance_data = json.load(f)
            generator.add_performance_metrics(performance_data)
        except Exception as e:
            print(f"Warning: Could not load performance data: {e}")
    
    # Load and add security data if provided
    if args.security_data:
        try:
            with open(args.security_data, 'r') as f:
                security_data = json.load(f)
            generator.add_security_status(security_data)
        except Exception as e:
            print(f"Warning: Could not load security data: {e}")
    
    # Generate recommendations and save report
    generator.generate_recommendations()
    generator.save_report(args.output)
    generator.print_summary()


if __name__ == "__main__":
    main()
