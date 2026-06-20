import requests
import json
import time

BASE = 'http://127.0.0.1:8151'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

print_section("1. 测试登录")
resp = requests.post(f'{BASE}/api/token/', json={'username': 'admin', 'password': 'admin123456'})
print(f"状态码: {resp.status_code}")
token = resp.json()['access']
print("管理员登录成功")
headers = {'Authorization': f'Bearer {token}'}

print_section("2. 测试创建巡检单（放映员流程）")
halls = requests.get(f'{BASE}/api/halls/', headers=headers).json()
hall_id = halls[0]['id']
hall_code = halls[0]['hall_code']
print(f"使用影厅: {hall_code}")

session_no = f"TEST-{int(time.time())}"
resp = requests.post(f'{BASE}/api/orders/create/', 
    json={'hall_id': hall_id, 'session_no': session_no},
    headers=headers)
print(f"创建巡检单: 状态码={resp.status_code}")
if resp.status_code == 201:
    order = resp.json()
    order_id = order['id']
    print(f"  订单ID: {order_id}")
    print(f"  当前状态: {order['status']}")
else:
    print(f"  错误: {resp.text}")
    exit(1)

print_section("3. 测试重复创建（应失败）")
resp = requests.post(f'{BASE}/api/orders/create/', 
    json={'hall_id': hall_id, 'session_no': session_no},
    headers=headers)
print(f"重复创建: 状态码={resp.status_code}")
print(f"  错误: {resp.json().get('error')}")

print_section("4. 测试提交自检 - 正常通过")
resp = requests.post(f'{BASE}/api/orders/{order_id}/self-check/',
    json={
        'self_check_result': True,
        'brightness': 85,
        'sound_channels': 'left,right,center',
        'film_source_verified': True,
        'cooling_status': 'normal'
    },
    headers=headers)
print(f"提交自检: 状态码={resp.status_code}")
if resp.status_code == 200:
    order = resp.json()
    print(f"  状态: {order['status']}")
    print(f"  亮度: {order['brightness']}")
    print(f"  片源校验: {order['film_source_verified']}")
else:
    print(f"  错误: {resp.text}")

print_section("5. 测试创建另一个巡检单 - 有故障")
session_no2 = f"TEST-FAULT-{int(time.time())}"
resp = requests.post(f'{BASE}/api/orders/create/', 
    json={'hall_id': hall_id, 'session_no': session_no2},
    headers=headers)
print(f"创建巡检单: 状态码={resp.status_code}")
order2_id = resp.json()['id']

resp = requests.post(f'{BASE}/api/orders/{order2_id}/self-check/',
    json={
        'self_check_result': False,
        'brightness': 65,
        'sound_channels': 'left,right',
        'film_source_verified': False,
        'cooling_status': 'overheat',
        'fault_description': '放映机亮度不足，散热风扇异响',
        'fault_level': 'high',
        'temp_solution': '已降低亮度，通知技术人员'
    },
    headers=headers)
print(f"提交故障自检: 状态码={resp.status_code}")
if resp.status_code == 200:
    order = resp.json()
    print(f"  状态: {order['status']}")
    print(f"  故障等级: {order['fault_level']}")
    print(f"  故障描述: {order['fault_description']}")

print_section("6. 测试复核员登录")
resp = requests.post(f'{BASE}/api/token/', json={'username': 'reviewer1', 'password': 'review123456'})
reviewer_token = resp.json()['access']
reviewer_headers = {'Authorization': f'Bearer {reviewer_token}'}
print("复核员登录成功")

print_section("7. 测试复映审核 - 通过")
resp = requests.post(f'{BASE}/api/orders/{order_id}/review/',
    json={
        'recheck_result': True,
        'problem_cause': '设备正常，自检通过',
        'final_conclusion': '可以正常放映'
    },
    headers=reviewer_headers)
print(f"复映审核: 状态码={resp.status_code}")
if resp.status_code == 200:
    order = resp.json()
    print(f"  状态: {order['status']}")
    print(f"  复核员: {order['reviewer_name']}")
    print(f"  最终结论: {order['final_conclusion']}")
else:
    print(f"  错误: {resp.text}")

print_section("8. 测试复映审核 - 故障单")
resp = requests.post(f'{BASE}/api/orders/{order2_id}/review/',
    json={
        'recheck_result': False,
        'problem_cause': '氙灯老化，需要更换',
        'final_conclusion': '暂停放映，待更换氙灯'
    },
    headers=reviewer_headers)
print(f"故障单复核: 状态码={resp.status_code}")
if resp.status_code == 200:
    order = resp.json()
    print(f"  状态: {order['status']}")
    print(f"  问题归因: {order['problem_cause']}")
else:
    print(f"  错误: {resp.text}")

print_section("9. 测试列表检索 - 多条件筛选")
test_cases = [
    ('全部', {}),
    ('按状态筛选', {'status': 'ready'}),
    ('按影厅筛选', {'hall_id': hall_id}),
    ('按故障等级筛选', {'fault_level': 'high'}),
]

for name, params in test_cases:
    resp = requests.get(f'{BASE}/api/orders/', params=params, headers=headers)
    data = resp.json()
    print(f"  {name}: {data['total']} 条")

print_section("10. 测试统计接口")
print("--- 高频故障设备 ---")
resp = requests.get(f'{BASE}/api/statistics/high-fault-devices/', headers=headers)
print(f"  状态码: {resp.status_code}, 数量: {len(resp.json())}")

print("--- 待复映任务 ---")
resp = requests.get(f'{BASE}/api/statistics/pending-review/', headers=headers)
print(f"  状态码: {resp.status_code}, 数量: {len(resp.json())}")

print("--- 影厅稳定率 ---")
resp = requests.get(f'{BASE}/api/statistics/hall-stability/', headers=headers)
data = resp.json()
print(f"  状态码: {resp.status_code}, 影厅数: {len(data)}")
for item in data[:3]:
    print(f"    {item['hall_code']}: {item['stability_rate']}%")

print("--- 总览 ---")
resp = requests.get(f'{BASE}/api/statistics/overview/', headers=headers)
data = resp.json()
print(f"  状态码: {resp.status_code}")
print(f"  高频故障设备: {len(data['high_fault_devices'])} 条")
print(f"  待复映任务: {len(data['pending_review_tasks'])} 条")
print(f"  影厅稳定率: {len(data['hall_stability_rates'])} 条")

print_section("11. 测试告警接口")
resp = requests.get(f'{BASE}/api/alerts/', headers=headers)
alerts = resp.json()
print(f"状态码: {resp.status_code}, 告警数量: {len(alerts)}")
for alert in alerts[:5]:
    print(f"  [{alert['level']}] {alert['type']}: {alert['message']}")

print_section("12. 测试选项接口")
print("--- 状态选项 ---")
resp = requests.get(f'{BASE}/api/choices/status/', headers=headers)
print(f"  状态码: {resp.status_code}, 选项数: {len(resp.json())}")

print("--- 故障等级选项 ---")
resp = requests.get(f'{BASE}/api/choices/fault-level/', headers=headers)
print(f"  状态码: {resp.status_code}, 选项数: {len(resp.json())}")

print_section("✅ 所有测试完成！")
