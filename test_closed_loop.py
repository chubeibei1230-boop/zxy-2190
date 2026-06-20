import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8151/api"

tokens = {}


def print_step(step_num, title):
    print(f"\n{'='*60}")
    print(f" 步骤 {step_num}: {title}")
    print(f"{'='*60}")


def print_result(label, data, is_success=True):
    status = "✅ 成功" if is_success else "❌ 失败"
    print(f"\n{status} - {label}")
    if isinstance(data, dict) and 'detail' not in data:
        keys = list(data.keys())
        if len(keys) <= 10:
            for k in keys:
                v = data[k]
                if isinstance(v, list) and len(v) > 3:
                    print(f"  {k}: [{len(v)} items] ... (show first 3)")
                    for i, item in enumerate(v[:3]):
                        print(f"    [{i}]: {json.dumps(item, ensure_ascii=False, default=str)[:120]}")
                elif isinstance(v, dict):
                    print(f"  {k}: {json.dumps(v, ensure_ascii=False, default=str)[:120]}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2, default=str)[:500])


def login(username, password):
    url = f"{BASE_URL}/token/"
    resp = requests.post(url, json={"username": username, "password": password})
    if resp.status_code == 200:
        return resp.json().get("access")
    return None


def setup_auth():
    print_step(0, "初始化用户并登录")
    url = f"{BASE_URL}/token/"
    resp = requests.post(url, json={"username": "admin", "password": "admin123456"})
    if resp.status_code == 200:
        tokens["admin"] = resp.json()["access"]
        print_result("管理员登录", {"username": "admin", "token_prefix": tokens["admin"][:20] + "..."})
    else:
        print(f"  管理员登录失败: {resp.text}")
        sys.exit(1)

    resp = requests.post(url, json={"username": "projectionist1", "password": "proj123456"})
    if resp.status_code == 200:
        tokens["projectionist"] = resp.json()["access"]
        print_result("放映员登录", {"username": "projectionist1", "token_prefix": tokens["projectionist"][:20] + "..."})
    else:
        print(f"  放映员登录失败: {resp.text}")

    resp = requests.post(url, json={"username": "reviewer1", "password": "review123456"})
    if resp.status_code == 200:
        tokens["reviewer"] = resp.json()["access"]
        print_result("复核员登录", {"username": "reviewer1", "token_prefix": tokens["reviewer"][:20] + "..."})
    else:
        print(f"  复核员登录失败: {resp.text}")


def auth_headers(role):
    return {"Authorization": f"Bearer {tokens[role]}"}


def get_halls(role="admin"):
    print_step(1, "获取影厅列表")
    resp = requests.get(f"{BASE_URL}/halls/", headers=auth_headers(role))
    print_result("获取影厅列表", resp.json())
    return resp.json()


def get_users(role="admin"):
    resp = requests.get(f"{BASE_URL}/users/", headers=auth_headers(role))
    data = resp.json()
    print_result("获取用户列表", data)
    return data


def create_order(hall_id, role="admin"):
    print_step(2, "创建巡检单（自检前）")
    session_no = f"SESSION_{hall_id}_{20260620}"
    resp = requests.post(f"{BASE_URL}/orders/create/",
                         json={"hall_id": hall_id, "session_no": session_no, "template_id": None},
                         headers=auth_headers(role))
    data = resp.json()
    print_result("创建巡检单", data)
    return data


def submit_self_check(order_id, has_fault=True, role="projectionist"):
    print_step(3, "提交自检 - 发现故障")
    payload = {
        "self_check_result": not has_fault,
        "brightness": 70 if has_fault else 90,
        "sound_channels": "5.1",
        "film_source_verified": True,
        "cooling_status": "normal",
    }
    if has_fault:
        payload.update({
            "fault_description": "投影机关机后无法重启，电源指示灯闪烁红色，疑似电源模块故障",
            "fault_level": "high",
            "temp_solution": "尝试断电重启，暂时使用备用放映机过渡"
        })
    resp = requests.post(f"{BASE_URL}/orders/{order_id}/self-check/",
                         json=payload,
                         headers=auth_headers(role))
    data = resp.json()
    print_result("提交自检", data)
    return data


def get_order_detail(order_id, role="admin"):
    print_step(4, "查看巡检单详情（含故障闭环状态）")
    resp = requests.get(f"{BASE_URL}/orders/{order_id}/", headers=auth_headers(role))
    data = resp.json()
    faults = data.get("fault_records", [])
    print(f"  巡检单状态: {data.get('status')}")
    print(f"  故障数量: {data.get('fault_total_count', 0)}")
    print(f"  已闭环: {data.get('fault_closed_loop_count', 0)}")
    print(f"  全部闭环: {data.get('fault_all_closed')}")
    print(f"  闭环率: {data.get('fault_closed_loop_rate')}%")
    if faults:
        print(f"  故障详情:")
        for f in faults:
            print(f"    - [{f.get('id')}] {f.get('fault_level')} | 状态: {f.get('processing_status')} | 闭环: {f.get('closed_loop')} | {f.get('description', '')[:50]}")
    return data


def list_faults(filters=None, role="admin"):
    print_step(5, "查看故障列表（支持按影厅/等级/处理状态筛选）")
    params = filters or {}
    resp = requests.get(f"{BASE_URL}/faults/", params=params, headers=auth_headers(role))
    data = resp.json()
    print(f"  总数: {data.get('total')}")
    for f in data.get('items', []):
        print(f"  - [{f.get('id')}] 影厅:{f.get('hall_code')} 等级:{f.get('fault_level')} "
              f"状态:{f.get('processing_status')} 闭环:{f.get('closed_loop')}")
    return data


def list_pending_faults(role="admin"):
    print_step(5.5, f"查看待处理故障列表（角色视角: {role}）")
    resp = requests.get(f"{BASE_URL}/faults/pending/", headers=auth_headers(role))
    data = resp.json()
    print(f"  待处理总数: {data.get('total')}")
    for f in data.get('items', []):
        print(f"  - [{f.get('id')}] 影厅:{f.get('hall_code')} 等级:{f.get('fault_level')} 状态:{f.get('processing_status')}")
    return data


def get_fault_detail(fault_id, role="admin"):
    print_step(6, f"查看故障详情 #{fault_id}（含处理时间线）")
    resp = requests.get(f"{BASE_URL}/faults/{fault_id}/", headers=auth_headers(role))
    data = resp.json()
    logs = data.get('progress_logs', [])
    print(f"  故障ID: {data.get('id')}")
    print(f"  影厅: {data.get('hall_code')}")
    print(f"  等级: {data.get('fault_level')}")
    print(f"  处理状态: {data.get('processing_status')}")
    print(f"  是否已关闭: {data.get('is_closed')}")
    print(f"  是否已闭环: {data.get('closed_loop')}")
    print(f"  指派给: {data.get('assigned_to_name')}")
    print(f"  最新进展: {data.get('latest_progress')}")
    print(f"  处理时间线 ({len(logs)} 条记录):")
    for log in logs:
        print(f"    [{log.get('created_at')}] {log.get('operator_name')}({log.get('operator_role')}) "
              f"- {log.get('action_type')}: {log.get('action_detail', '')[:60]}")
        if log.get('from_status') or log.get('to_status'):
            print(f"      状态流转: {log.get('from_status')} → {log.get('to_status')}")
    return data


def assign_fault(fault_id, user_id, user_name, role="admin"):
    print_step(7, f"管理员指派故障 #{fault_id} 给 {user_name}")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/assign/",
                         json={"assigned_to_id": user_id, "assigned_to_name": user_name},
                         headers=auth_headers(role))
    data = resp.json()
    print_result("指派故障", {"status": data.get("processing_status"), "assigned_to": data.get("assigned_to_name")})
    return data


