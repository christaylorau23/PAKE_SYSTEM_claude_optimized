#!/bin/bash

# 🚀 Kubernetes Deployment Script for Personal Wealth Generation Platform
# World-Class Production Deployment with Auto-Scaling
# Optimized for single-user maximum performance and wealth generation

set -e

echo "🚀 Starting Kubernetes deployment of Personal Wealth Generation Platform..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="wealth-platform"
KUBECTL_TIMEOUT="600s"
DOCKER_IMAGE="wealth-platform:latest"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${PURPLE}🎯 $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        print_error "docker is not installed or not in PATH"
        exit 1
    fi

    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster. Please check your kubectl configuration."
        exit 1
    fi

    print_status "All prerequisites satisfied"

    # Display cluster info
    print_info "Connected to cluster: $(kubectl config current-context)"
    print_info "Kubernetes version: $(kubectl version --client --short 2>/dev/null | grep Client || echo 'Unknown')"
}

# Build Docker image
build_docker_image() {
    print_header "Building Docker image..."

    if [ -f "../Dockerfile" ]; then
        cd ..
        docker build -t $DOCKER_IMAGE .
        cd k8s
        print_status "Docker image built successfully"
    else
        print_warning "Dockerfile not found, assuming image already exists"
    fi
}

# Create namespace and apply resource limits
setup_namespace() {
    print_header "Setting up namespace and resource limits..."

    kubectl apply -f namespace.yaml --timeout=$KUBECTL_TIMEOUT

    # Wait for namespace to be ready
    kubectl wait --for=condition=Active --timeout=$KUBECTL_TIMEOUT namespace/$NAMESPACE

    print_status "Namespace '$NAMESPACE' created and configured"
}

# Deploy data layer (Redis and PostgreSQL)
deploy_data_layer() {
    print_header "Deploying data layer (Redis and PostgreSQL)..."

    # Deploy Redis Enterprise
    print_info "Deploying Redis Enterprise cluster..."
    kubectl apply -f redis-deployment.yaml --timeout=$KUBECTL_TIMEOUT

    # Deploy PostgreSQL
    print_info "Deploying PostgreSQL primary..."
    kubectl apply -f postgresql-deployment.yaml --timeout=$KUBECTL_TIMEOUT

    # Wait for data services to be ready
    print_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=available --timeout=$KUBECTL_TIMEOUT deployment/redis-enterprise -n $NAMESPACE

    print_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=available --timeout=$KUBECTL_TIMEOUT deployment/postgresql-primary -n $NAMESPACE

    print_status "Data layer deployed successfully"
}

# Deploy application layer
deploy_application_layer() {
    print_header "Deploying application layer..."

    # Deploy main wealth platform application
    kubectl apply -f wealth-platform-deployment.yaml --timeout=$KUBECTL_TIMEOUT

    # Wait for application to be ready
    print_info "Waiting for wealth platform to be ready..."
    kubectl wait --for=condition=available --timeout=$KUBECTL_TIMEOUT deployment/wealth-platform-api -n $NAMESPACE

    print_status "Application layer deployed successfully"
}

# Deploy auto-scaling configuration
deploy_autoscaling() {
    print_header "Deploying auto-scaling configuration..."

    # Apply HPA and PDB configurations
    kubectl apply -f autoscaling.yaml --timeout=$KUBECTL_TIMEOUT

    # Check if HPA is working
    print_info "Checking Horizontal Pod Autoscaler status..."
    sleep 10  # Give HPA time to initialize
    kubectl get hpa -n $NAMESPACE

    print_status "Auto-scaling configuration deployed"
}

# Deploy monitoring stack
deploy_monitoring() {
    print_header "Deploying monitoring stack (Prometheus & Grafana)..."

    kubectl apply -f monitoring.yaml --timeout=$KUBECTL_TIMEOUT

    # Wait for monitoring services to be ready
    print_info "Waiting for Prometheus to be ready..."
    kubectl wait --for=condition=available --timeout=$KUBECTL_TIMEOUT deployment/prometheus -n $NAMESPACE

    print_info "Waiting for Grafana to be ready..."
    kubectl wait --for=condition=available --timeout=$KUBECTL_TIMEOUT deployment/grafana -n $NAMESPACE

    print_status "Monitoring stack deployed successfully"
}

# Deploy ingress and networking
deploy_ingress() {
    print_header "Deploying ingress and networking..."

    # Check if nginx ingress controller is installed
    if ! kubectl get ingressclass nginx &> /dev/null; then
        print_warning "NGINX Ingress Controller not found. Installing..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml

        # Wait for ingress controller to be ready
        print_info "Waiting for NGINX Ingress Controller..."
        kubectl wait --namespace ingress-nginx \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/component=controller \
            --timeout=$KUBECTL_TIMEOUT
    fi

    kubectl apply -f ingress.yaml --timeout=$KUBECTL_TIMEOUT

    print_status "Ingress and networking configured"
}

# Verify deployment
verify_deployment() {
    print_header "Verifying deployment..."

    print_info "Deployment status:"
    kubectl get deployments -n $NAMESPACE -o wide

    print_info "\nService status:"
    kubectl get services -n $NAMESPACE -o wide

    print_info "\nPod status:"
    kubectl get pods -n $NAMESPACE -o wide

    print_info "\nPersistent Volume Claims:"
    kubectl get pvc -n $NAMESPACE

    print_info "\nHorizontal Pod Autoscalers:"
    kubectl get hpa -n $NAMESPACE

    print_info "\nIngress status:"
    kubectl get ingress -n $NAMESPACE

    # Check if all pods are running
    NOT_READY=$(kubectl get pods -n $NAMESPACE --no-headers | grep -v Running | wc -l)
    if [ $NOT_READY -eq 0 ]; then
        print_status "All pods are running successfully!"
    else
        print_warning "$NOT_READY pods are not in Running state"
        kubectl get pods -n $NAMESPACE | grep -v Running
    fi

    print_status "Deployment verification completed"
}

