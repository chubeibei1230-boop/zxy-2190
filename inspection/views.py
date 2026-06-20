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
    OrderListFilterSerializer
)
from inspection.services import (
    HallService, TemplateService, InspectionOrderService,
    StatisticsService, AlertService
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
        data = StatisticsService.pending_review_tasks()
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
            'pending_review_tasks': StatisticsService.pending_review_tasks(),
            'hall_stability_rates': StatisticsService.hall_stability_rate(days=days)
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
