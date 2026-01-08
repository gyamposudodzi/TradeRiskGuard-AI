"""
Comprehensive test script for TradeGuard AI API
"""
import requests
import json
import pandas as pd
import io
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"
TEST_USER = {
    "email": f"test_{int(time.time())}@example.com",
    "username": f"tester_{int(time.time())}",
    "password": "SecurePass123!"
}

# Global variables
access_token = None
analysis_id = None
report_id = None

def print_response(response, label=""):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    if label:
        print(f"📋 {label}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response Body:")
        print(json.dumps(data, indent=2))
        return data
    except:
        print(f"Raw Response: {response.text}")
        return None
    print('='*60)

def create_test_user():
    """Create a test user for testing"""
    print("🧪 Creating test user...")
    
    response = requests.post(
        f"{BASE_URL}/api/users/register",
        json=TEST_USER
    )
    
    data = print_response(response, "User Registration")
    
    if response.status_code == 200:
        global access_token
        access_token = data.get("data", {}).get("access_token")
        print(f"✅ User created: {TEST_USER['email']}")
        print(f"🔑 Token: {access_token[:50]}...")
        return True
    return False

def login_user():
    """Login with test user"""
    print("\n🧪 Logging in test user...")
    
    response = requests.post(
        f"{BASE_URL}/api/users/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    data = print_response(response, "User Login")
    
    if response.status_code == 200:
        global access_token
        access_token = data.get("data", {}).get("access_token")
        print(f"✅ Logged in successfully")
        print(f"🔑 New token: {access_token[:50]}...")
        return True
    return False

def get_headers(with_auth=True):
    """Get request headers"""
    headers = {"Content-Type": "application/json"}
    if with_auth and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers

# =================== USER TESTS ===================

def test_user_profile():
    """Test user profile endpoint"""
    print("\n🧪 Testing User Profile...")
    
    response = requests.get(
        f"{BASE_URL}/api/users/profile",
        headers=get_headers()
    )
    
    print_response(response, "User Profile")
    return response.status_code == 200

def test_user_settings():
    """Test user settings endpoints"""
    print("\n🧪 Testing User Settings...")
    
    # Get current settings
    response = requests.get(
        f"{BASE_URL}/api/users/settings",
        headers=get_headers()
    )
    data = print_response(response, "Get Settings")
    
    if response.status_code != 200:
        return False
    
    # Update settings
    update_data = {
        "max_position_size_pct": 3.0,
        "min_win_rate": 35.0,
        "ai_enabled": True,
        "preferred_model": "gpt-4o-mini"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/users/settings",
        headers=get_headers(),
        json=update_data
    )
    
    print_response(response, "Update Settings")
    return response.status_code == 200

# =================== ANALYSIS TESTS ===================

def create_sample_csv():
    """Create sample CSV data for testing"""
    sample_data = {
        'trade_id': [1, 2, 3, 4, 5],
        'symbol': ['EURUSD', 'GBPUSD', 'BTCUSD', 'TSLA', 'XAUUSD'],
        'entry_time': [
            '2024-01-01 10:00:00',
            '2024-01-02 09:30:00', 
            '2024-01-03 15:00:00',
            '2024-01-04 11:00:00',
            '2024-01-05 08:00:00'
        ],
        'exit_time': [
            '2024-01-01 12:00:00',
            '2024-01-02 10:30:00',
            '2024-01-03 16:00:00',
            '2024-01-04 14:00:00',
            '2024-01-05 09:00:00'
        ],
        'trade_type': ['BUY', 'SELL', 'BUY', 'SELL', 'BUY'],
        'lot_size': [0.1, 0.2, 0.01, 5, 0.05],
        'entry_price': [1.1000, 1.2700, 42000, 250, 2020],
        'exit_price': [1.1020, 1.2680, 42500, 245, 2030],
        'stop_loss': [1.0980, 1.2750, 41000, 255, 2010],
        'take_profit': [1.1050, 1.2650, 43000, 240, 2040],
        'profit_loss': [20.00, 40.00, 50.00, -25.00, 10.00],
        'account_balance_before': [10000, 10020, 10060, 10110, 10085]
    }
    
    df = pd.DataFrame(sample_data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    return csv_buffer.getvalue()

def test_analyze_with_sample():
    """Test analysis with sample data"""
    print("\n🧪 Testing Analysis with Sample Data...")
    
    response = requests.post(
        f"{BASE_URL}/api/analyze/trades",
        params={"use_sample": True},
        headers=get_headers()
    )
    
    data = print_response(response, "Analyze with Sample")
    
    if response.status_code == 200 and data and data.get("success"):
        global analysis_id
        analysis_id = data.get("data", {}).get("analysis_id")
        print(f"✅ Analysis created: {analysis_id}")
        return True
    return False

def test_analyze_with_csv():
    """Test analysis with CSV upload"""
    print("\n🧪 Testing Analysis with CSV Upload...")
    
    # Create CSV file
    csv_content = create_sample_csv()
    
    files = {
        'file': ('sample_trades.csv', csv_content, 'text/csv')
    }
    
    response = requests.post(
        f"{BASE_URL}/api/analyze/trades",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"} if access_token else {}
    )
    
    data = print_response(response, "Analyze with CSV")
    
    if response.status_code == 200 and data and data.get("success"):
        global analysis_id
        analysis_id = data.get("data", {}).get("analysis_id")
        print(f"✅ CSV analysis created: {analysis_id}")
        return True
    return False

def test_get_analysis():
    """Test retrieving analysis results"""
    if not analysis_id:
        print("❌ No analysis ID available")
        return False
    
    print(f"\n🧪 Testing Get Analysis: {analysis_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/analyze/{analysis_id}",
        headers=get_headers()
    )
    
    data = print_response(response, "Get Analysis")
    
    if response.status_code == 200 and data and data.get("success"):
        result = data.get("data", {})
        print(f"✅ Analysis retrieved")
        print(f"   Score: {result.get('score_result', {}).get('score', 'N/A')}/100")
        print(f"   Grade: {result.get('score_result', {}).get('grade', 'N/A')}")
        print(f"   Risks: {len(result.get('risk_results', {}).get('detected_risks', []))}")
        return True
    return False

def test_list_analyses():
    """Test listing all analyses"""
    print("\n🧪 Testing List Analyses...")
    
    response = requests.get(
        f"{BASE_URL}/api/analyze/",
        headers=get_headers()
    )
    
    data = print_response(response, "List Analyses")
    
    if response.status_code == 200 and data and data.get("success"):
        analyses = data.get("data", {}).get("analyses", [])
        print(f"✅ Found {len(analyses)} analyses")
        return True
    return False

# =================== RISK TESTS ===================

def test_risk_calculation():
    """Test risk calculation endpoint"""
    print("\n🧪 Testing Risk Calculation...")
    
    sample_risk_details = {
        "over_leverage": {
            "severity": 75.0,
            "message": "Position size too large"
        },
        "no_stop_loss": {
            "severity": 60.0,
            "message": "Missing stop-loss"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/risk/calculate",
        headers=get_headers(),
        json=sample_risk_details
    )
    
    data = print_response(response, "Risk Calculation")
    return response.status_code == 200

def test_risk_explanations():
    """Test AI risk explanations"""
    print("\n🧪 Testing Risk Explanations...")
    
    sample_data = {
        "metrics": {
            "win_rate": 42.2,
            "profit_factor": 1.35,
            "max_drawdown_pct": 22.5,
            "avg_position_size_pct": 3.2
        },
        "risk_results": {
            "detected_risks": ["over_leverage", "no_stop_loss"],
            "risk_details": {
                "over_leverage": {"severity": 75.0, "message": "Position size too large"},
                "no_stop_loss": {"severity": 60.0, "message": "Missing stop-loss"}
            }
        },
        "score_result": {
            "score": 65.5,
            "grade": "C",
            "total_risks": 2
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/risk/explanations",
        headers=get_headers(),
        json={**sample_data, "format_for_display": True}
    )
    
    data = print_response(response, "Risk Explanations")
    
    if response.status_code == 200 and data and data.get("success"):
        result = data.get("data", {})
        print(f"✅ AI Model used: {result.get('ai_model', 'N/A')}")
        if result.get('formatted'):
            print(f"📝 Formatted output available ({len(result.get('formatted', ''))} chars)")
        return True
    return False

def test_risk_simulation():
    """Test risk simulation"""
    print("\n🧪 Testing Risk Simulation...")
    
    simulation_data = {
        "current_score": 65.5,
        "improvements": {
            "over_leverage": 30.0,
            "no_stop_loss": 20.0
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/risk/simulate",
        headers=get_headers(),
        json=simulation_data
    )
    
    data = print_response(response, "Risk Simulation")
    
    if response.status_code == 200 and data and data.get("success"):
        result = data.get("data", {})
        print(f"✅ Original: {result.get('original_score')}")
        print(f"✅ Simulated: {result.get('simulated_score')}")
        print(f"✅ Improvement: {result.get('improvement'):.1f} points")
        return True
    return False

def test_risk_types():
    """Test getting risk types"""
    print("\n🧪 Testing Risk Types...")
    
    response = requests.get(
        f"{BASE_URL}/api/risk/types",
        headers=get_headers()
    )
    
    data = print_response(response, "Risk Types")
    
    if response.status_code == 200 and data and data.get("success"):
        risk_types = data.get("data", {})
        print(f"✅ Found {len(risk_types)} risk types")
        for risk_name in risk_types.keys():
            print(f"   - {risk_name}")
        return True
    return False

# =================== REPORT TESTS ===================

def test_generate_report():
    """Test report generation"""
    if not analysis_id:
        print("❌ No analysis ID available for report")
        return False
    
    print(f"\n🧪 Testing Report Generation for analysis: {analysis_id}")
    
    report_data = {
        "analysis_id": analysis_id,
        "format": "markdown",
        "include_sections": [
            "Executive Summary",
            "Trading Metrics", 
            "Risk Analysis",
            "AI Insights"
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers=get_headers(),
        json=report_data
    )
    
    data = print_response(response, "Generate Report")
    
    if response.status_code == 200 and data and data.get("success"):
        global report_id
        report_id = data.get("data", {}).get("id")
        print(f"✅ Report generated: {report_id}")
        return True
    return False

def test_download_report():
    """Test report download"""
    if not report_id:
        print("❌ No report ID available")
        return False
    
    print(f"\n🧪 Testing Report Download: {report_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/reports/download/{report_id}",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        print(f"✅ Report downloaded successfully")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   Size: {len(response.text)} characters")
        return True
    else:
        print_response(response, "Download Report")
        return False

def test_list_reports():
    """Test listing reports for an analysis"""
    if not analysis_id:
        print("❌ No analysis ID available")
        return False
    
    print(f"\n🧪 Testing List Reports for analysis: {analysis_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/reports/{analysis_id}",
        headers=get_headers()
    )
    
    data = print_response(response, "List Reports")
    
    if response.status_code == 200 and data and data.get("success"):
        reports = data.get("data", [])
        print(f"✅ Found {len(reports)} reports")
        return True
    return False

# =================== DASHBOARD TESTS ===================

def test_dashboard_summary():
    """Test dashboard summary"""
    print("\n🧪 Testing Dashboard Summary...")
    
    response = requests.get(
        f"{BASE_URL}/api/dashboard/summary",
        headers=get_headers()
    )
    
    data = print_response(response, "Dashboard Summary")
    
    if response.status_code == 200 and data and data.get("success"):
        summary = data.get("data", {})
        print(f"✅ Total Analyses: {summary.get('total_analyses', 0)}")
        print(f"✅ Average Score: {summary.get('average_score', 0):.1f}")
        return True
    return False

def test_dashboard_metrics():
    """Test dashboard metrics"""
    print("\n🧪 Testing Dashboard Metrics...")
    
    response = requests.get(
        f"{BASE_URL}/api/dashboard/metrics",
        params={"period": "month"},
        headers=get_headers()
    )
    
    data = print_response(response, "Dashboard Metrics")
    
    if response.status_code == 200 and data and data.get("success"):
        metrics = data.get("data", {})
        print(f"✅ Period: {metrics.get('period')}")
        print(f"✅ Analyses Count: {metrics.get('analyses_count')}")
        return True
    return False

def test_dashboard_insights():
    """Test dashboard insights"""
    print("\n🧪 Testing Dashboard Insights...")
    
    response = requests.get(
        f"{BASE_URL}/api/dashboard/insights",
        params={"limit": 3},
        headers=get_headers()
    )
    
    data = print_response(response, "Dashboard Insights")
    
    if response.status_code == 200 and data and data.get("success"):
        insights = data.get("data", {})
        print(f"✅ Insights: {len(insights.get('insights', []))}")
        for insight in insights.get('insights', []):
            print(f"   • {insight[:80]}...")
        return True
    return False

# =================== QUICK ANALYSIS TESTS ===================

def test_quick_analyze():
    """Test quick analysis with JSON data"""
    print("\n🧪 Testing Quick Analysis...")
    
    trades_data = {
        "trades": [
            {
                "trade_id": 1,
                "symbol": "EURUSD",
                "profit_loss": 50.0,
                "lot_size": 0.1,
                "account_balance_before": 10000,
                "entry_time": "2024-01-01 10:00:00",
                "exit_time": "2024-01-01 12:00:00"
            },
            {
                "trade_id": 2,
                "symbol": "GBPUSD",
                "profit_loss": -30.0,
                "lot_size": 0.2,
                "account_balance_before": 10050,
                "entry_time": "2024-01-02 09:30:00",
                "exit_time": "2024-01-02 10:30:00"
            }
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/analyze/quick",
        headers=get_headers(),
        json=trades_data
    )
    
    data = print_response(response, "Quick Analysis")
    
    if response.status_code == 200 and data and data.get("success"):
        print(f"✅ Quick analysis completed")
        return True
    return False

# =================== ERROR CASE TESTS ===================

def test_error_cases():
    """Test error scenarios"""
    print("\n🧪 Testing Error Cases...")
    
    tests = [
        # 1. Register with duplicate email
        ("POST", "/api/users/register", {
            "email": TEST_USER["email"],
            "username": "duplicate_test",
            "password": "Test123!"
        }, "Duplicate Registration (Should fail)"),
        
        # 2. Invalid login
        ("POST", "/api/users/login", {
            "email": TEST_USER["email"],
            "password": "WRONG_PASSWORD"
        }, "Invalid Login (Should fail)"),
        
        # 3. Profile without token
        ("GET", "/api/users/profile", None, "Profile without token (Should fail)"),
        
        # 4. Analyze with invalid file
        ("POST", "/api/analyze/trades", None, "Analyze without file (Should fail)"),
    ]
    
    all_passed = True
    for method, endpoint, data, label in tests:
        print(f"\n   Testing: {label}")
        
        if method == "POST":
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"} if data else {}
            )
        else:  # GET
            response = requests.get(f"{BASE_URL}{endpoint}")
        
        if response.status_code >= 400:
            print(f"   ✅ Correctly failed with {response.status_code}")
        else:
            print(f"   ❌ Should have failed but got {response.status_code}")
            all_passed = False
    
    return all_passed

# =================== MAIN TEST RUNNER ===================

def run_all_tests():
    """Run all API tests"""
    print("🚀 Starting Comprehensive API Tests")
    print("="*60)
    
    results = {}
    
    # Phase 1: User Management
    print("\n📋 PHASE 1: USER MANAGEMENT")
    print("-" * 40)
    results["create_user"] = create_test_user()
    results["login"] = login_user()
    results["profile"] = test_user_profile()
    results["settings"] = test_user_settings()
    
    # Phase 2: Analysis
    print("\n📋 PHASE 2: TRADE ANALYSIS")
    print("-" * 40)
    results["analyze_sample"] = test_analyze_with_sample()
    results["analyze_csv"] = test_analyze_with_csv()
    results["get_analysis"] = test_get_analysis()
    results["list_analyses"] = test_list_analyses()
    results["quick_analyze"] = test_quick_analyze()
    
    # Phase 3: Risk Assessment
    print("\n📋 PHASE 3: RISK ASSESSMENT")
    print("-" * 40)
    results["risk_calculation"] = test_risk_calculation()
    results["risk_explanations"] = test_risk_explanations()
    results["risk_simulation"] = test_risk_simulation()
    results["risk_types"] = test_risk_types()
    
    # Phase 4: Reports
    print("\n📋 PHASE 4: REPORT GENERATION")
    print("-" * 40)
    results["generate_report"] = test_generate_report()
    results["download_report"] = test_download_report()
    results["list_reports"] = test_list_reports()
    
    # Phase 5: Dashboard
    print("\n📋 PHASE 5: DASHBOARD")
    print("-" * 40)
    results["dashboard_summary"] = test_dashboard_summary()
    results["dashboard_metrics"] = test_dashboard_metrics()
    results["dashboard_insights"] = test_dashboard_insights()
    
    # Phase 6: Error Cases
    print("\n📋 PHASE 6: ERROR CASES")
    print("-" * 40)
    results["error_cases"] = test_error_cases()
    
    # Print Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🌟 ALL TESTS PASSED! Your API is working perfectly!")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")
    
    return results

if __name__ == "__main__":
    # Make sure the API is running first!
    print("⚠️  Make sure your API is running on http://localhost:8000")
    print("   Run: python main.py")
    print("="*60)
    
    input("Press Enter to start tests...")
    
    try:
        results = run_all_tests()
        
        # Save results to file
        with open("test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "user": TEST_USER["email"],
                "results": results,
                "analysis_id": analysis_id,
                "report_id": report_id
            }, f, indent=2)
        
        print(f"\n📄 Results saved to test_results.json")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API. Make sure it's running on http://localhost:8000")
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()