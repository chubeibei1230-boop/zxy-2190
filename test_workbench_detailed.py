import requests
import json

BASE = 'http://127.0.0.1:8151'

def login(username, password):
    resp = requests.post(f'{BASE}/api/token/', json={'username': username, 'password': password})
    if resp.status_code == 200:
        token = resp.json()['access']
        return {'Authorization': f'Bearer {token}'}
    print(f'登录失败 ({username}): {resp.text}')
    return None

def test_detailed_filters(headers, role_name):
    print(f'\n{"="*60}')
    print(f'详细过滤测试 - 角色: {role_name}')
    print(f'{"="*60}')
    
    print(f'\n--- 测试按影厅过滤 (hall_id=1) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?hall_id=1', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"影厅1待办数量: {data['total']}")
    
    print(f'\n--- 测试按状态过滤 (status=pending_review) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?status=pending_review', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"待复映状态待办数量: {data['total']}")
    
    print(f'\n--- 测试多条件过滤 (hall_id=1, fault_level=high) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?hall_id=1&fault_level=high', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"影厅1高等级故障待办数量: {data['total']}")
    
    print(f'\n--- 测试已催办分类 ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?category=reminded', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"已催办数量: {data['total']}")
        if data['items']:
            item = data['items'][0]
            print(f"  第一条催办: {item['title']}")
            print(f"    催办次数: {item['reminder_count']}")
    
    print(f'\n--- 测试已超时升级分类 ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?category=escalated', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"已超时升级数量: {data['total']}")
        if data['items']:
            item = data['items'][0]
            print(f"  第一条超时: {item['title']}")
            print(f"    超时原因: {item.get('escalation_reason', 'N/A')}")
    
    print(f'\n--- 测试列表项详情链接是否正确 ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?page_size=3', headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        for item in data['items']:
            print(f"  [{item['category_label']}] ID={item['id']}, type={item['type']}, detail_url={item['detail_url']}")
            
            detail_resp = requests.get(f'{BASE}{item["detail_url"]}', headers=headers)
            status = '✓' if detail_resp.status_code == 200 else '✗'
            print(f"    详情链接可访问: {status} (状态码: {detail_resp.status_code})")

if __name__ == '__main__':
    print('=== 我的待办工作台 详细过滤测试 ===')
    
    print(f'\n{"#"*60}')
    print('# 管理员视角 (全量数据)')
    print(f'{"#"*60}')
    admin_headers = login('admin', 'admin123456')
    if admin_headers:
        test_detailed_filters(admin_headers, '管理员')
    
    print(f'\n{"#"*60}')
    print('# 放映员视角 (仅自己相关)')
    print(f'{"#"*60}')
    proj_headers = login('projectionist1', 'proj123456')
    if proj_headers:
        test_detailed_filters(proj_headers, '放映员')
    
    print(f'\n{"#"*60}')
    print('# 技术复核员视角 (待复核或相关)')
    print(f'{"#"*60}')
    reviewer_headers = login('reviewer1', 'review123456')
    if reviewer_headers:
        test_detailed_filters(reviewer_headers, '技术复核员')
    
    print(f'\n{"="*60}')
    print('所有详细测试完成')
    print(f'{"="*60}')
