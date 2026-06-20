import requests
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:8151'

def login(username, password):
    resp = requests.post(f'{BASE}/api/token/', json={'username': username, 'password': password})
    if resp.status_code == 200:
        return resp.json()['access']
    return None

print("=== Fix 2: Admin edit hall with illegal fields ===")
token = login('admin', 'admin123456')
headers = {'Authorization': f'Bearer {token}'}
print("Admin login:", "OK" if token else "FAIL")

halls = requests.get(f'{BASE}/api/halls/', headers=headers).json()
hall_id = halls[0]['id']
print(f"Using hall ID={hall_id}")

resp = requests.put(f'{BASE}/api/halls/{hall_id}/',
    json={
        'hall_name': 'Modified Hall',
        'illegal_field_xyz': 'this field does not exist',
        'another_bad_field': 12345,
        'DROP TABLE halls;': 'SQL injection test'
    },
    headers=headers)
print(f"Update with illegal fields: status={resp.status_code}")
if resp.status_code == 500:
    print("  FAIL: Still returns 500")
elif resp.status_code == 200:
    print("  PASS: Illegal fields filtered, normal response")
else:
    print(f"  Unexpected status: {resp.status_code}, body: {resp.text[:200]}")

print("\n=== Fix 3+4: Fault order in pending review and alert timing ===")
session_no = f"FIX-TEST-{int(time.time())}"
resp = requests.post(f'{BASE}/api/orders/create/',
    json={'hall_id': hall_id, 'session_no': session_no},
    headers=headers)
print(f"Create order: status={resp.status_code}")
order_id = resp.json()['id']

resp = requests.post(f'{BASE}/api/orders/{order_id}/self-check/',
    json={
        'self_check_result': False,
        'brightness': 55,
        'sound_channels': 'left',
        'film_source_verified': False,
        'cooling_status': 'overheat',
        'fault_description': 'Projector serious fault',
        'fault_level': 'high',
        'temp_solution': 'Temporary fix applied, pending review'
    },
    headers=headers)
print(f"Submit fault self-check: status={resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"  status: {data['status']}, temp_solution: {data.get('temp_solution')}")

print("\n--- Check pending review stats ---")
resp = requests.get(f'{BASE}/api/statistics/pending-review/', headers=headers)
data = resp.json()
print(f"Pending review count: {len(data)}")
found = any(o['id'] == order_id for o in data)
print(f"  Fault order in pending review: {'PASS' if found else 'FAIL'}")

print("\n--- Check alerts (should NOT have unreviewed alert right after submit) ---")
resp = requests.get(f'{BASE}/api/alerts/', headers=headers)
alerts = resp.json()
unreviewed_alerts = [a for a in alerts if a.get('type') == 'unreviewed_after_fix']
print(f"Total alerts: {len(alerts)}")
print(f"  Unreviewed alerts: {len(unreviewed_alerts)} (should be 0)")
print(f"  {'PASS' if len(unreviewed_alerts) == 0 else 'FAIL'}: No unreviewed alert immediately")

print("\n--- Create a normal order (pending_review status) ---")
session_no2 = f"FIX-TEST2-{int(time.time())}"
resp = requests.post(f'{BASE}/api/orders/create/',
    json={'hall_id': hall_id, 'session_no': session_no2},
    headers=headers)
order2_id = resp.json()['id']

resp = requests.post(f'{BASE}/api/orders/{order2_id}/self-check/',
    json={
        'self_check_result': True,
        'brightness': 95,
        'sound_channels': 'left,right,center',
        'film_source_verified': True,
        'cooling_status': 'normal'
    },
    headers=headers)
print(f"Normal self-check: status={resp.status_code}, new_status={resp.json()['status']}")

print("\n--- Check pending review stats (should have 2) ---")
resp = requests.get(f'{BASE}/api/statistics/pending-review/', headers=headers)
data = resp.json()
print(f"Pending review count: {len(data)} (expected 2)")
for o in data:
    print(f"  - {o['hall_code']} {o['session_no']} status={o['status']}")

print("\n=== All fix validations complete ===")
