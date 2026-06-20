from inspection.duckdb_db import dict_fetch_one, dict_fetch_all, execute_update, insert_returning_id
from datetime import datetime, timedelta
from django.conf import settings


class HallService:
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    ALLOWED_UPDATE_FIELDS = {
        'hall_code', 'hall_name', 'projector_model', 'server_code',
        'responsible_person', 'review_time_limit', 'status'
    }

    @staticmethod
    def list_all():
        return dict_fetch_all("SELECT * FROM halls WHERE status = 'active' ORDER BY hall_code")

    @staticmethod
    def get_by_id(hall_id):
        return dict_fetch_one("SELECT * FROM halls WHERE id = ?", [hall_id])

    @staticmethod
    def get_by_code(hall_code):
        return dict_fetch_one("SELECT * FROM halls WHERE hall_code = ?", [hall_code])

    @staticmethod
    def create(hall_code, hall_name, projector_model, server_code, responsible_person=None, review_time_limit=24):
        new_id = insert_returning_id(
            """INSERT INTO halls (hall_code, hall_name, projector_model, server_code, responsible_person, review_time_limit, status)
               VALUES (?, ?, ?, ?, ?, ?, 'active') RETURNING id""",
            [hall_code, hall_name, projector_model, server_code, responsible_person, review_time_limit]
        )
        return HallService.get_by_id(new_id)

    @staticmethod
    def update(hall_id, **kwargs):
        fields = []
        params = []
        for key, value in kwargs.items():
            if key not in HallService.ALLOWED_UPDATE_FIELDS:
                continue
            if value is not None:
                fields.append(f"{key} = ?")
                params.append(value)
        if not fields:
            return HallService.get_by_id(hall_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(hall_id)
        execute_update(f"UPDATE halls SET {', '.join(fields)} WHERE id = ?", params)
        return HallService.get_by_id(hall_id)

    @staticmethod
    def delete(hall_id):
        execute_update("UPDATE halls SET status = 'inactive', updated_at = CURRENT_TIMESTAMP WHERE id = ?", [hall_id])
        return True


class TemplateService:
    ALLOWED_UPDATE_FIELDS = {
        'template_name', 'template_type', 'check_items',
        'brightness_min', 'sound_channels'
    }
    @staticmethod
    def list_all():
        return dict_fetch_all("SELECT * FROM inspection_templates ORDER BY id")

    @staticmethod
    def get_by_id(template_id):
        return dict_fetch_one("SELECT * FROM inspection_templates WHERE id = ?", [template_id])

    @staticmethod
    def create(template_name, template_type, check_items=None, brightness_min=80, sound_channels=None):
        new_id = insert_returning_id(
            """INSERT INTO inspection_templates (template_name, template_type, check_items, brightness_min, sound_channels)
               VALUES (?, ?, ?, ?, ?) RETURNING id""",
            [template_name, template_type, check_items, brightness_min, sound_channels]
        )
        return TemplateService.get_by_id(new_id)

    @staticmethod
    def update(template_id, **kwargs):
        fields = []
        params = []
        for key, value in kwargs.items():
            if key not in TemplateService.ALLOWED_UPDATE_FIELDS:
                continue
            if value is not None:
                fields.append(f"{key} = ?")
                params.append(value)
        if not fields:
            return TemplateService.get_by_id(template_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        execute_update(f"UPDATE inspection_templates SET {', '.join(fields)} WHERE id = ?", params)
        return TemplateService.get_by_id(template_id)

    @staticmethod
    def delete(template_id):
        execute_update("DELETE FROM inspection_templates WHERE id = ?", [template_id])
        return True


class InspectionOrderService:
    STATUS_PENDING_CHECK = 'pending_check'
    STATUS_CHECKING = 'checking'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_FAULT_HANDLING = 'fault_handling'
    STATUS_READY = 'ready'
    STATUS_SUSPENDED = 'suspended'

    FAULT_LEVEL_LOW = 'low'
    FAULT_LEVEL_MEDIUM = 'medium'
    FAULT_LEVEL_HIGH = 'high'
    FAULT_LEVEL_CRITICAL = 'critical'

    OPEN_STATUSES = [STATUS_PENDING_CHECK, STATUS_CHECKING, STATUS_PENDING_REVIEW, STATUS_FAULT_HANDLING]

    @staticmethod
    def check_open_order_exists(hall_id, session_no):
        placeholders = ','.join(['?'] * len(InspectionOrderService.OPEN_STATUSES))
        result = dict_fetch_one(
            f"""SELECT id, status FROM inspection_orders 
               WHERE hall_id = ? AND session_no = ? AND status IN ({placeholders})
               LIMIT 1""",
            [hall_id, session_no] + InspectionOrderService.OPEN_STATUSES
        )
        return result is not None

    @staticmethod
    def create(hall_id, session_no, template_id=None, projectionist_id=None, projectionist_name=None):
        hall = HallService.get_by_id(hall_id)
        if not hall:
            raise ValueError("影厅不存在")

        if InspectionOrderService.check_open_order_exists(hall_id, session_no):
            raise ValueError("该影厅该场次已存在未关闭的巡检单")

        review_deadline = None
        if hall.get('review_time_limit'):
            review_deadline = datetime.now() + timedelta(hours=hall['review_time_limit'])

        new_id = insert_returning_id(
            """INSERT INTO inspection_orders 
               (hall_id, hall_code, session_no, status, template_id, projectionist_id, projectionist_name, review_deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [hall_id, hall['hall_code'], session_no, InspectionOrderService.STATUS_PENDING_CHECK,
             template_id, projectionist_id, projectionist_name, review_deadline]
        )
        
        return InspectionOrderService.get_by_id(new_id)

    @staticmethod
    def get_by_id(order_id):
        order = dict_fetch_one("SELECT * FROM inspection_orders WHERE id = ?", [order_id])
        if order:
            faults = FaultService.get_by_order_id(order_id)
            order['fault_records'] = faults
            closed_count = sum(1 for f in faults if f.get('closed_loop'))
            total_count = len(faults)
            if total_count > 0:
                order['fault_closed_loop_count'] = closed_count
                order['fault_total_count'] = total_count
                order['fault_all_closed'] = closed_count == total_count
                order['fault_closed_loop_rate'] = round(closed_count / total_count * 100, 2)
            else:
                order['fault_closed_loop_count'] = 0
                order['fault_total_count'] = 0
                order['fault_all_closed'] = True
                order['fault_closed_loop_rate'] = 0.0

            reminder_summary = ReminderService.get_reminder_summary('order', order_id)
            escalation_summary = EscalationService.get_escalation_summary('order', order_id)
            order['reminder_info'] = reminder_summary
            order['escalation_info'] = escalation_summary

            reminders = ReminderService.list_by_target('order', order_id)
            order['reminder_records'] = reminders
        return order

    @staticmethod
    def list(filters=None, page=1, page_size=20):
        sql = "SELECT * FROM inspection_orders WHERE 1=1"
        count_sql = "SELECT COUNT(*) as cnt FROM inspection_orders WHERE 1=1"
        params = []
        
        if filters:
            if filters.get('hall_id'):
                sql += " AND hall_id = ?"
                count_sql += " AND hall_id = ?"
                params.append(filters['hall_id'])
            if filters.get('hall_code'):
                sql += " AND hall_code LIKE ?"
                count_sql += " AND hall_code LIKE ?"
                params.append(f"%{filters['hall_code']}%")
            if filters.get('projector_model'):
                sql += " AND hall_id IN (SELECT id FROM halls WHERE projector_model = ?)"
                count_sql += " AND hall_id IN (SELECT id FROM halls WHERE projector_model = ?)"
                params.append(filters['projector_model'])
            if filters.get('responsible_person'):
                sql += " AND hall_id IN (SELECT id FROM halls WHERE responsible_person = ?)"
                count_sql += " AND hall_id IN (SELECT id FROM halls WHERE responsible_person = ?)"
                params.append(filters['responsible_person'])
            if filters.get('status'):
                sql += " AND status = ?"
                count_sql += " AND status = ?"
                params.append(filters['status'])
            if filters.get('fault_level'):
                sql += " AND fault_level = ?"
                count_sql += " AND fault_level = ?"
                params.append(filters['fault_level'])
            if filters.get('start_date'):
                sql += " AND created_at >= ?"
                count_sql += " AND created_at >= ?"
                params.append(filters['start_date'])
            if filters.get('end_date'):
                sql += " AND created_at <= ?"
                count_sql += " AND created_at <= ?"
                params.append(filters['end_date'])
        
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        total = dict_fetch_one(count_sql, params[:-2])['cnt'] if params[:-2] else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(sql, params)

        for item in items:
            reminder_summary = ReminderService.get_reminder_summary('order', item['id'])
            escalation_summary = EscalationService.get_escalation_summary('order', item['id'])
            item['reminder_info'] = reminder_summary
            item['escalation_info'] = escalation_summary
        
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    @staticmethod
    def submit_self_check(order_id, self_check_result, brightness=None, sound_channels=None,
                          film_source_verified=None, cooling_status=None, fault_description=None,
                          fault_level=None, temp_solution=None):
        order = InspectionOrderService.get_by_id(order_id)
        if not order:
            raise ValueError("巡检单不存在")
        
        if order['status'] not in [InspectionOrderService.STATUS_PENDING_CHECK, InspectionOrderService.STATUS_CHECKING]:
            raise ValueError("当前状态不允许提交自检")
        
        has_fault = fault_description and fault_level
        if self_check_result and not has_fault and film_source_verified:
            new_status = InspectionOrderService.STATUS_PENDING_REVIEW
        elif has_fault:
            new_status = InspectionOrderService.STATUS_FAULT_HANDLING
        else:
            new_status = InspectionOrderService.STATUS_CHECKING
        
        execute_update(
            """UPDATE inspection_orders SET 
               status = ?, self_check_result = ?, brightness = ?, sound_channels = ?,
               film_source_verified = ?, cooling_status = ?, fault_description = ?,
               fault_level = ?, temp_solution = ?, submitted_at = CURRENT_TIMESTAMP,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [new_status, self_check_result, brightness, sound_channels,
             film_source_verified, cooling_status, fault_description,
             fault_level, temp_solution, order_id]
        )
        
        if has_fault:
            hall = HallService.get_by_id(order['hall_id'])
            FaultService.create_from_self_check(
                order_id=order_id,
                hall_id=order['hall_id'],
                projector_model=hall['projector_model'] if hall else None,
                fault_level=fault_level,
                description=fault_description,
                solution=temp_solution,
                handler_id=order.get('projectionist_id'),
                handler_name=order.get('projectionist_name')
            )
        
        return InspectionOrderService.get_by_id(order_id)

    @staticmethod
    def submit_review(order_id, reviewer_id, reviewer_name, recheck_result, problem_cause=None, final_conclusion=None):
        order = InspectionOrderService.get_by_id(order_id)
        if not order:
            raise ValueError("巡检单不存在")
        
        if order['status'] not in [InspectionOrderService.STATUS_PENDING_REVIEW, InspectionOrderService.STATUS_FAULT_HANDLING]:
            raise ValueError("当前状态不允许复核")
        
        if recheck_result:
            new_status = InspectionOrderService.STATUS_READY
        else:
            new_status = InspectionOrderService.STATUS_SUSPENDED
        
        execute_update(
            """UPDATE inspection_orders SET 
               status = ?, reviewer_id = ?, reviewer_name = ?, recheck_result = ?,
               problem_cause = ?, final_conclusion = ?, reviewed_at = CURRENT_TIMESTAMP,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [new_status, reviewer_id, reviewer_name, recheck_result,
             problem_cause, final_conclusion, order_id]
        )

        EscalationService.resolve_escalation('order', order_id)
        
        return InspectionOrderService.get_by_id(order_id)

    @staticmethod
    def update_status(order_id, status):
        execute_update(
            "UPDATE inspection_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [status, order_id]
        )
        return InspectionOrderService.get_by_id(order_id)


class StatisticsService:
    @staticmethod
    def high_fault_devices(days=30, limit=10):
        start_date = datetime.now() - timedelta(days=days)
        result = dict_fetch_all(
            """SELECT projector_model, COUNT(*) as fault_count, 
               COUNT(DISTINCT hall_id) as affected_halls,
               SUM(CASE WHEN closed_loop = TRUE THEN 1 ELSE 0 END) as closed_count,
               SUM(CASE WHEN is_closed = FALSE THEN 1 ELSE 0 END) as pending_count
               FROM fault_records
               WHERE created_at >= ?
               GROUP BY projector_model
               ORDER BY fault_count DESC
               LIMIT ?""",
            [start_date, limit]
        )
        for r in result:
            total = r['fault_count']
            closed = r.get('closed_count', 0)
            r['closed_loop_rate'] = round(closed / total * 100, 2) if total > 0 else 0.0
        return result

    @staticmethod
    def pending_review_tasks(user_role=None, user_id=None):
        sql = """SELECT o.*, h.responsible_person, h.projector_model
                 FROM inspection_orders o
                 JOIN halls h ON o.hall_id = h.id
                 WHERE (o.status = 'pending_review'
                    OR (o.status = 'fault_handling' AND o.temp_solution IS NOT NULL AND o.temp_solution != ''))"""
        params = []

        if user_role == 'projectionist':
            sql += " AND o.projectionist_id = ?"
            params.append(user_id)
        elif user_role == 'reviewer':
            sql += " AND o.reviewer_id = ?"
            params.append(user_id)

        sql += " ORDER BY o.review_deadline ASC NULLS LAST, o.id DESC"

        result = dict_fetch_all(sql, params)
        for item in result:
            reminder_summary = ReminderService.get_reminder_summary('order', item['id'])
            escalation_summary = EscalationService.get_escalation_summary('order', item['id'])
            item['reminder_info'] = reminder_summary
            item['escalation_info'] = escalation_summary
        return result

    @staticmethod
    def hall_stability_rate(days=30):
        start_date = datetime.now() - timedelta(days=days)
        total_orders = dict_fetch_all(
            """SELECT hall_id, hall_code, COUNT(*) as total_count
               FROM inspection_orders
               WHERE created_at >= ?
               GROUP BY hall_id, hall_code""",
            [start_date]
        )
        
        ready_orders = dict_fetch_all(
            """SELECT hall_id, COUNT(*) as ready_count
               FROM inspection_orders
               WHERE status = 'ready' AND created_at >= ?
               GROUP BY hall_id""",
            [start_date]
        )
        
        fault_stats = dict_fetch_all(
            """SELECT hall_id, COUNT(*) as fault_total,
               SUM(CASE WHEN closed_loop = TRUE THEN 1 ELSE 0 END) as fault_closed
               FROM fault_records
               WHERE created_at >= ?
               GROUP BY hall_id""",
            [start_date]
        )
        fault_map = {f['hall_id']: f for f in fault_stats}
        
        ready_map = {r['hall_id']: r['ready_count'] for r in ready_orders}
        
        result = []
        for item in total_orders:
            total = item['total_count']
            ready = ready_map.get(item['hall_id'], 0)
            rate = (ready / total * 100) if total > 0 else 0
            entry = {
                'hall_id': item['hall_id'],
                'hall_code': item['hall_code'],
                'total_count': total,
                'ready_count': ready,
                'stability_rate': round(rate, 2)
            }
            fs = fault_map.get(item['hall_id'])
            if fs:
                ft = fs['fault_total']
                fc = fs['fault_closed']
                entry['fault_total'] = ft
                entry['fault_closed'] = ft - (ft - fc)
                entry['fault_closed_loop_rate'] = round(fc / ft * 100, 2) if ft > 0 else 0.0
            else:
                entry['fault_total'] = 0
                entry['fault_closed'] = 0
                entry['fault_closed_loop_rate'] = 0.0
            result.append(entry)
        
        return result

    @staticmethod
    def fault_closed_loop_overview(days=30):
        return FaultService.get_closed_loop_stats(days=days)

    @staticmethod
    def pending_fault_tasks(user_role=None, user_id=None):
        items = FaultService.list_pending(user_role=user_role, user_id=user_id)
        for item in items:
            reminder_summary = ReminderService.get_reminder_summary('fault', item['id'])
            escalation_summary = EscalationService.get_escalation_summary('fault', item['id'])
            item['reminder_info'] = reminder_summary
            item['escalation_info'] = escalation_summary
        return items


class AlertService:
    @staticmethod
    def check_brightness_low(hall_id, consecutive_count=3, threshold=80):
        recent = dict_fetch_all(
            """SELECT brightness FROM inspection_orders
               WHERE hall_id = ? AND brightness IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            [hall_id, consecutive_count]
        )
        
        if len(recent) < consecutive_count:
            return False
        
        return all(r['brightness'] < threshold for r in recent)

    @staticmethod
    def check_film_source_missing(hall_id, recent_count=5):
        recent = dict_fetch_all(
            """SELECT film_source_verified FROM inspection_orders
               WHERE hall_id = ?
               ORDER BY id DESC LIMIT ?""",
            [hall_id, recent_count]
        )
        
        if not recent:
            return False
        
        return any(r['film_source_verified'] is None or r['film_source_verified'] == False for r in recent)

    @staticmethod
    def check_review_timeout():
        result = dict_fetch_all(
            """SELECT * FROM inspection_orders
               WHERE status = 'pending_review' 
               AND review_deadline < CURRENT_TIMESTAMP""",
            []
        )
        return result

    @staticmethod
    def check_model_fault_concentration(model, days=7, threshold=3):
        start_date = datetime.now() - timedelta(days=days)
        count = dict_fetch_one(
            """SELECT COUNT(*) as cnt FROM fault_records
               WHERE projector_model = ? 
               AND created_at >= ?""",
            [model, start_date]
        )
        return count['cnt'] >= threshold

    @staticmethod
    def check_unreviewed_after_fix():
        grace_hours = getattr(settings, 'UNREVIEWED_GRACE_HOURS', 2)
        threshold_time = datetime.now() - timedelta(hours=grace_hours)
        result = dict_fetch_all(
            """SELECT * FROM inspection_orders
               WHERE status = 'fault_handling' 
               AND temp_solution IS NOT NULL 
               AND temp_solution != ''
               AND submitted_at IS NOT NULL
               AND submitted_at <= ?
               AND reviewed_at IS NULL""",
            [threshold_time]
        )
        return result

    @staticmethod
    def get_all_alerts():
        alerts = []

        EscalationService.check_all_escalations()

        escalated_orders = EscalationService.list_order_escalations_with_details(
            filters={'is_resolved': False}, page_size=50
        )['items']
        for esc in escalated_orders:
            alerts.append({
                'type': 'order_escalated',
                'level': 'danger',
                'message': f"【超时升级】影厅 {esc.get('hall_code')} 场次 {esc.get('session_no')} 巡检单复核超时",
                'order_id': esc['target_id'],
                'escalation_id': esc['id'],
                'escalation_reason': esc.get('escalation_reason'),
                'escalated_at': esc.get('escalated_at')
            })

        escalated_faults = EscalationService.list_fault_escalations_with_details(
            filters={'is_resolved': False}, page_size=50
        )['items']
        for esc in escalated_faults:
            alerts.append({
                'type': 'fault_escalated',
                'level': 'danger',
                'message': f"【超时升级】影厅 {esc.get('hall_code')} 场次 {esc.get('session_no')} 故障复核超时 - {esc.get('fault_level', '')}",
                'fault_id': esc['target_id'],
                'order_id': esc.get('order_id'),
                'escalation_id': esc['id'],
                'escalation_reason': esc.get('escalation_reason'),
                'escalated_at': esc.get('escalated_at')
            })
        
        timeout_orders = AlertService.check_review_timeout()
        for order in timeout_orders:
            alerts.append({
                'type': 'review_timeout',
                'level': 'warning',
                'message': f"影厅 {order['hall_code']} 场次 {order['session_no']} 复映超时",
                'order_id': order['id']
            })
        
        unreviewed = AlertService.check_unreviewed_after_fix()
        for order in unreviewed:
            alerts.append({
                'type': 'unreviewed_after_fix',
                'level': 'info',
                'message': f"影厅 {order['hall_code']} 场次 {order['session_no']} 故障处理后未复核",
                'order_id': order['id']
            })
        
        halls = HallService.list_all()
        for hall in halls:
            if AlertService.check_brightness_low(hall['id']):
                alerts.append({
                    'type': 'brightness_low',
                    'level': 'warning',
                    'message': f"影厅 {hall['hall_code']} 连续{settings.BRIGHTNESS_CONSECUTIVE_COUNT}次亮度偏低",
                    'hall_id': hall['id']
                })
        
        models = set(h['projector_model'] for h in halls)
        for model in models:
            if AlertService.check_model_fault_concentration(model):
                alerts.append({
                    'type': 'model_fault_concentration',
                    'level': 'danger',
                    'message': f"型号 {model} 近{settings.FAULT_CONCENTRATION_DAYS}天故障集中",
                    'projector_model': model
                })

        fault_alerts = FaultService.get_pending_fault_alerts()
        alerts.extend(fault_alerts)

        pending_count = FaultService.list(filters={'is_closed': False}, page_size=1)['total']
        if pending_count > 0:
            closed_loop_stats = FaultService.get_closed_loop_stats(days=7)
            alerts.append({
                'type': 'fault_summary',
                'level': 'info',
                'message': f"当前有 {pending_count} 个待处理故障，近7天闭环率 {closed_loop_stats['closed_loop_rate']}%",
                'meta': {
                    'pending_count': pending_count,
                    'closed_loop_rate': closed_loop_stats['closed_loop_rate'],
                    'total_7d': closed_loop_stats['total_faults'],
                    'closed_7d': closed_loop_stats['closed_faults']
                }
            })
        
        return alerts


class FaultService:
    STATUS_PENDING = 'pending'
    STATUS_ASSIGNED = 'assigned'
    STATUS_PROCESSING = 'processing'
    STATUS_TEMP_SOLVED = 'temp_solved'
    STATUS_REVIEWING = 'reviewing'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = {
        STATUS_PENDING: '待处理',
        STATUS_ASSIGNED: '已指派',
        STATUS_PROCESSING: '处理中',
        STATUS_TEMP_SOLVED: '临时解决',
        STATUS_REVIEWING: '复核中',
        STATUS_CLOSED: '已关闭'
    }

    ACTION_CREATE = 'create'
    ACTION_ASSIGN = 'assign'
    ACTION_ADD_PROGRESS = 'add_progress'
    ACTION_UPDATE_TEMP_SOLUTION = 'update_temp_solution'
    ACTION_SUBMIT_FOR_REVIEW = 'submit_for_review'
    ACTION_REVIEW = 'review'
    ACTION_CLOSE = 'close'
    ACTION_REOPEN = 'reopen'

    @staticmethod
    def _log_progress(fault_id, operator_id, operator_name, operator_role,
                      action_type, action_detail=None, from_status=None, to_status=None):
        insert_returning_id(
            """INSERT INTO fault_progress_logs 
               (fault_id, operator_id, operator_name, operator_role, 
                action_type, action_detail, from_status, to_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [fault_id, operator_id, operator_name, operator_role,
             action_type, action_detail, from_status, to_status]
        )

    @staticmethod
    def create_from_self_check(order_id, hall_id, projector_model, fault_level,
                               description, solution=None, handler_id=None, handler_name=None):
        new_id = insert_returning_id(
            """INSERT INTO fault_records 
               (order_id, hall_id, projector_model, fault_type, fault_level, 
                description, solution, handler_id, handler_name, processing_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [order_id, hall_id, projector_model, 'self_check_fault', fault_level,
             description, solution, handler_id, handler_name, FaultService.STATUS_PENDING]
        )
        FaultService._log_progress(
            fault_id=new_id,
            operator_id=handler_id,
            operator_name=handler_name,
            operator_role='projectionist',
            action_type=FaultService.ACTION_CREATE,
            action_detail=f"自检发现故障：{description}",
            from_status=None,
            to_status=FaultService.STATUS_PENDING
        )
        return FaultService.get_by_id(new_id)

    @staticmethod
    def get_by_id(fault_id):
        fault = dict_fetch_one("SELECT * FROM fault_records WHERE id = ?", [fault_id])
        if fault:
            fault['progress_logs'] = FaultService.get_progress_logs(fault_id)
            hall = HallService.get_by_id(fault['hall_id'])
            if hall:
                fault['hall_code'] = hall['hall_code']
                fault['hall_name'] = hall.get('hall_name', '')
                fault['responsible_person'] = hall.get('responsible_person', '')

            reminder_summary = ReminderService.get_reminder_summary('fault', fault_id)
            escalation_summary = EscalationService.get_escalation_summary('fault', fault_id)
            fault['reminder_info'] = reminder_summary
            fault['escalation_info'] = escalation_summary

            reminders = ReminderService.list_by_target('fault', fault_id)
            fault['reminder_records'] = reminders
        return fault

    @staticmethod
    def get_progress_logs(fault_id):
        return dict_fetch_all(
            """SELECT * FROM fault_progress_logs 
               WHERE fault_id = ? ORDER BY id ASC""",
            [fault_id]
        )

    @staticmethod
    def list(filters=None, page=1, page_size=20):
        sql = """SELECT f.*, h.hall_code, h.hall_name, h.responsible_person, 
                        o.session_no, o.projectionist_name as order_projectionist
                 FROM fault_records f
                 LEFT JOIN halls h ON f.hall_id = h.id
                 LEFT JOIN inspection_orders o ON f.order_id = o.id
                 WHERE 1=1"""
        count_sql = "SELECT COUNT(*) as cnt FROM fault_records f WHERE 1=1"
        params = []
        count_params = []

        if filters:
            if filters.get('hall_id'):
                sql += " AND f.hall_id = ?"
                count_sql += " AND f.hall_id = ?"
                params.append(filters['hall_id'])
                count_params.append(filters['hall_id'])
            if filters.get('fault_level'):
                sql += " AND f.fault_level = ?"
                count_sql += " AND f.fault_level = ?"
                params.append(filters['fault_level'])
                count_params.append(filters['fault_level'])
            if filters.get('processing_status'):
                sql += " AND f.processing_status = ?"
                count_sql += " AND f.processing_status = ?"
                params.append(filters['processing_status'])
                count_params.append(filters['processing_status'])
            if filters.get('is_closed') is not None:
                sql += " AND f.is_closed = ?"
                count_sql += " AND f.is_closed = ?"
                params.append(filters['is_closed'])
                count_params.append(filters['is_closed'])
            if filters.get('assigned_to_id'):
                sql += " AND f.assigned_to_id = ?"
                count_sql += " AND f.assigned_to_id = ?"
                params.append(filters['assigned_to_id'])
                count_params.append(filters['assigned_to_id'])
            if filters.get('handler_id'):
                sql += " AND f.handler_id = ?"
                count_sql += " AND f.handler_id = ?"
                params.append(filters['handler_id'])
                count_params.append(filters['handler_id'])
            if filters.get('start_date'):
                sql += " AND f.created_at >= ?"
                count_sql += " AND f.created_at >= ?"
                params.append(filters['start_date'])
                count_params.append(filters['start_date'])
            if filters.get('end_date'):
                sql += " AND f.created_at <= ?"
                count_sql += " AND f.created_at <= ?"
                params.append(filters['end_date'])
                count_params.append(filters['end_date'])
            if filters.get('order_id'):
                sql += " AND f.order_id = ?"
                count_sql += " AND f.order_id = ?"
                params.append(filters['order_id'])
                count_params.append(filters['order_id'])

        sql += " ORDER BY f.is_closed ASC, f.id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        total = dict_fetch_one(count_sql, count_params)['cnt'] if count_params else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(sql, params)

        for item in items:
            reminder_summary = ReminderService.get_reminder_summary('fault', item['id'])
            escalation_summary = EscalationService.get_escalation_summary('fault', item['id'])
            item['reminder_info'] = reminder_summary
            item['escalation_info'] = escalation_summary

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    @staticmethod
    def list_pending(user_role=None, user_id=None):
        filters = {'is_closed': False}
        result = FaultService.list(filters=filters, page_size=100)
        items = result['items']

        if user_role == 'projectionist' and user_id:
            items = [f for f in items if f.get('assigned_to_id') == user_id or f.get('handler_id') == user_id]
        elif user_role == 'reviewer':
            items = [f for f in items if f['processing_status'] in [
                FaultService.STATUS_TEMP_SOLVED,
                FaultService.STATUS_REVIEWING
            ]]

        return items

    @staticmethod
    def assign_fault(fault_id, assigned_to_id, assigned_to_name, operator_id, operator_name):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法指派")

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_ASSIGNED

        execute_update(
            """UPDATE fault_records SET 
               assigned_to_id = ?, assigned_to_name = ?, processing_status = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [assigned_to_id, assigned_to_name, new_status, fault_id]
        )

        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role='admin',
            action_type=FaultService.ACTION_ASSIGN,
            action_detail=f"指派给 {assigned_to_name} 处理",
            from_status=old_status,
            to_status=new_status
        )

        return FaultService.get_by_id(fault_id)

    @staticmethod
    def add_progress(fault_id, progress_note, operator_id, operator_name, operator_role):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法添加进展")

        old_status = fault['processing_status']
        new_status = old_status
        if old_status == FaultService.STATUS_PENDING or old_status == FaultService.STATUS_ASSIGNED:
            new_status = FaultService.STATUS_PROCESSING

        execute_update(
            """UPDATE fault_records SET 
               latest_progress = ?, processing_status = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [progress_note, new_status, fault_id]
        )

        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role=operator_role,
            action_type=FaultService.ACTION_ADD_PROGRESS,
            action_detail=progress_note,
            from_status=old_status,
            to_status=new_status
        )

        return FaultService.get_by_id(fault_id)

    @staticmethod
    def update_temp_solution(fault_id, temp_solution, operator_id, operator_name, operator_role):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法更新解决方案")

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_TEMP_SOLVED

        execute_update(
            """UPDATE fault_records SET 
               temp_solution_updated = ?, solution = ?, processing_status = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [temp_solution, temp_solution, new_status, fault_id]
        )

        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role=operator_role,
            action_type=FaultService.ACTION_UPDATE_TEMP_SOLUTION,
            action_detail=f"补充临时解决方案：{temp_solution}",
            from_status=old_status,
            to_status=new_status
        )

        return FaultService.get_by_id(fault_id)

    @staticmethod
    def submit_for_review(fault_id, operator_id, operator_name, operator_role):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法提交复核")
        if fault['processing_status'] not in [FaultService.STATUS_TEMP_SOLVED, FaultService.STATUS_PROCESSING]:
            raise ValueError("当前状态不允许提交复核，请先补充处理进展或临时解决方案")

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_REVIEWING

        execute_update(
            """UPDATE fault_records SET 
               processing_status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [new_status, fault_id]
        )

        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role=operator_role,
            action_type=FaultService.ACTION_SUBMIT_FOR_REVIEW,
            action_detail="提交技术复核员进行复核",
            from_status=old_status,
            to_status=new_status
        )

        return FaultService.get_by_id(fault_id)

    @staticmethod
    def submit_review(fault_id, review_result, final_conclusion,
                      reviewer_id, reviewer_name):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法复核")
        if fault['processing_status'] != FaultService.STATUS_REVIEWING:
            raise ValueError("当前状态不允许复核，请先由放映员执行【提交复核】操作后再复核")

        result_text = '通过' if review_result else '不通过'
        detail = f"复核结果：{result_text}"
        if final_conclusion:
            detail += f"，最终结论：{final_conclusion}"

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_REVIEWING

        if review_result:
            new_status = FaultService.STATUS_CLOSED
            closed_loop = True
            is_closed = True

            execute_update(
                """UPDATE fault_records SET 
                   review_result = ?, final_conclusion = ?,
                   reviewer_id = ?, reviewer_name = ?,
                   reviewed_at = CURRENT_TIMESTAMP,
                   processing_status = ?, is_closed = ?, closed_loop = ?,
                   closed_by_id = ?, closed_by_name = ?, closed_at = CURRENT_TIMESTAMP,
                   resolved_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                [result_text, final_conclusion,
                 reviewer_id, reviewer_name,
                 new_status, is_closed, closed_loop,
                 reviewer_id, reviewer_name,
                 fault_id]
            )

            FaultService._sync_order_status(fault['order_id'])
        else:
            new_status = FaultService.STATUS_PROCESSING
            execute_update(
                """UPDATE fault_records SET 
                   review_result = ?, final_conclusion = ?,
                   reviewer_id = ?, reviewer_name = ?,
                   reviewed_at = CURRENT_TIMESTAMP,
                   processing_status = ?,
                   updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                [result_text, final_conclusion,
                 reviewer_id, reviewer_name,
                 new_status,
                 fault_id]
            )

        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=reviewer_id,
            operator_name=reviewer_name,
            operator_role='reviewer',
            action_type=FaultService.ACTION_REVIEW,
            action_detail=detail,
            from_status=old_status,
            to_status=new_status
        )

        if review_result:
            EscalationService.resolve_escalation('fault', fault_id)

        return FaultService.get_by_id(fault_id)

    @staticmethod
    def _sync_order_status(order_id):
        unresolved = dict_fetch_one(
            """SELECT COUNT(*) as cnt FROM fault_records 
               WHERE order_id = ? AND is_closed = FALSE""",
            [order_id]
        )
        if unresolved and unresolved['cnt'] == 0:
            order = InspectionOrderService.get_by_id(order_id)
            if order and order['status'] == InspectionOrderService.STATUS_FAULT_HANDLING:
                InspectionOrderService.update_status(
                    order_id, InspectionOrderService.STATUS_PENDING_REVIEW
                )

    @staticmethod
    def _sync_order_status_reopen(order_id):
        unresolved = dict_fetch_one(
            """SELECT COUNT(*) as cnt FROM fault_records 
               WHERE order_id = ? AND is_closed = FALSE""",
            [order_id]
        )
        if unresolved and unresolved['cnt'] > 0:
            order = InspectionOrderService.get_by_id(order_id)
            if order and order['status'] in [
                InspectionOrderService.STATUS_PENDING_REVIEW,
                InspectionOrderService.STATUS_READY,
                InspectionOrderService.STATUS_SUSPENDED
            ]:
                InspectionOrderService.update_status(
                    order_id, InspectionOrderService.STATUS_FAULT_HANDLING
                )

    @staticmethod
    def close_fault(fault_id, operator_id, operator_name, operator_role,
                    close_note=None, force=False):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭")

        normal_close_statuses = [FaultService.STATUS_REVIEWING]
        if force:
            if operator_role != 'admin':
                raise ValueError("只有管理员可以强制关闭故障")
        else:
            if fault['processing_status'] not in normal_close_statuses:
                raise ValueError(
                    "当前状态不允许关闭故障：必须先经过放映员【提交复核】后进入【复核中】状态才能正常关闭；"
                    "如需跳过流程直接关闭，请由管理员使用【强制关闭】并说明原因"
                )

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_CLOSED
        closed_loop_flag = not force

        final_note = close_note or ''
        if force:
            final_note = f"【强制关闭】{final_note or '管理员强制关闭，未经过正常复核流程'}"

        execute_update(
            """UPDATE fault_records SET 
               processing_status = ?, is_closed = TRUE, closed_loop = ?,
               closed_by_id = ?, closed_by_name = ?, closed_at = CURRENT_TIMESTAMP,
               resolved_at = CURRENT_TIMESTAMP,
               final_conclusion = COALESCE(final_conclusion, ?),
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [new_status, closed_loop_flag, operator_id, operator_name,
             final_note or '管理员关闭', fault_id]
        )

        detail = final_note or "关闭故障"
        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role=operator_role,
            action_type=FaultService.ACTION_CLOSE,
            action_detail=detail,
            from_status=old_status,
            to_status=new_status
        )

        FaultService._sync_order_status(fault['order_id'])
        return FaultService.get_by_id(fault_id)

    @staticmethod
    def reopen_fault(fault_id, operator_id, operator_name, operator_role, reason=None):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if not fault['is_closed']:
            raise ValueError("故障未关闭，无需重新打开")

        old_status = fault['processing_status']
        new_status = FaultService.STATUS_PROCESSING

        execute_update(
            """UPDATE fault_records SET 
               processing_status = ?, is_closed = FALSE, closed_loop = FALSE,
               closed_by_id = NULL, closed_by_name = NULL, closed_at = NULL,
               resolved_at = NULL,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [new_status, fault_id]
        )

        detail = reason or "重新打开故障"
        FaultService._log_progress(
            fault_id=fault_id,
            operator_id=operator_id,
            operator_name=operator_name,
            operator_role=operator_role,
            action_type=FaultService.ACTION_REOPEN,
            action_detail=detail,
            from_status=old_status,
            to_status=new_status
        )

        FaultService._sync_order_status_reopen(fault['order_id'])
        return FaultService.get_by_id(fault_id)

    @staticmethod
    def get_by_order_id(order_id):
        faults = dict_fetch_all(
            """SELECT f.*, h.hall_code, h.hall_name
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               WHERE f.order_id = ?
               ORDER BY f.id DESC""",
            [order_id]
        )
        return faults

    @staticmethod
    def get_closed_loop_stats(days=30):
        start_date = datetime.now() - timedelta(days=days)
        total = dict_fetch_one(
            "SELECT COUNT(*) as cnt FROM fault_records WHERE created_at >= ?",
            [start_date]
        )['cnt']
        closed = dict_fetch_one(
            "SELECT COUNT(*) as cnt FROM fault_records WHERE created_at >= ? AND closed_loop = TRUE",
            [start_date]
        )['cnt']
        pending = dict_fetch_one(
            "SELECT COUNT(*) as cnt FROM fault_records WHERE created_at >= ? AND is_closed = FALSE",
            [start_date]
        )['cnt']
        closed_loop_rate = (closed / total * 100) if total > 0 else 0

        by_status = dict_fetch_all(
            """SELECT processing_status, COUNT(*) as cnt 
               FROM fault_records 
               WHERE created_at >= ?
               GROUP BY processing_status""",
            [start_date]
        )

        by_level = dict_fetch_all(
            """SELECT fault_level, COUNT(*) as total,
               SUM(CASE WHEN closed_loop = TRUE THEN 1 ELSE 0 END) as closed
               FROM fault_records
               WHERE created_at >= ?
               GROUP BY fault_level""",
            [start_date]
        )

        avg_close_hours = None
        close_times = dict_fetch_all(
            """SELECT closed_at, created_at FROM fault_records 
               WHERE created_at >= ? AND closed_loop = TRUE 
               AND closed_at IS NOT NULL""",
            [start_date]
        )
        if close_times:
            total_hours = 0
            for ct in close_times:
                if ct['closed_at'] and ct['created_at']:
                    delta = ct['closed_at'] - ct['created_at']
                    total_hours += delta.total_seconds() / 3600
            avg_close_hours = round(total_hours / len(close_times), 2)

        return {
            'period_days': days,
            'total_faults': total,
            'closed_faults': closed,
            'pending_faults': pending,
            'closed_loop_rate': round(closed_loop_rate, 2),
            'avg_close_hours': avg_close_hours,
            'by_status': by_status,
            'by_level': by_level
        }

    @staticmethod
    def get_pending_fault_alerts():
        alerts = []

        pending_critical = dict_fetch_all(
            """SELECT f.*, h.hall_code, o.session_no
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               LEFT JOIN inspection_orders o ON f.order_id = o.id
               WHERE f.is_closed = FALSE AND f.fault_level = 'critical'
               ORDER BY f.created_at DESC""",
            []
        )
        for f in pending_critical:
            alerts.append({
                'type': 'critical_fault_pending',
                'level': 'danger',
                'message': f"严重故障待处理：影厅 {f['hall_code']} 场次 {f['session_no']} - {f['description'][:30]}",
                'fault_id': f['id'],
                'order_id': f['order_id'],
                'hall_id': f['hall_id']
            })

        stuck_processing = dict_fetch_all(
            """SELECT f.*, h.hall_code, o.session_no
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               LEFT JOIN inspection_orders o ON f.order_id = o.id
               WHERE f.is_closed = FALSE 
               AND f.processing_status = 'processing'
               AND f.updated_at < CURRENT_TIMESTAMP - INTERVAL 24 HOUR
               ORDER BY f.updated_at ASC""",
            []
        )
        for f in stuck_processing:
            alerts.append({
                'type': 'fault_stuck_in_processing',
                'level': 'warning',
                'message': f"故障处理超过24小时无进展：影厅 {f['hall_code']} 场次 {f['session_no']}",
                'fault_id': f['id'],
                'order_id': f['order_id'],
                'hall_id': f['hall_id']
            })

        unreviewed = dict_fetch_all(
            """SELECT f.*, h.hall_code, o.session_no
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               LEFT JOIN inspection_orders o ON f.order_id = o.id
               WHERE f.is_closed = FALSE 
               AND f.processing_status IN ('temp_solved', 'reviewing')
               AND f.updated_at < CURRENT_TIMESTAMP - INTERVAL 12 HOUR
               ORDER BY f.updated_at ASC""",
            []
        )
        for f in unreviewed:
            alerts.append({
                'type': 'fault_pending_review',
                'level': 'warning',
                'message': f"故障待复核超过12小时：影厅 {f['hall_code']} 场次 {f['session_no']}",
                'fault_id': f['id'],
                'order_id': f['order_id'],
                'hall_id': f['hall_id']
            })

        recently_closed = dict_fetch_all(
            """SELECT f.*, h.hall_code, o.session_no
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               LEFT JOIN inspection_orders o ON f.order_id = o.id
               WHERE f.is_closed = TRUE 
               AND f.closed_loop = TRUE
               AND f.closed_at IS NOT NULL
               AND f.closed_at >= CURRENT_TIMESTAMP - INTERVAL 24 HOUR
               ORDER BY f.closed_at DESC
               LIMIT 5""",
            []
        )
        for f in recently_closed:
            level = 'success'
            prefix = '故障闭环完成'
            reviewer = f.get('reviewer_name') or f.get('closed_by_name') or '系统'
            conclusion = f.get('final_conclusion') or ''
            if len(conclusion) > 20:
                conclusion = conclusion[:20] + '...'
            alerts.append({
                'type': 'fault_closed_loop',
                'level': level,
                'message': (f"{prefix}：影厅 {f['hall_code']} 场次 {f['session_no']} "
                           f"[{f.get('fault_level','')}] - 由 {reviewer} 处理完成。"
                           f"结论：{conclusion}"),
                'fault_id': f['id'],
                'order_id': f['order_id'],
                'hall_id': f['hall_id'],
                'closed_loop': f.get('closed_loop', False),
                'closed_at': f.get('closed_at'),
                'closed_by': f.get('closed_by_name'),
                'reviewer': f.get('reviewer_name')
            })

        force_closed = dict_fetch_all(
            """SELECT f.*, h.hall_code, o.session_no
               FROM fault_records f
               LEFT JOIN halls h ON f.hall_id = h.id
               LEFT JOIN inspection_orders o ON f.order_id = o.id
               WHERE f.is_closed = TRUE 
               AND f.closed_loop = FALSE
               AND f.closed_at IS NOT NULL
               AND f.closed_at >= CURRENT_TIMESTAMP - INTERVAL 72 HOUR
               ORDER BY f.closed_at DESC
               LIMIT 3""",
            []
        )
        for f in force_closed:
            alerts.append({
                'type': 'fault_force_closed',
                'level': 'warning',
                'message': (f"⚠️ 故障被强制关闭（未经过正常复核闭环）："
                           f"影厅 {f['hall_code']} 场次 {f['session_no']} "
                           f"关闭人：{f.get('closed_by_name')}。建议关注后续复检情况。"),
                'fault_id': f['id'],
                'order_id': f['order_id'],
                'hall_id': f['hall_id'],
                'closed_at': f.get('closed_at'),
                'closed_by': f.get('closed_by_name')
            })

        return alerts


