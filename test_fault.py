import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_inspection.settings')
django.setup()

from inspection.services import HallService, InspectionOrderService

halls = HallService.list_all()
hall = halls[0]
print(f"影厅: {hall['hall_code']}")

order = InspectionOrderService.create(hall['id'], 'TEST-FAULT-001')
print(f"创建巡检单: id={order['id']}, status={order['status']}")

try:
    result = InspectionOrderService.submit_self_check(
        order_id=order['id'],
        self_check_result=False,
        brightness=65,
        sound_channels='left,right',
        film_source_verified=False,
        cooling_status='overheat',
        fault_description='放映机亮度不足，散热风扇异响',
        fault_level='high',
        temp_solution='已降低亮度，通知技术人员'
    )
    print(f"提交自检成功: status={result['status']}")
except Exception as e:
    print(f"提交自检失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
