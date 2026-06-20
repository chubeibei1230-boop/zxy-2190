import requests
import json

BASE = 'http://127.0.0.1:8151'

print('=== 测试登录 ===')
resp = requests.post(f'{BASE}/api/token/', json={'username': 'admin', 'password': 'admin123456'})
print(f'状态码: {resp.status_code}')
if resp.status_code == 200:
    token = resp.json()['access']
    print('登录成功')
    headers = {'Authorization': f'Bearer {token}'}
    
    print('\n=== 测试用户信息 ===')
    resp = requests.get(f'{BASE}/api/users/profile/', headers=headers)
    print(f'状态码: {resp.status_code}, 数据: {resp.json()}')
    
    print('\n=== 测试影厅列表 ===')
    resp = requests.get(f'{BASE}/api/halls/', headers=headers)
    print(f'状态码: {resp.status_code}, 影厅数量: {len(resp.json())}')
    for hall in resp.json()[:2]:
        print(f"  - {hall['hall_code']}: {hall['hall_name']}")
    
    print('\n=== 测试检查模板 ===')
    resp = requests.get(f'{BASE}/api/templates/', headers=headers)
    print(f'状态码: {resp.status_code}, 模板数量: {len(resp.json())}')
    
    print('\n=== 测试创建巡检单 ===')
    halls = requests.get(f'{BASE}/api/halls/', headers=headers).json()
    if halls:
        hall_id = halls[0]['id']
        resp = requests.post(f'{BASE}/api/orders/create/', 
            json={'hall_id': hall_id, 'session_no': 'S001'},
            headers=headers)
        print(f'状态码: {resp.status_code}')
        if resp.status_code == 201:
            print(f"巡检单创建成功: ID={resp.json()['id']}")
            
            print('\n=== 测试提交自检 ===')
            order_id = resp.json()['id']
            resp = requests.post(f'{BASE}/api/orders/{order_id}/self-check/',
                json={
                    'self_check_result': True,
                    'brightness': 85,
                    'sound_channels': 'left,right,center',
                    'film_source_verified': True,
                    'cooling_status': 'normal'
                },
                headers=headers)
            print(f'状态码: {resp.status_code}')
            print(f"当前状态: {resp.json()['status']}")
    
    print('\n=== 测试统计接口 ===')
    resp = requests.get(f'{BASE}/api/statistics/overview/', headers=headers)
    print(f'状态码: {resp.status_code}')
    data = resp.json()
    print(f"高频故障设备: {len(data['high_fault_devices'])} 条")
    print(f"待复映任务: {len(data['pending_review_tasks'])} 条")
    print(f"影厅稳定率: {len(data['hall_stability_rates'])} 条")
    
    print('\n=== 测试告警接口 ===')
    resp = requests.get(f'{BASE}/api/alerts/', headers=headers)
    print(f'状态码: {resp.status_code}, 告警数量: {len(resp.json())}')
    
    print('\n=== 测试列表检索 ===')
    resp = requests.get(f'{BASE}/api/orders/?status=pending_review', headers=headers)
    print(f'状态码: {resp.status_code}')
    print(f"待复映巡检单数量: {resp.json()['total']}")
    
    print('\n=== 所有测试完成 ===')
else:
    print(f'登录失败: {resp.text}')
