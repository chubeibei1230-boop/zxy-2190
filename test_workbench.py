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

def test_workbench(headers, role_name):
    print(f'\n{"="*60}')
    print(f'测试角色: {role_name}')
    print(f'{"="*60}')
    
    print(f'\n--- 测试工作台汇总 (无过滤) ---')
    resp = requests.get(f'{BASE}/api/workbench/summary/', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"待办总数: {data['total_pending']}")
        print(f"分类汇总:")
        for cat in data['categories']:
            latest = cat.get('latest_item')
            latest_info = f" - 最新: {latest['title']}" if latest else ""
            print(f"  {cat['category_label']}: {cat['count']} 条{latest_info}")
    
    print(f'\n--- 测试工作台列表 (无过滤) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"总数: {data['total']}, 页码: {data['page']}, 每页: {data['page_size']}")
        print(f"列表项 ({len(data['items'])} 条):")
        for item in data['items'][:5]:
            print(f"  [{item['category_label']}] {item['title']} - {item['status_label']}")
            print(f"    详情链接: {item['detail_url']}")
            if item.get('is_escalated'):
                print(f"    ⚠️ 已超时升级: {item.get('escalation_reason')}")
            if item.get('has_reminder'):
                print(f"    📢 已被催办 {item.get('reminder_count')} 次")
    
    print(f'\n--- 测试按分类过滤 (待复核) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?category=pending_review', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"待复核数量: {data['total']}")
    
    print(f'\n--- 测试按故障等级过滤 (严重) ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?fault_level=critical', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"严重故障待办数量: {data['total']}")
    
    print(f'\n--- 测试分页 ---')
    resp = requests.get(f'{BASE}/api/workbench/items/?page=1&page_size=5', headers=headers)
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"总数: {data['total']}, 第{data['page']}页, 每页{data['page_size']}条")

if __name__ == '__main__':
    print('=== 我的待办工作台 测试 ===')
    
    admin_headers = login('admin', 'admin123456')
    if admin_headers:
        test_workbench(admin_headers, '管理员')
    
    proj_headers = login('projectionist1', 'proj123456')
    if proj_headers:
        test_workbench(proj_headers, '放映员')
    
    reviewer_headers = login('reviewer1', 'review123456')
    if reviewer_headers:
        test_workbench(reviewer_headers, '技术复核员')
    
    print(f'\n{"="*60}')
    print('所有测试完成')
    print(f'{"="*60}')