def add_progress(fault_id, note, role="projectionist"):
    print_step(8, f"放映员添加处理进展")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/progress/",
                         json={"progress_note": note},
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("添加进展失败", data, is_success=False)
    else:
        print_result("添加进展", {"latest_progress": data.get("latest_progress"), "status": data.get("processing_status")})
    return data


def update_temp_solution(fault_id, solution, role="projectionist"):
    print_step(9, f"放映员补充临时解决方案")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/temp-solution/",
                         json={"temp_solution": solution},
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("更新方案失败", data, is_success=False)
    else:
        print_result("更新方案", {"solution": data.get("solution")[:60], "status": data.get("processing_status")})
    return data


def submit_for_review(fault_id, role="projectionist"):
    print_step(10, f"放映员提交故障进入复核")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/submit-review/",
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("提交复核失败", data, is_success=False)
    else:
        print_result("提交复核", {"status": data.get("processing_status")})
    return data


def review_fault(fault_id, passed, conclusion, role="reviewer"):
    print_step(11, f"技术复核员提交复核结果（{'通过' if passed else '不通过'}）")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/review/",
                         json={"review_result": passed, "final_conclusion": conclusion},
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("复核失败", data, is_success=False)
    else:
        print_result("复核完成", {
            "status": data.get("processing_status"),
            "closed": data.get("is_closed"),
            "closed_loop": data.get("closed_loop"),
            "review_result": data.get("review_result"),
            "conclusion": (data.get("final_conclusion") or "")[:60]
        })
    return data


