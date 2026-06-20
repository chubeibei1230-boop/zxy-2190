from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from inspection.permissions import IsAdmin, IsProjectionist, IsReviewer, IsAdminOrProjectionist, IsAdminOrReviewer
from inspection.serializers import (
    UserSerializer, UserCreateSerializer,
    HallSerializer, TemplateSerializer,
    InspectionOrderCreateSerializer, SelfCheckSubmitSerializer,
    ReviewSubmitSerializer, InspectionOrderSerializer,
    OrderListFilterSerializer,
    FaultListFilterSerializer, FaultAssignSerializer, FaultProgressSerializer,
    FaultTempSolutionSerializer, FaultReviewSerializer, FaultCloseSerializer,
    FaultReopenSerializer, FaultSerializer,
    ReminderSerializer, ReminderCreateSerializer, ReminderListFilterSerializer,
    EscalationSerializer, EscalationListFilterSerializer,
    ReminderSummarySerializer, EscalationSummarySerializer
)
from inspection.services import (
    HallService, TemplateService, InspectionOrderService,
    StatisticsService, AlertService, FaultService,
    ReminderService, EscalationService
)


class UserRegisterView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class HallListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        halls = HallService.list_all()
        return Response(halls)

    def post(self, request):
        serializer = HallSerializer(data=request.data)
        if serializer.is_valid():
            hall = HallService.create(**serializer.validated_data)
            return Response(hall, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HallDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request, pk):
        hall = HallService.get_by_id(pk)
        if not hall:
            return Response({'error': '影厅不存在'}, status=status.HTTP_404_NOT_FOUND)
        return Response(hall)

    def put(self, request, pk):
        hall = HallService.get_by_id(pk)
        if not hall:
            return Response({'error': '影厅不存在'}, status=status.HTTP_404_NOT_FOUND)
        serializer = HallSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        updated = HallService.update(pk, **serializer.validated_data)
        return Response(updated)

    def delete(self, request, pk):
        hall = HallService.get_by_id(pk)
        if not hall:
            return Response({'error': '影厅不存在'}, status=status.HTTP_404_NOT_FOUND)
        HallService.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplateListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request):
        templates = TemplateService.list_all()
        return Response(templates)

    def post(self, request):
        serializer = TemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = TemplateService.create(**serializer.validated_data)
            return Response(template, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TemplateDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get(self, request, pk):
        template = TemplateService.get_by_id(pk)
        if not template:
            return Response({'error': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)
        return Response(template)

    def put(self, request, pk):
        template = TemplateService.get_by_id(pk)
        if not template:
            return Response({'error': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TemplateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        updated = TemplateService.update(pk, **serializer.validated_data)
        return Response(updated)

    def delete(self, request, pk):
        template = TemplateService.get_by_id(pk)
        if not template:
            return Response({'error': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)
        TemplateService.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderCreateView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request):
        serializer = InspectionOrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = InspectionOrderService.create(
                hall_id=serializer.validated_data['hall_id'],
                session_no=serializer.validated_data['session_no'],
                template_id=serializer.validated_data.get('template_id'),
                projectionist_id=request.user.id,
                projectionist_name=request.user.real_name or request.user.username
            )
            return Response(order, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = InspectionOrderService.get_by_id(pk)
        if not order:
            return Response({'error': '巡检单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            if order.get('projectionist_id') != request.user.id:
                return Response({'error': '您无权查看该巡检单详情'},
                                status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'reviewer':
            reviewer_id = order.get('reviewer_id')
            if reviewer_id is not None and reviewer_id != request.user.id:
                return Response({'error': '您无权查看该巡检单详情'},
                                status=status.HTTP_403_FORBIDDEN)

        return Response(order)


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = OrderListFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        filters = {}
        for key in ['hall_id', 'hall_code', 'projector_model', 'responsible_person',
                   'status', 'fault_level', 'start_date', 'end_date']:
            if key in serializer.validated_data and serializer.validated_data[key] is not None:
                filters[key] = serializer.validated_data[key]
        
        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('page_size', 20)
        
        result = InspectionOrderService.list(filters=filters, page=page, page_size=page_size)
        return Response(result)


class SelfCheckSubmitView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        order = InspectionOrderService.get_by_id(pk)
        if not order:
            return Response({'error': '巡检单不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = SelfCheckSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = InspectionOrderService.submit_self_check(
                order_id=pk,
                **serializer.validated_data
            )
            return Response(order)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewSubmitView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request, pk):
        order = InspectionOrderService.get_by_id(pk)
        if not order:
            return Response({'error': '巡检单不存在'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ReviewSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = InspectionOrderService.submit_review(
                order_id=pk,
                reviewer_id=request.user.id,
                reviewer_name=request.user.real_name or request.user.username,
                **serializer.validated_data
            )
            return Response(order)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StatisticsHighFaultDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        data = StatisticsService.high_fault_devices(days=days, limit=limit)
        return Response(data)


class StatisticsPendingReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = StatisticsService.pending_review_tasks(
            user_role=request.user.role,
            user_id=request.user.id
        )
        return Response(data)


class StatisticsHallStabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        data = StatisticsService.hall_stability_rate(days=days)
        return Response(data)


class StatisticsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        return Response({
            'high_fault_devices': StatisticsService.high_fault_devices(days=days, limit=10),
            'pending_review_tasks': StatisticsService.pending_review_tasks(
                user_role=request.user.role,
                user_id=request.user.id
            ),
            'hall_stability_rates': StatisticsService.hall_stability_rate(days=days),
            'fault_closed_loop': StatisticsService.fault_closed_loop_overview(days=days),
            'pending_fault_tasks': StatisticsService.pending_fault_tasks(
                user_role=request.user.role,
                user_id=request.user.id
            )
        })


class AlertListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alerts = AlertService.get_all_alerts()
        return Response(alerts)


class OrderStatusChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'pending_check': '待检查',
            'checking': '检查中',
            'pending_review': '待复映',
            'fault_handling': '故障处理中',
            'ready': '可放映',
            'suspended': '暂停放映'
        })


class FaultLevelChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'low': '低',
            'medium': '中',
            'high': '高',
            'critical': '严重'
        })


class RoleChoicesView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            'admin': '管理员',
            'projectionist': '放映员',
            'reviewer': '技术复核员'
        })


class FaultProcessingStatusChoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(FaultService.STATUS_CHOICES)


class FaultListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FaultListFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = {}
        for key in ['hall_id', 'fault_level', 'processing_status', 'is_closed',
                    'assigned_to_id', 'handler_id', 'order_id', 'start_date', 'end_date']:
            if key in serializer.validated_data and serializer.validated_data[key] is not None:
                filters[key] = serializer.validated_data[key]

        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('page_size', 20)

        result = FaultService.list(filters=filters, page=page, page_size=page_size)
        return Response(result)


class FaultPendingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = FaultService.list_pending(
            user_role=request.user.role,
            user_id=request.user.id
        )
        return Response({
            'total': len(items),
            'items': items
        })


class FaultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)
        return Response(fault)


class FaultAssignView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FaultAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            fault = FaultService.assign_fault(
                fault_id=pk,
                assigned_to_id=serializer.validated_data['assigned_to_id'],
                assigned_to_name=serializer.validated_data['assigned_to_name'],
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultAddProgressView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            assigned_id = fault.get('assigned_to_id')
            handler_id = fault.get('handler_id')
            if assigned_id != request.user.id and handler_id != request.user.id:
                return Response({'error': '您不是该故障的处理人员，无权添加进展'},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = FaultProgressSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            fault = FaultService.add_progress(
                fault_id=pk,
                progress_note=serializer.validated_data['progress_note'],
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username,
                operator_role=request.user.role
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultUpdateTempSolutionView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            assigned_id = fault.get('assigned_to_id')
            handler_id = fault.get('handler_id')
            if assigned_id != request.user.id and handler_id != request.user.id:
                return Response({'error': '您不是该故障的处理人员，无权更新解决方案'},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = FaultTempSolutionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            fault = FaultService.update_temp_solution(
                fault_id=pk,
                temp_solution=serializer.validated_data['temp_solution'],
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username,
                operator_role=request.user.role
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultSubmitForReviewView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            assigned_id = fault.get('assigned_to_id')
            handler_id = fault.get('handler_id')
            if assigned_id != request.user.id and handler_id != request.user.id:
                return Response({'error': '您不是该故障的处理人员，无权提交复核'},
                                status=status.HTTP_403_FORBIDDEN)

        try:
            fault = FaultService.submit_for_review(
                fault_id=pk,
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username,
                operator_role=request.user.role
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultReviewView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FaultReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            fault = FaultService.submit_review(
                fault_id=pk,
                review_result=serializer.validated_data['review_result'],
                final_conclusion=serializer.validated_data.get('final_conclusion'),
                reviewer_id=request.user.id,
                reviewer_name=request.user.real_name or request.user.username
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultCloseView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FaultCloseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        force_flag = serializer.validated_data.get('force', False)
        if force_flag and request.user.role != 'admin':
            return Response({'error': '只有管理员可以执行强制关闭操作'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            fault = FaultService.close_fault(
                fault_id=pk,
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username,
                operator_role=request.user.role,
                close_note=serializer.validated_data.get('close_note'),
                force=force_flag
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultReopenView(APIView):
    permission_classes = [IsAdminOrReviewer]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        serializer = FaultReopenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            fault = FaultService.reopen_fault(
                fault_id=pk,
                operator_id=request.user.id,
                operator_name=request.user.real_name or request.user.username,
                operator_role=request.user.role,
                reason=serializer.validated_data.get('reason')
            )
            return Response(fault)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StatisticsClosedLoopView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        data = StatisticsService.fault_closed_loop_overview(days=days)
        return Response(data)


class StatisticsPendingFaultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = StatisticsService.pending_fault_tasks(
            user_role=request.user.role,
            user_id=request.user.id
        )
        return Response(data)


class OrderReminderCreateView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        order = InspectionOrderService.get_by_id(pk)
        if not order:
            return Response({'error': '巡检单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            if order.get('projectionist_id') != request.user.id:
                return Response({'error': '您只能对自己相关的巡检单发起催办'},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = ReminderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            reminder = ReminderService.create_order_reminder(
                order_id=pk,
                initiator_id=request.user.id,
                initiator_name=request.user.real_name or request.user.username,
                initiator_role=request.user.role,
                reminder_note=serializer.validated_data.get('reminder_note')
            )
            return Response(reminder, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderReminderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = InspectionOrderService.get_by_id(pk)
        if not order:
            return Response({'error': '巡检单不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            if order.get('projectionist_id') != request.user.id:
                return Response({'error': '您无权查看该巡检单的催办记录'},
                                status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'reviewer':
            reviewer_id = order.get('reviewer_id')
            if reviewer_id is not None and reviewer_id != request.user.id:
                return Response({'error': '您无权查看该巡检单的催办记录'},
                                status=status.HTTP_403_FORBIDDEN)

        reminders = ReminderService.list_by_target('order', pk)
        return Response({
            'total': len(reminders),
            'items': reminders
        })


class FaultReminderCreateView(APIView):
    permission_classes = [IsAdminOrProjectionist]

    def post(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            assigned_id = fault.get('assigned_to_id')
            handler_id = fault.get('handler_id')
            if assigned_id != request.user.id and handler_id != request.user.id:
                return Response({'error': '您只能对自己相关的故障发起催办'},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = ReminderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            reminder = ReminderService.create_fault_reminder(
                fault_id=pk,
                initiator_id=request.user.id,
                initiator_name=request.user.real_name or request.user.username,
                initiator_role=request.user.role,
                reminder_note=serializer.validated_data.get('reminder_note')
            )
            return Response(reminder, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FaultReminderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        fault = FaultService.get_by_id(pk)
        if not fault:
            return Response({'error': '故障记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role == 'projectionist':
            assigned_id = fault.get('assigned_to_id')
            handler_id = fault.get('handler_id')
            if assigned_id != request.user.id and handler_id != request.user.id:
                return Response({'error': '您无权查看该故障的催办记录'},
                                status=status.HTTP_403_FORBIDDEN)
        elif request.user.role == 'reviewer':
            reviewer_id = fault.get('reviewer_id')
            if reviewer_id is not None and reviewer_id != request.user.id:
                return Response({'error': '您无权查看该故障的催办记录'},
                                status=status.HTTP_403_FORBIDDEN)

        reminders = ReminderService.list_by_target('fault', pk)
        return Response({
            'total': len(reminders),
            'items': reminders
        })


class ReminderListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        serializer = ReminderListFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = {}
        for key in ['target_type', 'reminder_type', 'initiator_id', 'start_date', 'end_date']:
            if key in serializer.validated_data and serializer.validated_data[key] is not None:
                filters[key] = serializer.validated_data[key]

        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('page_size', 20)

        result = ReminderService.list(filters=filters, page=page, page_size=page_size)
        return Response(result)


class OrderEscalationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = EscalationListFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = {}
        for key in ['is_resolved', 'hall_id', 'hall_code']:
            if key in serializer.validated_data and serializer.validated_data[key] is not None:
                filters[key] = serializer.validated_data[key]

        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('page_size', 20)

        if request.user.role == 'projectionist':
            result = EscalationService.list_order_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )
            filtered_items = [
                item for item in result['items']
                if item.get('projectionist_name') and item.get('projectionist_id') == request.user.id
            ]
            result['items'] = filtered_items
            result['total'] = len(filtered_items)
        elif request.user.role == 'reviewer':
            result = EscalationService.list_order_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )
            filtered_items = [
                item for item in result['items']
                if item.get('reviewer_name') is None or item.get('reviewer_id') == request.user.id
            ]
            result['items'] = filtered_items
            result['total'] = len(filtered_items)
        else:
            result = EscalationService.list_order_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )

        return Response(result)


class FaultEscalationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = EscalationListFilterSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        filters = {}
        for key in ['is_resolved', 'hall_id', 'fault_level', 'assigned_to_id', 'handler_id']:
            if key in serializer.validated_data and serializer.validated_data[key] is not None:
                filters[key] = serializer.validated_data[key]

        page = serializer.validated_data.get('page', 1)
        page_size = serializer.validated_data.get('page_size', 20)

        if request.user.role == 'projectionist':
            filters['handler_id'] = request.user.id
            result = EscalationService.list_fault_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )
        elif request.user.role == 'reviewer':
            result = EscalationService.list_fault_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )
            filtered_items = [
                item for item in result['items']
                if item.get('reviewer_name') is None
            ]
            result['items'] = filtered_items
            result['total'] = len(filtered_items)
        else:
            result = EscalationService.list_fault_escalations_with_details(
                filters=filters, page=page, page_size=page_size
            )

        return Response(result)


class EscalationCheckView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        EscalationService.check_all_escalations()
        return Response({'message': '超时升级检测已执行'})


class ReminderSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_type = request.query_params.get('target_type')
        target_id = request.query_params.get('target_id')

        if not target_type or not target_id:
            return Response({'error': '缺少 target_type 或 target_id 参数'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            target_id = int(target_id)
        except (ValueError, TypeError):
            return Response({'error': 'target_id 必须是整数'},
                            status=status.HTTP_400_BAD_REQUEST)

        reminder_summary = ReminderService.get_reminder_summary(target_type, target_id)
        escalation_summary = EscalationService.get_escalation_summary(target_type, target_id)

        return Response({
            'reminder': reminder_summary,
            'escalation': escalation_summary
        })