class ReminderService:
    TARGET_TYPE_ORDER = 'order'
    TARGET_TYPE_FAULT = 'fault'
    REMINDER_TYPE_REVIEW = 'review'

    MIN_REMINDER_INTERVAL_MINUTES = 5

    @staticmethod
    def _check_can_remind_order(order_id):
        order = InspectionOrderService.get_by_id(order_id)
        if not order:
            raise ValueError("巡检单不存在")
        if order['status'] != InspectionOrderService.STATUS_PENDING_REVIEW:
            raise ValueError("当前状态不允许发起催办，仅待复核状态可催办")
        return order

    @staticmethod
    def _check_can_remind_fault(fault_id):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            raise ValueError("故障记录不存在")
        if fault['is_closed']:
            raise ValueError("故障已关闭，无法催办")
        if fault['processing_status'] not in [
            FaultService.STATUS_REVIEWING,
            FaultService.STATUS_TEMP_SOLVED
        ]:
            raise ValueError("当前状态不允许发起催办，仅复核中或临时解决状态可催办")
        return fault

    @staticmethod
    def _check_duplicate_reminder(target_type, target_id):
        last_reminder = dict_fetch_one(
            """SELECT * FROM review_reminders 
               WHERE target_type = ? AND target_id = ? 
               ORDER BY id DESC LIMIT 1""",
            [target_type, target_id]
        )
        if last_reminder:
            created_at = last_reminder['created_at']
            if created_at:
                delta = datetime.now() - created_at
                if delta.total_seconds() < ReminderService.MIN_REMINDER_INTERVAL_MINUTES * 60:
                    remaining = ReminderService.MIN_REMINDER_INTERVAL_MINUTES * 60 - delta.total_seconds()
                    raise ValueError(
                        f"催办过于频繁，请等待 {int(remaining)} 秒后再尝试"
                    )

    @staticmethod
    def create_order_reminder(order_id, initiator_id, initiator_name, initiator_role, reminder_note=None):
        order = ReminderService._check_can_remind_order(order_id)
        ReminderService._check_duplicate_reminder(
            ReminderService.TARGET_TYPE_ORDER, order_id
        )

        new_id = insert_returning_id(
            """INSERT INTO review_reminders 
               (target_type, target_id, reminder_type, initiator_id, initiator_name, initiator_role, reminder_note)
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [ReminderService.TARGET_TYPE_ORDER, order_id, ReminderService.REMINDER_TYPE_REVIEW,
             initiator_id, initiator_name, initiator_role, reminder_note]
        )
        return ReminderService.get_by_id(new_id)

    @staticmethod
    def create_fault_reminder(fault_id, initiator_id, initiator_name, initiator_role, reminder_note=None):
        fault = ReminderService._check_can_remind_fault(fault_id)
        ReminderService._check_duplicate_reminder(
            ReminderService.TARGET_TYPE_FAULT, fault_id
        )

        new_id = insert_returning_id(
            """INSERT INTO review_reminders 
               (target_type, target_id, reminder_type, initiator_id, initiator_name, initiator_role, reminder_note)
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            [ReminderService.TARGET_TYPE_FAULT, fault_id, ReminderService.REMINDER_TYPE_REVIEW,
             initiator_id, initiator_name, initiator_role, reminder_note]
        )
        return ReminderService.get_by_id(new_id)

    @staticmethod
    def get_by_id(reminder_id):
        return dict_fetch_one("SELECT * FROM review_reminders WHERE id = ?", [reminder_id])

    @staticmethod
    def list_by_target(target_type, target_id):
        return dict_fetch_all(
            """SELECT * FROM review_reminders 
               WHERE target_type = ? AND target_id = ? 
               ORDER BY id DESC""",
            [target_type, target_id]
        )

    @staticmethod
    def list(filters=None, page=1, page_size=20):
        sql = "SELECT * FROM review_reminders WHERE 1=1"
        count_sql = "SELECT COUNT(*) as cnt FROM review_reminders WHERE 1=1"
        params = []

        if filters:
            if filters.get('target_type'):
                sql += " AND target_type = ?"
                count_sql += " AND target_type = ?"
                params.append(filters['target_type'])
            if filters.get('reminder_type'):
                sql += " AND reminder_type = ?"
                count_sql += " AND reminder_type = ?"
                params.append(filters['reminder_type'])
            if filters.get('initiator_id'):
                sql += " AND initiator_id = ?"
                count_sql += " AND initiator_id = ?"
                params.append(filters['initiator_id'])
            if filters.get('start_date'):
                sql += " AND created_at >= ?"
                count_sql += " AND created_at >= ?"
                params.append(filters['start_date'])
            if filters.get('end_date'):
                sql += " AND created_at <= ?"
                count_sql += " AND created_at <= ?"
                params.append(filters['end_date'])

        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        count_params = params[:]
        params.extend([page_size, (page - 1) * page_size])

        total = dict_fetch_one(count_sql, count_params)['cnt'] if count_params else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(sql, params)

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    @staticmethod
    def get_reminder_summary(target_type, target_id):
        result = dict_fetch_one(
            """SELECT 
               COUNT(*) as reminder_count,
               MAX(created_at) as last_reminder_at
               FROM review_reminders 
               WHERE target_type = ? AND target_id = ?""",
            [target_type, target_id]
        )
        if result:
            return {
                'reminder_count': result['reminder_count'] or 0,
                'last_reminder_at': result['last_reminder_at'],
                'has_reminder': (result['reminder_count'] or 0) > 0
            }
        return {
            'reminder_count': 0,
            'last_reminder_at': None,
            'has_reminder': False
        }


