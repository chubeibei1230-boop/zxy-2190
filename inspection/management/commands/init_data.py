from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inspection.services import HallService, TemplateService, InspectionOrderService
from datetime import datetime, timedelta


User = get_user_model()


class Command(BaseCommand):
    help = '初始化系统基础数据'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化数据...')
        
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@cinema.com',
                password='admin123456',
                role='admin',
                real_name='系统管理员'
            )
            self.stdout.write(self.style.SUCCESS('创建管理员账号: admin / admin123456'))
        
        if not User.objects.filter(username='projectionist1').exists():
            User.objects.create_user(
                username='projectionist1',
                password='proj123456',
                role='projectionist',
                real_name='张放映',
                phone='13800138001'
            )
            self.stdout.write(self.style.SUCCESS('创建放映员账号: projectionist1 / proj123456'))
        
        if not User.objects.filter(username='reviewer1').exists():
            User.objects.create_user(
                username='reviewer1',
                password='review123456',
                role='reviewer',
                real_name='李复核',
                phone='13800138002'
            )
            self.stdout.write(self.style.SUCCESS('创建复核员账号: reviewer1 / review123456'))
        
        halls = HallService.list_all()
        if not halls:
            hall_data = [
                ('H01', '1号影厅', 'Barco DP2K-20C', 'SVR-001', '张放映', 24),
                ('H02', '2号影厅', 'Barco DP2K-20C', 'SVR-002', '王放映', 24),
                ('H03', '3号影厅', 'Christie CP2220', 'SVR-003', '李放映', 24),
                ('H04', '4号影厅', 'Christie CP2220', 'SVR-004', '赵放映', 24),
                ('H05', '5号影厅', 'NEC NC900C', 'SVR-005', '张放映', 48),
            ]
            for code, name, model, server, person, limit in hall_data:
                HallService.create(code, name, model, server, person, limit)
            self.stdout.write(self.style.SUCCESS('创建5个影厅数据'))
        
        templates = TemplateService.list_all()
        if not templates:
            TemplateService.create(
                '标准开机检查模板',
                'standard',
                '电源检查,光路检查,散热检查,音频检查',
                80,
                '左,右,中,左环绕,右环绕,低音'
            )
            TemplateService.create(
                'IMAX专用检查模板',
                'imax',
                '电源检查,双机对齐,亮度校准,3D设备检查',
                90,
                '左,右,中,左环绕,右环绕,左后环绕,右后环绕,低音'
            )
            self.stdout.write(self.style.SUCCESS('创建2个检查模板'))
        
        self.stdout.write(self.style.SUCCESS('数据初始化完成!'))