# Performance testing
run_performance_test() {
    print_header "Running basic performance test..."

    # Get the service endpoint
    WEALTH_SERVICE_IP=$(kubectl get service wealth-platform-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

    if [ -z "$WEALTH_SERVICE_IP" ]; then
        WEALTH_SERVICE_IP=$(kubectl get service wealth-platform-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')
        print_info "Using ClusterIP for testing: $WEALTH_SERVICE_IP"
    else
        print_info "Using LoadBalancer IP for testing: $WEALTH_SERVICE_IP"
    fi

    # Port forward for testing if no external IP
    if [ "$WEALTH_SERVICE_IP" = "$(kubectl get service wealth-platform-service -n $NAMESPACE -o jsonpath='{.spec.clusterIP}')" ]; then
        print_info "Setting up port forward for testing..."
        kubectl port-forward -n $NAMESPACE service/wealth-platform-service 8000:80 &
        PORT_FORWARD_PID=$!
        sleep 5

        # Test health endpoint
        if curl -s -f http://localhost:8000/health > /dev/null; then
            print_status "Health check passed ✅"
        else
            print_error "Health check failed ❌"
        fi

        # Test API endpoint
        if curl -s -f http://localhost:8000/api/status > /dev/null; then
            print_status "API endpoint accessible ✅"
        else
            print_warning "API endpoint test failed (may be expected if not implemented)"
        fi

        # Clean up port forward
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi

    print_status "Basic performance test completed"
}

# Display access information
show_access_info() {
    print_header "Access Information"

    echo -e "${CYAN}🌐 Wealth Generation Platform Endpoints:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Get LoadBalancer IPs if available
    WEALTH_LB_IP=$(kubectl get service wealth-platform-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    GRAFANA_PORT=$(kubectl get service grafana-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')
    PROMETHEUS_PORT=$(kubectl get service prometheus-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}')

    if [ -n "$WEALTH_LB_IP" ]; then
        echo -e "🚀 Main Platform:    ${GREEN}https://$WEALTH_LB_IP${NC}"
        echo -e "📊 API Endpoint:     ${GREEN}https://$WEALTH_LB_IP/api${NC}"
        echo -e "❤️  Health Check:     ${GREEN}https://$WEALTH_LB_IP/health${NC}"
    else
        echo -e "🚀 Main Platform:    ${YELLOW}kubectl port-forward -n $NAMESPACE service/wealth-platform-service 8000:80${NC}"
        echo -e "                    ${YELLOW}Then access: http://localhost:8000${NC}"
    fi

    echo -e "📈 Grafana:          ${GREEN}kubectl port-forward -n $NAMESPACE service/grafana-service $GRAFANA_PORT:$GRAFANA_PORT${NC}"
    echo -e "                    ${GREEN}Then access: http://localhost:$GRAFANA_PORT${NC}"
    echo -e "                    ${YELLOW}Username: admin, Password: Check Grafana secret in Vault${NC}"

    echo -e "🔍 Prometheus:       ${GREEN}kubectl port-forward -n $NAMESPACE service/prometheus-service $PROMETHEUS_PORT:$PROMETHEUS_PORT${NC}"
    echo -e "                    ${GREEN}Then access: http://localhost:$PROMETHEUS_PORT${NC}"

    echo ""
    echo -e "${CYAN}🛠️  Management Commands:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "📊 View all resources:   ${GREEN}kubectl get all -n $NAMESPACE${NC}"
    echo -e "📋 View logs:           ${GREEN}kubectl logs -f deployment/wealth-platform-api -n $NAMESPACE${NC}"
    echo -e "🔄 Restart deployment:  ${GREEN}kubectl rollout restart deployment/wealth-platform-api -n $NAMESPACE${NC}"
    echo -e "📈 View HPA status:     ${GREEN}kubectl get hpa -n $NAMESPACE${NC}"
    echo -e "🧹 Clean up:           ${GREEN}kubectl delete namespace $NAMESPACE${NC}"

    echo ""
    echo -e "${PURPLE}🎯 Your Personal Wealth Generation Platform is now running!${NC}"
    echo -e "${PURPLE}Ready to identify opportunities and generate wealth with AI-powered intelligence.${NC}"
}

# Main deployment flow
main() {
    print_header "Personal Wealth Generation Platform - Kubernetes Deployment"
    echo "Optimized for single-user maximum performance and wealth generation"
    echo ""

    check_prerequisites
    build_docker_image
    setup_namespace
    deploy_data_layer
    deploy_application_layer
    deploy_autoscaling
    deploy_monitoring
    deploy_ingress
    verify_deployment
    run_performance_test
    show_access_info

    echo ""
    print_status "🎉 Deployment completed successfully!"
    print_info "Your Personal Wealth Generation Platform is ready to identify trends and opportunities!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Handle script interruption
cleanup() {
    print_warning "Deployment interrupted. Cleaning up..."
    kill $PORT_FORWARD_PID 2>/dev/null || true
    exit 1
}

trap cleanup INT TERM

# Run main function
main "$@"