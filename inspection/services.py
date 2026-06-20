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
        return dict_fetch_one("SELECT * FROM inspection_orders WHERE id = ?", [order_id])

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
            insert_returning_id(
                """INSERT INTO fault_records (order_id, hall_id, projector_model, fault_type, fault_level, description, solution)
                   VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
                [order_id, order['hall_id'], hall['projector_model'] if hall else None,
                 'self_check_fault', fault_level, fault_description, temp_solution]
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
               COUNT(DISTINCT hall_id) as affected_halls
               FROM fault_records
               WHERE created_at >= ?
               GROUP BY projector_model
               ORDER BY fault_count DESC
               LIMIT ?""",
            [start_date, limit]
        )
        return result

    @staticmethod
    def pending_review_tasks():
        result = dict_fetch_all(
            """SELECT o.*, h.responsible_person, h.projector_model
               FROM inspection_orders o
               JOIN halls h ON o.hall_id = h.id
               WHERE o.status = 'pending_review'
                  OR (o.status = 'fault_handling' AND o.temp_solution IS NOT NULL AND o.temp_solution != '')
               ORDER BY o.review_deadline ASC NULLS LAST, o.id DESC""",
            []
        )
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
        
        ready_map = {r['hall_id']: r['ready_count'] for r in ready_orders}
        
        result = []
        for item in total_orders:
            total = item['total_count']
            ready = ready_map.get(item['hall_id'], 0)
            rate = (ready / total * 100) if total > 0 else 0
            result.append({
                'hall_id': item['hall_id'],
                'hall_code': item['hall_code'],
                'total_count': total,
                'ready_count': ready,
                'stability_rate': round(rate, 2)
            })
        
        return result


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
        
        return alerts
