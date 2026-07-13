import requests

BASE_URL = "http://127.0.0.1:8000"

test_incidents = [
    "Core switch has no LEDs on and is not responding to ping",
    "Users complaining about slow internet, router CPU is at 95%",
    "Wifi on 3rd floor keeps disconnecting every few minutes",
    "Port 12 on switch keeps going up and down in the logs",
    "BGP neighbor to ISP router is down",
    "New laptop not getting an IP address from DHCP",
    "VPN tunnel to branch office keeps dropping",
    "Firewall is blocking access to the internal portal",
    "Printer not responding to any print jobs",
    "Something strange is happening with the network, not sure what",
]

def run_tests():
    print(f"{'='*70}")
    print(f"NetMind AI — Automated End-to-End Test ({len(test_incidents)} incidents)")
    print(f"{'='*70}\n")

    results = []

    for idx, text in enumerate(test_incidents, 1):
        print(f"[{idx}/{len(test_incidents)}] Testing: \"{text[:60]}...\"" if len(text) > 60 else f"[{idx}/{len(test_incidents)}] Testing: \"{text}\"")

        status = {"text": text, "create": "FAIL", "detail": "FAIL", "alert": "FAIL", "report": "FAIL"}

        # 1. Create incident
        try:
            r = requests.post(f"{BASE_URL}/api/incidents", json={"text": text}, timeout=10)
            if r.status_code == 200:
                incident_id = r.json()["id"]
                device = r.json()["parsed"]["device"]
                severity = r.json()["diagnosis"]["severity"]
                matched = r.json()["diagnosis"]["matched"]
                status["create"] = "PASS"
                print(f"    Created -> ID:{incident_id} | Device:{device} | Severity:{severity} | Matched:{matched}")
            else:
                print(f"    Create FAILED — status {r.status_code}")
                results.append(status)
                continue
        except Exception as e:
            print(f"    Create FAILED — {e}")
            results.append(status)
            continue

        # 2. Get detail
        try:
            r = requests.get(f"{BASE_URL}/api/incidents/{incident_id}", timeout=10)
            status["detail"] = "PASS" if r.status_code == 200 else "FAIL"
        except Exception as e:
            print(f"    Detail FAILED — {e}")

        # 3. Get alert
        try:
            r = requests.get(f"{BASE_URL}/api/incidents/{incident_id}/alert", timeout=10)
            status["alert"] = "PASS" if r.status_code == 200 and "alert" in r.json() else "FAIL"
        except Exception as e:
            print(f"    Alert FAILED — {e}")

        # 4. Get PDF report
        try:
            r = requests.get(f"{BASE_URL}/api/incidents/{incident_id}/report", timeout=15)
            status["report"] = "PASS" if r.status_code == 200 and r.headers.get("content-type") == "application/pdf" else "FAIL"
        except Exception as e:
            print(f"    Report FAILED — {e}")

        print(f"    Detail:{status['detail']} | Alert:{status['alert']} | Report:{status['report']}\n")
        results.append(status)

    # Summary
    print(f"{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    total_tests = len(results) * 4
    passed = sum(1 for r in results for k in ["create", "detail", "alert", "report"] if r[k] == "PASS")
    print(f"Total checks: {total_tests} | Passed: {passed} | Failed: {total_tests - passed}\n")

    for r in results:
        failed_steps = [k for k in ["create", "detail", "alert", "report"] if r[k] == "FAIL"]
        if failed_steps:
            print(f"ISSUE in \"{r['text'][:50]}...\": failed at {', '.join(failed_steps)}")

    if passed == total_tests:
        print("\nAll tests passed! System is stable for demo.")
    else:
        print(f"\n{total_tests - passed} check(s) failed — review above before presenting.")


if __name__ == "__main__":
    run_tests()