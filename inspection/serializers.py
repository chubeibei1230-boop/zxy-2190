from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'real_name', 'phone']
        read_only_fields = ['id']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'role', 'real_name', 'phone']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'projectionist'),
            real_name=validated_data.get('real_name'),
            phone=validated_data.get('phone')
        )
        return user


class HallSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    hall_code = serializers.CharField(max_length=50)
    hall_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    projector_model = serializers.CharField(max_length=100)
    server_code = serializers.CharField(max_length=50)
    responsible_person = serializers.CharField(max_length=50, allow_blank=True, required=False)
    review_time_limit = serializers.IntegerField(default=24, required=False)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TemplateSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    template_name = serializers.CharField(max_length=100)
    template_type = serializers.CharField(max_length=50)
    check_items = serializers.CharField(allow_blank=True, required=False)
    brightness_min = serializers.IntegerField(default=80, required=False)
    sound_channels = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class InspectionOrderCreateSerializer(serializers.Serializer):
    hall_id = serializers.IntegerField()
    session_no = serializers.CharField(max_length=50)
    template_id = serializers.IntegerField(required=False, allow_null=True)


class SelfCheckSubmitSerializer(serializers.Serializer):
    self_check_result = serializers.BooleanField()
    brightness = serializers.IntegerField(required=False, allow_null=True)
    sound_channels = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    film_source_verified = serializers.BooleanField(required=False, allow_null=True)
    cooling_status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fault_description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fault_level = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    temp_solution = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReviewSubmitSerializer(serializers.Serializer):
    recheck_result = serializers.BooleanField()
    problem_cause = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    final_conclusion = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class InspectionOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    hall_id = serializers.IntegerField()
    hall_code = serializers.CharField()
    session_no = serializers.CharField()
    status = serializers.CharField()
    template_id = serializers.IntegerField(allow_null=True, required=False)
    projectionist_id = serializers.IntegerField(allow_null=True, required=False)
    projectionist_name = serializers.CharField(allow_null=True, required=False)
    reviewer_id = serializers.IntegerField(allow_null=True, required=False)
    reviewer_name = serializers.CharField(allow_null=True, required=False)
    self_check_result = serializers.BooleanField(allow_null=True, required=False)
    brightness = serializers.IntegerField(allow_null=True, required=False)
    sound_channels = serializers.CharField(allow_null=True, required=False)
    film_source_verified = serializers.BooleanField(allow_null=True, required=False)
    cooling_status = serializers.CharField(allow_null=True, required=False)
    fault_description = serializers.CharField(allow_null=True, required=False)
    fault_level = serializers.CharField(allow_null=True, required=False)
    temp_solution = serializers.CharField(allow_null=True, required=False)
    recheck_result = serializers.BooleanField(allow_null=True, required=False)
    problem_cause = serializers.CharField(allow_null=True, required=False)
    final_conclusion = serializers.CharField(allow_null=True, required=False)
    submitted_at = serializers.DateTimeField(allow_null=True, required=False)
    review_deadline = serializers.DateTimeField(allow_null=True, required=False)
    reviewed_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class OrderListFilterSerializer(serializers.Serializer):
    hall_id = serializers.IntegerField(required=False)
    hall_code = serializers.CharField(required=False)
    projector_model = serializers.CharField(required=False)
    responsible_person = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    fault_level = serializers.CharField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, required=False)
    page_size = serializers.IntegerField(default=20, required=False)


class FaultListFilterSerializer(serializers.Serializer):
    hall_id = serializers.IntegerField(required=False)
    fault_level = serializers.CharField(required=False)
    processing_status = serializers.CharField(required=False)
    is_closed = serializers.BooleanField(required=False, allow_null=True)
    assigned_to_id = serializers.IntegerField(required=False)
    handler_id = serializers.IntegerField(required=False)
    order_id = serializers.IntegerField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    page = serializers.IntegerField(default=1, required=False)
    page_size = serializers.IntegerField(default=20, required=False)


class FaultAssignSerializer(serializers.Serializer):
    assigned_to_id = serializers.IntegerField()
    assigned_to_name = serializers.CharField(max_length=50)


class FaultProgressSerializer(serializers.Serializer):
    progress_note = serializers.CharField()


class FaultTempSolutionSerializer(serializers.Serializer):
    temp_solution = serializers.CharField()


class FaultReviewSerializer(serializers.Serializer):
    review_result = serializers.BooleanField()
    final_conclusion = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class FaultCloseSerializer(serializers.Serializer):
    close_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class FaultReopenSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class FaultProgressLogSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    fault_id = serializers.IntegerField(read_only=True)
    operator_id = serializers.IntegerField(allow_null=True, required=False)
    operator_name = serializers.CharField(allow_null=True, required=False)
    operator_role = serializers.CharField(allow_null=True, required=False)
    action_type = serializers.CharField(read_only=True)
    action_detail = serializers.CharField(allow_null=True, required=False)
    from_status = serializers.CharField(allow_null=True, required=False)
    to_status = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)


class FaultSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    order_id = serializers.IntegerField()
    hall_id = serializers.IntegerField()
    hall_code = serializers.CharField(required=False, allow_null=True)
    hall_name = serializers.CharField(required=False, allow_null=True)
    session_no = serializers.CharField(required=False, allow_null=True)
    projector_model = serializers.CharField(required=False, allow_null=True)
    fault_type = serializers.CharField(required=False, allow_null=True)
    fault_level = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    solution = serializers.CharField(required=False, allow_null=True)
    handler_id = serializers.IntegerField(allow_null=True, required=False)
    handler_name = serializers.CharField(required=False, allow_null=True)
    processing_status = serializers.CharField(required=False)
    assigned_to_id = serializers.IntegerField(allow_null=True, required=False)
    assigned_to_name = serializers.CharField(required=False, allow_null=True)
    latest_progress = serializers.CharField(required=False, allow_null=True)
    temp_solution_updated = serializers.CharField(required=False, allow_null=True)
    reviewer_id = serializers.IntegerField(allow_null=True, required=False)
    reviewer_name = serializers.CharField(required=False, allow_null=True)
    review_result = serializers.CharField(required=False, allow_null=True)
    final_conclusion = serializers.CharField(required=False, allow_null=True)
    reviewed_at = serializers.DateTimeField(required=False, allow_null=True)
    closed_by_id = serializers.IntegerField(allow_null=True, required=False)
    closed_by_name = serializers.CharField(required=False, allow_null=True)
    closed_at = serializers.DateTimeField(required=False, allow_null=True)
    is_closed = serializers.BooleanField(required=False)
    closed_loop = serializers.BooleanField(required=False)
    resolved_at = serializers.DateTimeField(required=False, allow_null=True)
    progress_logs = FaultProgressLogSerializer(many=True, read_only=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