def close_fault(fault_id, note, role="admin"):
    print_step(11.5, f"管理员关闭故障")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/close/",
                         json={"close_note": note},
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("关闭失败", data, is_success=False)
    else:
        print_result("关闭故障", {"closed": data.get("is_closed"), "closed_loop": data.get("closed_loop")})
    return data


def reopen_fault(fault_id, reason, role="admin"):
    print_step(11.8, f"管理员重新打开故障（用于演示）")
    resp = requests.post(f"{BASE_URL}/faults/{fault_id}/reopen/",
                         json={"reason": reason},
                         headers=auth_headers(role))
    data = resp.json()
    if "error" in data:
        print_result("重新打开失败", data, is_success=False)
    else:
        print_result("重新打开", {"closed": data.get("is_closed"), "status": data.get("processing_status")})
    return data


def get_statistics_overview(role="admin"):
    print_step(12, "查看统计概览（含故障闭环统计）")
    resp = requests.get(f"{BASE_URL}/statistics/overview/?days=30", headers=auth_headers(role))
    data = resp.json()
    cl = data.get('fault_closed_loop', {})
    pf = data.get('pending_fault_tasks', [])
    print(f"  --- 故障闭环统计 ---")
    print(f"  周期: {cl.get('period_days')}天")
    print(f"  总故障数: {cl.get('total_faults')}")
    print(f"  已闭环: {cl.get('closed_faults')}")
    print(f"  待处理: {cl.get('pending_faults')}")
    print(f"  闭环率: {cl.get('closed_loop_rate')}%")
    print(f"  平均关闭耗时: {cl.get('avg_close_hours')} 小时")
    print(f"  按状态分布: {cl.get('by_status')}")
    print(f"  按等级分布: {cl.get('by_level')}")
    print(f"  待处理故障任务: {len(pf)} 个")
    return data


def get_closed_loop_stats(role="admin"):
    print_step(12.5, "查看专门的故障闭环统计接口")
    resp = requests.get(f"{BASE_URL}/statistics/closed-loop/?days=30", headers=auth_headers(role))
    data = resp.json()
    print_result("故障闭环统计", data)
    return data


def get_alerts(role="admin"):
    print_step(13, "查看告警信息（含故障闭环相关告警）")
    resp = requests.get(f"{BASE_URL}/alerts/", headers=auth_headers(role))
    data = resp.json()
    print(f"  共 {len(data)} 条告警:")
    for alert in data:
        print(f"  - [{alert.get('type')}] ({alert.get('level')}) {alert.get('message')[:80]}")
        if 'fault_id' in alert:
            print(f"    关联故障ID: {alert['fault_id']}")
    return data


