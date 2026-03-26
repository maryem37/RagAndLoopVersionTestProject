#!/bin/bash

# Test Execution Script for Leave Request Management System
# This script provides convenient commands to run different test categories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPORT_DIR="$PROJECT_DIR/target"

# Functions
print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Main menu
show_menu() {
    echo ""
    print_header "Test Execution Menu"
    echo "1. Run all tests"
    echo "2. Run unit tests only"
    echo "3. Run integration tests only"
    echo "4. Run E2E tests only"
    echo "5. Run contract tests only"
    echo "6. Run with coverage report"
    echo "7. Run specific test class"
    echo "8. View coverage report"
    echo "9. View surefire report"
    echo "10. Clean build artifacts"
    echo "0. Exit"
    echo ""
    read -p "Select option (0-10): " choice
}

# Run all tests
run_all_tests() {
    print_header "Running All Tests"
    cd "$PROJECT_DIR"
    mvn clean test
    print_success "All tests completed"
}

# Run unit tests
run_unit_tests() {
    print_header "Running Unit Tests"
    cd "$PROJECT_DIR"
    mvn test -Dtest=*Service*Test
    print_success "Unit tests completed"
}

# Run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    
    # Check if services are running
    if ! nc -z localhost 9000 2>/dev/null; then
        print_warning "Auth Service not running on port 9000"
    fi
    if ! nc -z localhost 8080 2>/dev/null; then
        print_warning "Leave Service not running on port 8080"
    fi
    
    cd "$PROJECT_DIR"
    mvn test -Dtest=*IntegrationTest
    print_success "Integration tests completed"
}

# Run E2E tests
run_e2e_tests() {
    print_header "Running E2E Tests"
    
    # Check if services are running
    if ! nc -z localhost 9000 2>/dev/null; then
        print_error "Auth Service must be running on port 9000"
        return 1
    fi
    if ! nc -z localhost 8080 2>/dev/null; then
        print_error "Leave Service must be running on port 8080"
        return 1
    fi
    
    cd "$PROJECT_DIR"
    mvn test -Dtest=*E2ETest
    print_success "E2E tests completed"
}

# Run contract tests
run_contract_tests() {
    print_header "Running Contract Tests"
    cd "$PROJECT_DIR"
    mvn test -Dtest=*ContractTest
    print_success "Contract tests completed"
}

# Run with coverage
run_with_coverage() {
    print_header "Running Tests with Coverage Report"
    cd "$PROJECT_DIR"
    mvn clean test jacoco:report
    print_success "Coverage report generated"
    echo ""
    echo "Open coverage report:"
    echo "  target/site/jacoco/index.html"
}

# Run specific test class
run_specific_test() {
    echo ""
    read -p "Enter test class name (e.g., AuthServiceTest): " test_name
    if [ -z "$test_name" ]; then
        print_error "No test class specified"
        return 1
    fi
    
    print_header "Running $test_name"
    cd "$PROJECT_DIR"
    mvn test -Dtest="$test_name"
    print_success "Test completed"
}

# View coverage report
view_coverage_report() {
    if [ ! -f "$REPORT_DIR/site/jacoco/index.html" ]; then
        print_warning "Coverage report not found. Run tests with coverage first."
        return 1
    fi
    
    print_header "Opening Coverage Report"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$REPORT_DIR/site/jacoco/index.html"
    elif command -v open &> /dev/null; then
        open "$REPORT_DIR/site/jacoco/index.html"
    else
        echo "Please open: $REPORT_DIR/site/jacoco/index.html"
    fi
}

# View surefire report
view_surefire_report() {
    if [ ! -f "$REPORT_DIR/site/surefire-report.html" ]; then
        print_warning "Surefire report not found. Run tests first."
        return 1
    fi
    
    print_header "Opening Surefire Report"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$REPORT_DIR/site/surefire-report.html"
    elif command -v open &> /dev/null; then
        open "$REPORT_DIR/site/surefire-report.html"
    else
        echo "Please open: $REPORT_DIR/site/surefire-report.html"
    fi
}

# Clean build artifacts
clean_build() {
    print_header "Cleaning Build Artifacts"
    cd "$PROJECT_DIR"
    mvn clean
    print_success "Build cleaned"
}

# Main loop
main() {
    while true; do
        show_menu
        
        case $choice in
            1) run_all_tests ;;
            2) run_unit_tests ;;
            3) run_integration_tests ;;
            4) run_e2e_tests ;;
            5) run_contract_tests ;;
            6) run_with_coverage ;;
            7) run_specific_test ;;
            8) view_coverage_report ;;
            9) view_surefire_report ;;
            10) clean_build ;;
            0) 
                print_header "Exiting"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please try again."
                ;;
        esac
        
        read -p "Press Enter to continue..."
    done
}

# Run main function
main