class EscalationService:
    TARGET_TYPE_ORDER = 'order'
    TARGET_TYPE_FAULT = 'fault'
    ESCALATION_TYPE_REVIEW_TIMEOUT = 'review_timeout'

    @staticmethod
    def get_by_id(escalation_id):
        return dict_fetch_one("SELECT * FROM review_escalations WHERE id = ?", [escalation_id])

    @staticmethod
    def get_by_target(target_type, target_id):
        return dict_fetch_one(
            """SELECT * FROM review_escalations 
               WHERE target_type = ? AND target_id = ? AND is_resolved = FALSE
               ORDER BY id DESC LIMIT 1""",
            [target_type, target_id]
        )

    @staticmethod
    def list(filters=None, page=1, page_size=20):
        sql = "SELECT * FROM review_escalations WHERE 1=1"
        count_sql = "SELECT COUNT(*) as cnt FROM review_escalations WHERE 1=1"
        params = []

        if filters:
            if filters.get('target_type'):
                sql += " AND target_type = ?"
                count_sql += " AND target_type = ?"
                params.append(filters['target_type'])
            if filters.get('escalation_type'):
                sql += " AND escalation_type = ?"
                count_sql += " AND escalation_type = ?"
                params.append(filters['escalation_type'])
            if filters.get('is_resolved') is not None:
                sql += " AND is_resolved = ?"
                count_sql += " AND is_resolved = ?"
                params.append(filters['is_resolved'])
            if filters.get('start_date'):
                sql += " AND escalated_at >= ?"
                count_sql += " AND escalated_at >= ?"
                params.append(filters['start_date'])
            if filters.get('end_date'):
                sql += " AND escalated_at <= ?"
                count_sql += " AND escalated_at <= ?"
                params.append(filters['end_date'])

        sql += " ORDER BY is_resolved ASC, escalated_at DESC, id DESC LIMIT ? OFFSET ?"
        count_params = params[:]
        params.extend([page_size, (page - 1) * page_size])

        total = dict_fetch_one(count_sql, count_params)['cnt'] if count_params else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(sql, params)

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    @staticmethod
    def create_escalation(target_type, target_id, escalation_type, escalation_reason):
        existing = EscalationService.get_by_target(target_type, target_id)
        if existing:
            return existing

        new_id = insert_returning_id(
            """INSERT INTO review_escalations 
               (target_type, target_id, escalation_type, escalation_reason, escalated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) RETURNING id""",
            [target_type, target_id, escalation_type, escalation_reason]
        )
        return EscalationService.get_by_id(new_id)

    @staticmethod
    def resolve_escalation(target_type, target_id):
        escalation = EscalationService.get_by_target(target_type, target_id)
        if not escalation:
            return None
        execute_update(
            """UPDATE review_escalations SET 
               is_resolved = TRUE, resolved_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            [escalation['id']]
        )
        return EscalationService.get_by_id(escalation['id'])

    @staticmethod
    def check_order_escalation(order_id):
        order = InspectionOrderService.get_by_id(order_id)
        if not order:
            return None

        if order['status'] not in [
            InspectionOrderService.STATUS_PENDING_REVIEW,
            InspectionOrderService.STATUS_FAULT_HANDLING
        ]:
            EscalationService.resolve_escalation(
                EscalationService.TARGET_TYPE_ORDER, order_id
            )
            return None

        hall = HallService.get_by_id(order['hall_id'])
        time_limit = hall.get('review_time_limit', 24) if hall else 24

        review_start = order.get('submitted_at') or order.get('created_at')
        if not review_start:
            return None

        deadline = review_start + timedelta(hours=time_limit)
        if datetime.now() > deadline:
            reason = f"巡检单复核超时，超过影厅规定时限 {time_limit} 小时"
            return EscalationService.create_escalation(
                EscalationService.TARGET_TYPE_ORDER,
                order_id,
                EscalationService.ESCALATION_TYPE_REVIEW_TIMEOUT,
                reason
            )
        return None

    @staticmethod
    def check_fault_escalation(fault_id):
        fault = FaultService.get_by_id(fault_id)
        if not fault:
            return None

        if fault['is_closed']:
            EscalationService.resolve_escalation(
                EscalationService.TARGET_TYPE_FAULT, fault_id
            )
            return None

        if fault['processing_status'] not in [
            FaultService.STATUS_REVIEWING,
            FaultService.STATUS_TEMP_SOLVED
        ]:
            EscalationService.resolve_escalation(
                EscalationService.TARGET_TYPE_FAULT, fault_id
            )
            return None

        hall = HallService.get_by_id(fault['hall_id']) if fault.get('hall_id') else None
        time_limit = hall.get('review_time_limit', 24) if hall else 24

        review_start = fault.get('updated_at') or fault.get('created_at')
        if not review_start:
            return None

        deadline = review_start + timedelta(hours=time_limit)
        if datetime.now() > deadline:
            reason = f"故障复核超时，超过影厅规定时限 {time_limit} 小时"
            return EscalationService.create_escalation(
                EscalationService.TARGET_TYPE_FAULT,
                fault_id,
                EscalationService.ESCALATION_TYPE_REVIEW_TIMEOUT,
                reason
            )
        return None

    @staticmethod
    def check_all_escalations():
        pending_orders = dict_fetch_all(
            """SELECT id FROM inspection_orders 
               WHERE status IN ('pending_review', 'fault_handling')""",
            []
        )
        for order in pending_orders:
            try:
                EscalationService.check_order_escalation(order['id'])
            except Exception:
                pass

        pending_faults = dict_fetch_all(
            """SELECT id FROM fault_records 
               WHERE is_closed = FALSE AND processing_status IN ('reviewing', 'temp_solved')""",
            []
        )
        for fault in pending_faults:
            try:
                EscalationService.check_fault_escalation(fault['id'])
            except Exception:
                pass

    @staticmethod
    def get_escalation_summary(target_type, target_id):
        escalation = EscalationService.get_by_target(target_type, target_id)
        if escalation:
            return {
                'is_escalated': True,
                'escalation_id': escalation['id'],
                'escalation_type': escalation['escalation_type'],
                'escalation_reason': escalation['escalation_reason'],
                'escalated_at': escalation['escalated_at']
            }
        return {
            'is_escalated': False,
            'escalation_id': None,
            'escalation_type': None,
            'escalation_reason': None,
            'escalated_at': None
        }

    @staticmethod
    def list_order_escalations_with_details(filters=None, page=1, page_size=20):
        base_sql = """
            SELECT e.*, o.hall_code, o.session_no, o.status as order_status,
                   o.projectionist_name, o.reviewer_name, h.responsible_person,
                   h.review_time_limit
            FROM review_escalations e
            LEFT JOIN inspection_orders o ON e.target_id = o.id
            LEFT JOIN halls h ON o.hall_id = h.id
            WHERE e.target_type = 'order'
        """
        count_sql = """
            SELECT COUNT(*) as cnt FROM review_escalations e
            LEFT JOIN inspection_orders o ON e.target_id = o.id
            WHERE e.target_type = 'order'
        """
        params = []

        if filters:
            conditions = []
            if filters.get('is_resolved') is not None:
                conditions.append("e.is_resolved = ?")
                params.append(filters['is_resolved'])
            if filters.get('hall_id'):
                conditions.append("o.hall_id = ?")
                params.append(filters['hall_id'])
            if filters.get('hall_code'):
                conditions.append("o.hall_code LIKE ?")
                params.append(f"%{filters['hall_code']}%")

            if conditions:
                cond_str = " AND " + " AND ".join(conditions)
                base_sql += cond_str
                count_sql += cond_str

        base_sql += " ORDER BY e.is_resolved ASC, e.escalated_at DESC, e.id DESC LIMIT ? OFFSET ?"
        count_params = params[:]
        params.extend([page_size, (page - 1) * page_size])

        total = dict_fetch_one(count_sql, count_params)['cnt'] if count_params else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(base_sql, params)

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    @staticmethod
    def list_fault_escalations_with_details(filters=None, page=1, page_size=20):
        base_sql = """
            SELECT e.*, f.hall_id, f.fault_level, f.description,
                   f.processing_status as fault_status,
                   f.assigned_to_name, f.handler_name, f.reviewer_name,
                   o.session_no, h.hall_code
            FROM review_escalations e
            LEFT JOIN fault_records f ON e.target_id = f.id
            LEFT JOIN inspection_orders o ON f.order_id = o.id
            LEFT JOIN halls h ON f.hall_id = h.id
            WHERE e.target_type = 'fault'
        """
        count_sql = """
            SELECT COUNT(*) as cnt FROM review_escalations e
            LEFT JOIN fault_records f ON e.target_id = f.id
            WHERE e.target_type = 'fault'
        """
        params = []

        if filters:
            conditions = []
            if filters.get('is_resolved') is not None:
                conditions.append("e.is_resolved = ?")
                params.append(filters['is_resolved'])
            if filters.get('hall_id'):
                conditions.append("f.hall_id = ?")
                params.append(filters['hall_id'])
            if filters.get('fault_level'):
                conditions.append("f.fault_level = ?")
                params.append(filters['fault_level'])
            if filters.get('assigned_to_id'):
                conditions.append("f.assigned_to_id = ?")
                params.append(filters['assigned_to_id'])
            if filters.get('handler_id'):
                conditions.append("f.handler_id = ?")
                params.append(filters['handler_id'])

            if conditions:
                cond_str = " AND " + " AND ".join(conditions)
                base_sql += cond_str
                count_sql += cond_str

        base_sql += " ORDER BY e.is_resolved ASC, e.escalated_at DESC, e.id DESC LIMIT ? OFFSET ?"
        count_params = params[:]
        params.extend([page_size, (page - 1) * page_size])

        total = dict_fetch_one(count_sql, count_params)['cnt'] if count_params else dict_fetch_one(count_sql)['cnt']
        items = dict_fetch_all(base_sql, params)

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }
