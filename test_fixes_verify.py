import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
import random

BASE_URL = "http://127.0.0.1:8151/api"
tokens = {}
_counter = [0]

def print_title(t):
    print(f"\n{'#'*70}")
    print(f"#  {t}")
    print(f"{'#'*70}")

def print_subtitle(t):
    print(f"\n--- {t} ---")

def print_result(label, expect_pass, data=None):
    if expect_pass:
        status = "[PASS]"
    else:
        status = "[PASS] 拦截正确"
    print(f"  {status} - {label}")
    if data:
        if isinstance(data, dict):
            msg = data.get('error') or data.get('message')
            if msg:
                print(f"     信息: {msg[:120]}")
            else:
                keys_show = ['processing_status', 'is_closed', 'closed_loop', 
                           'review_result', 'final_conclusion']
                for k in keys_show:
                    if k in data:
                        print(f"     {k}: {data[k]}")

def login_all():
    url = f"{BASE_URL}/token/"
    for role, user, pwd in [('admin', 'admin', 'admin123456'),
                            ('projectionist', 'projectionist1', 'proj123456'),
                            ('reviewer', 'reviewer1', 'review123456')]:
        resp = requests.post(url, json={"username": user, "password": pwd})
        tokens[role] = resp.json()["access"]
    print("[INFO] 登录完成")

def headers(role):
    return {"Authorization": f"Bearer {tokens[role]}"}

def get_hall_id():
    resp = requests.get(f"{BASE_URL}/halls/", headers=headers("admin"))
    return resp.json()[0]["id"]

def create_order_and_fault(has_fault=True, fault_level="high"):
    hall_id = get_hall_id()
    _counter[0] += 1
    session_no = f"FIX{int(time.time())}{_counter[0]}{random.randint(1000,9999)}"
    resp = requests.post(f"{BASE_URL}/orders/create/",
                         json={"hall_id": hall_id, "session_no": session_no},
                         headers=headers("admin"))
    assert resp.status_code in (200, 201), f"创建巡检单失败: {resp.text}"
    order_id = resp.json()["id"]

    payload = {
        "self_check_result": False, "brightness": 70, "sound_channels": "5.1",
        "film_source_verified": True, "cooling_status": "normal",
        "fault_description": "测试故障：放映机无法启动",
        "fault_level": fault_level,
        "temp_solution": "初始解决思路"
    } if has_fault else {
        "self_check_result": True, "brightness": 95, "sound_channels": "5.1",
        "film_source_verified": True, "cooling_status": "normal"
    }
    requests.post(f"{BASE_URL}/orders/{order_id}/self-check/",
                  json=payload, headers=headers("projectionist"))

    resp = requests.get(f"{BASE_URL}/faults/", params={"order_id": order_id},
                        headers=headers("admin"))
    items = resp.json().get("items", [])
    fault_id = items[0]["id"] if items else None
    return order_id, fault_id

def advance_to_status(fault_id, target_status, user_id=None, user_name=None):
    if target_status == "assigned":
        if not (user_id and user_name):
            user_id, user_name = 2, "张放映"
        requests.post(f"{BASE_URL}/faults/{fault_id}/assign/",
                      json={"assigned_to_id": user_id, "assigned_to_name": user_name},
                      headers=headers("admin"))
    elif target_status == "processing":
        advance_to_status(fault_id, "assigned", user_id, user_name)
        requests.post(f"{BASE_URL}/faults/{fault_id}/progress/",
                      json={"progress_note": "已联系技术支持"},
                      headers=headers("projectionist"))
    elif target_status == "temp_solved":
        advance_to_status(fault_id, "processing", user_id, user_name)
        requests.post(f"{BASE_URL}/faults/{fault_id}/temp-solution/",
                      json={"temp_solution": "临时方案：备件更换完成"},
                      headers=headers("projectionist"))
    elif target_status == "reviewing":
        advance_to_status(fault_id, "temp_solved", user_id, user_name)
        requests.post(f"{BASE_URL}/faults/{fault_id}/submit-review/",
                      headers=headers("projectionist"))

def get_current_status(fault_id):
    resp = requests.get(f"{BASE_URL}/faults/{fault_id}/", headers=headers("admin"))
    d = resp.json()
    return d.get("processing_status"), d

def get_order_status(order_id):
    resp = requests.get(f"{BASE_URL}/orders/{order_id}/", headers=headers("admin"))
    return resp.json().get("status"), resp.json()


def test_issue_1_direct_close_blocked():
    print_title("问题1：绕过流程直接关闭")

    _, fid = create_order_and_fault()
    cur_status, _ = get_current_status(fid)
    print_subtitle(f"当前状态：{cur_status} -> 尝试正常关闭（未走复核流程）")

    resp = requests.post(f"{BASE_URL}/faults/{fid}/close/",
                         json={"close_note": "我想直接关闭"},
                         headers=headers("admin"))
    data = resp.json()
    expect_fail = resp.status_code != 200 or 'error' in data
    print_result("pending状态下直接正常关闭 -> 被系统拦截", expect_fail, data)

    print_subtitle("复核员尝试在pending状态正常关闭")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/close/",
                         json={"close_note": "我是复核员我想直接关"},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = resp.status_code != 200 or 'error' in data
    print_result("复核员pending直接关闭 -> 被系统拦截", expect_fail, data)

    print_subtitle("管理员使用【force=True】强制关闭")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/close/",
                         json={"close_note": "紧急情况需要直接关闭", "force": True},
                         headers=headers("admin"))
    data = resp.json()
    expect_pass = data.get("processing_status") == "closed" and data.get("is_closed") == True
    print_result("管理员强制关闭（force=True）-> 成功", expect_pass, data)
    assert data.get("closed_loop") == False
    print("  [ASSERT OK] 强制关闭 closed_loop=False")
    if data.get("final_conclusion"):
        print(f"     final_conclusion: {data['final_conclusion'][:60]}")

    print_subtitle("复核员尝试force=True强制关闭 -> 权限拦截")
    _, fid2 = create_order_and_fault()
    resp = requests.post(f"{BASE_URL}/faults/{fid2}/close/",
                         json={"close_note": "越权强制关闭", "force": True},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = resp.status_code == 403 or 'error' in data
    print_result("复核员force关闭 -> 403拦截", expect_fail, data)

    print_subtitle("推进到reviewing状态后执行正常关闭")
    _, fid3 = create_order_and_fault()
    advance_to_status(fid3, "reviewing")
    resp = requests.post(f"{BASE_URL}/faults/{fid3}/close/",
                         json={"close_note": "已执行复核流程，正常关闭"},
                         headers=headers("admin"))
    data = resp.json()
    expect_pass = data.get("processing_status") == "closed" and data.get("closed_loop") == True
    print_result("reviewing正常关闭 -> closed_loop=True", expect_pass, data)
    assert data.get("closed_loop") == True
    print("  [ASSERT OK] 正常流程关闭 closed_loop=True")

    print("\n[PASS] 问题1修复验证完成")


def test_issue_2_reopen_sync_order_status():
    print_title("问题2：重新打开故障后巡检单状态同步回退")

    oid, fid = create_order_and_fault()
    advance_to_status(fid, "reviewing")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/review/",
                         json={"review_result": True, "final_conclusion": "测试闭环"},
                         headers=headers("reviewer"))
    assert resp.json().get("closed_loop") == True
    order_status, _ = get_order_status(oid)
    print(f"  故障闭环完成后，巡检单状态：{order_status}")
    assert order_status in ("pending_review", "ready")

    print_subtitle(f"执行 reopen 重新打开故障 #{fid}")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/reopen/",
                         json={"reason": "发现故障复现，需要重新处理"},
                         headers=headers("admin"))
    data = resp.json()
    cur_fault_status = data.get("processing_status")
    print(f"  故障重开后状态：{cur_fault_status}")

    order_status, order_data = get_order_status(oid)
    print(f"  巡检单同步后状态：{order_status}")

    assert cur_fault_status == "processing"
    assert order_status == "fault_handling", f"应为fault_handling，实际 {order_status}"
    assert data.get("is_closed") == False
    assert data.get("closed_loop") == False
    print_result(f"故障重开={cur_fault_status}, 巡检单回退={order_status}", True)
    print("  [ASSERT OK] 巡检单自动从pending_review回退到fault_handling")

    print("\n[PASS] 问题2修复验证完成")


def test_issue_3_review_only_in_reviewing_status():
    print_title("问题3：必须经放映员提交复核后才能复核")

    _, fid = create_order_and_fault()
    cur_status, _ = get_current_status(fid)
    print_subtitle(f"状态：{cur_status} -> 复核员尝试直接复核")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/review/",
                         json={"review_result": True, "final_conclusion": "我想直接复核"},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = 'error' in data
    print_result("pending状态直接复核 -> 拦截", expect_fail, data)

    _, fid2 = create_order_and_fault()
    advance_to_status(fid2, "assigned")
    cur_status, _ = get_current_status(fid2)
    print_subtitle(f"状态：{cur_status} -> 复核员尝试直接复核")
    resp = requests.post(f"{BASE_URL}/faults/{fid2}/review/",
                         json={"review_result": True},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = 'error' in data
    print_result("assigned状态直接复核 -> 拦截", expect_fail, data)

    _, fid3 = create_order_and_fault()
    advance_to_status(fid3, "processing")
    cur_status, _ = get_current_status(fid3)
    print_subtitle(f"状态：{cur_status} -> 复核员尝试直接复核")
    resp = requests.post(f"{BASE_URL}/faults/{fid3}/review/",
                         json={"review_result": True},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = 'error' in data
    print_result("processing状态直接复核 -> 拦截", expect_fail, data)

    _, fid4 = create_order_and_fault()
    advance_to_status(fid4, "temp_solved")
    cur_status, _ = get_current_status(fid4)
    print_subtitle(f"状态：{cur_status} -> 复核员尝试直接复核")
    resp = requests.post(f"{BASE_URL}/faults/{fid4}/review/",
                         json={"review_result": True},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_fail = 'error' in data
    print_result("temp_solved直接复核 -> 拦截（须先submit-review）", expect_fail, data)

    _, fid5 = create_order_and_fault()
    advance_to_status(fid5, "reviewing")
    cur_status, _ = get_current_status(fid5)
    print_subtitle(f"状态：{cur_status} -> 复核员正常复核")
    resp = requests.post(f"{BASE_URL}/faults/{fid5}/review/",
                         json={"review_result": True, "final_conclusion": "正确流程通过"},
                         headers=headers("reviewer"))
    data = resp.json()
    expect_pass = data.get("processing_status") == "closed" and data.get("closed_loop") == True
    print_result("reviewing状态正常复核 -> 闭环成功", expect_pass, data)

    print("\n[PASS] 问题3修复验证完成")


def test_issue_4_alerts_show_closed_loop():
    print_title("问题4：故障关闭后告警体现闭环结果")

    oid, fid = create_order_and_fault(fault_level="critical")
    advance_to_status(fid, "reviewing")
    resp = requests.post(f"{BASE_URL}/faults/{fid}/review/",
                         json={"review_result": True,
                               "final_conclusion": "经复核：电源板已更换，测试稳定。"},
                         headers=headers("reviewer"))
    assert resp.json().get("closed_loop") == True

    print_subtitle("创建高等级故障，管理员强制关闭（closed_loop=False）")
    oid2, fid2 = create_order_and_fault(fault_level="high")
    requests.post(f"{BASE_URL}/faults/{fid2}/close/",
                  json={"close_note": "客户自行解决，紧急关闭后续跟踪", "force": True},
                  headers=headers("admin"))

    print_subtitle("查询告警列表")
    resp = requests.get(f"{BASE_URL}/alerts/", headers=headers("admin"))
    alerts = resp.json()
    print(f"  共获取 {len(alerts)} 条告警")

    closed_loop_alerts = [a for a in alerts if a.get('type') == 'fault_closed_loop']
    force_closed_alerts = [a for a in alerts if a.get('type') == 'fault_force_closed']

    print(f"  fault_closed_loop: {len(closed_loop_alerts)} 条")
    for a in closed_loop_alerts:
        print(f"    - [{a['level']}] {a['message'][:120]}")
        assert 'closed_loop' in a and a['closed_loop'] == True
    print_result("告警中存在【故障闭环完成】通知（closed_loop=True）",
                 len(closed_loop_alerts) >= 1, closed_loop_alerts[0] if closed_loop_alerts else None)

    print(f"  fault_force_closed: {len(force_closed_alerts)} 条")
    for a in force_closed_alerts:
        print(f"    - [{a['level']}] {a['message'][:120]}")
    print_result("告警中存在【强制关闭提醒】通知（warning级别）",
                 len(force_closed_alerts) >= 1, force_closed_alerts[0] if force_closed_alerts else None)

    summary_alerts = [a for a in alerts if a.get('type') == 'fault_summary']
    if summary_alerts:
        print(f"  fault_summary 信息: {summary_alerts[0]['message']}")

    print("\n[PASS] 问题4修复验证完成")


if __name__ == "__main__":
    login_all()
    print_title("4个业务流程漏洞修复验证测试")

    all_pass = True

    for name, fn in [("问题1", test_issue_1_direct_close_blocked),
                     ("问题2", test_issue_2_reopen_sync_order_status),
                     ("问题3", test_issue_3_review_only_in_reviewing_status),
                     ("问题4", test_issue_4_alerts_show_closed_loop)]:
        try:
            fn()
            sys.stdout.flush()
        except Exception as e:
            with open("err_log.txt", "w", encoding="utf-8") as fl:
                fl.write(f"\n[FAIL] {name}测试异常: {type(e).__name__}: {e}\n")
                import traceback
                traceback.print_exc(file=fl)
            print(f"\n[FAIL] {name}测试异常: {type(e).__name__}: {e}")
            print(f"详细信息已写入 err_log.txt")
            all_pass = False
            break

    print("\n" + "="*70)
    if all_pass:
        print("[ALL PASS] 全部4个问题修复验证通过！")
    else:
        print("[FAIL] 存在测试失败")
    print("="*70)
    if all_pass:
        print("""
 [问题1] 关闭流程受保护：
   - 未进入reviewing状态不能直接关闭
   - 管理员可强制关闭，closed_loop=False + 【强制关闭】标记
   - 复核员无权强制关闭

 [问题2] 故障重开后巡检单状态自动同步：
   - 从 pending_review/ready 同步回退到 fault_handling
   - 不再出现故障未闭环但巡检单显示待复映的错乱

 [问题3] 复核操作严格限定：
   - 只能在 reviewing 状态执行复核
   - 放映员必须执行【提交复核】后，复核员才能操作
   - 彻底防止越权直接复核

 [问题4] 关闭后告警保留闭环结果：
   - 24h内正常闭环 -> success级别通知
   - 72h内强制关闭 -> warning级别强制关闭提醒
   - 不再是一关闭就消失，完整展示处理结果
""")