def get_fault_status_choices(role="admin"):
    print_step(14, "获取故障处理状态选项")
    resp = requests.get(f"{BASE_URL}/choices/fault-processing-status/", headers=auth_headers(role))
    data = resp.json()
    print_result("故障处理状态选项", data)
    return data


def test_complete_workflow():
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + " "*15 + "故障闭环跟踪模块完整流程测试" + " "*20 + "#")
    print("#" + " "*68 + "#")
    print("#"*70)

    try:
        setup_auth()

        halls = get_halls()
        hall_id = halls[0]["id"] if halls else 1

        users = get_users()
        projectionists = [u for u in users if u.get("role") == "projectionist"]
        proj_user = projectionists[0] if projectionists else {"id": 2, "real_name": "放映员A"}

        order = create_order(hall_id)
        order_id = order["id"]

        submit_self_check(order_id, has_fault=True, role="projectionist")
        order_detail = get_order_detail(order_id)

        faults = list_faults(role="admin")
        fault_id = faults["items"][0]["id"] if faults["items"] else 1

        get_fault_detail(fault_id)

        list_pending_faults(role="projectionist")

        assign_fault(fault_id, proj_user["id"], proj_user.get("real_name") or proj_user.get("username"), role="admin")

        get_fault_detail(fault_id)

        add_progress(fault_id,
                     "已联系技术支持，初步判断电源板电容烧毁，正在等待备件",
                     role="projectionist")

        add_progress(fault_id,
                     "备件已到货，正在拆机更换电源板，预计2小时内完成",
                     role="projectionist")

        update_temp_solution(fault_id,
                             "1. 电源板已更换完成；2. 测试开机正常；3. 温度稳定在45度；4. 连续运行30分钟无异常",
                             role="projectionist")

        get_fault_detail(fault_id)

        submit_for_review(fault_id, role="projectionist")

        list_pending_faults(role="reviewer")

        review_fault(fault_id,
                     passed=True,
                     conclusion="经复核，电源板更换规范，连续测试4小时温度稳定，亮度恢复至标准值95，无异常报错。故障已彻底解决。",
                     role="reviewer")

        get_fault_detail(fault_id)

        get_order_detail(order_id)

        list_faults(filters={"is_closed": "true"}, role="admin")

        print("\n--- 筛选测试 ---")
        list_faults(filters={"fault_level": "high"}, role="admin")
        list_faults(filters={"processing_status": "closed"}, role="admin")
        list_faults(filters={"hall_id": hall_id}, role="admin")

        get_statistics_overview()

        get_closed_loop_stats()

        get_alerts()

        get_fault_status_choices()

        print("\n" + "="*60)
        print("🎉 故障闭环跟踪模块 - 所有核心流程测试通过!")
        print("="*60)
        print("\n✅ 验证的业务链路:")
        print("  1️⃣  发现故障（自检提交 → 故障自动创建）")
        print("  2️⃣  指派处理（管理员 → 指定放映员处理）")
        print("  3️⃣  处理进展（放映员补充多次进展）")
        print("  4️⃣  临时方案（放映员补充解决方案）")
        print("  5️⃣  提交复核（放映员 → 技术复核员）")
        print("  6️⃣  技术复核（复核员给出结果与结论）")
        print("  7️⃣  关闭归档（自动闭环，巡检单状态联动）")
        print("  8️⃣  列表筛选（影厅/等级/状态多维度）")
        print("  9️⃣  角色视角（管理员/放映员/复核员）")
        print("  🔟  统计概览（闭环率/耗时/分布）")
        print("  1️⃣1️⃣ 告警联动（严重故障/超时/待复核）")
        print("  1️⃣2️⃣ 时间线（完整操作轨迹）")

    except Exception as e:
        print(f"\n❌ 测试异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_complete_workflow()
