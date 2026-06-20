from django.urls import path
from inspection import views

urlpatterns = [
    path('users/register/', views.UserRegisterView.as_view(), name='user-register'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/profile/', views.UserProfileView.as_view(), name='user-profile'),
    
    path('halls/', views.HallListView.as_view(), name='hall-list'),
    path('halls/<int:pk>/', views.HallDetailView.as_view(), name='hall-detail'),
    
    path('templates/', views.TemplateListView.as_view(), name='template-list'),
    path('templates/<int:pk>/', views.TemplateDetailView.as_view(), name='template-detail'),
    
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/self-check/', views.SelfCheckSubmitView.as_view(), name='order-self-check'),
    path('orders/<int:pk>/review/', views.ReviewSubmitView.as_view(), name='order-review'),
    
    path('statistics/high-fault-devices/', views.StatisticsHighFaultDevicesView.as_view(), name='stats-high-fault'),
    path('statistics/pending-review/', views.StatisticsPendingReviewView.as_view(), name='stats-pending-review'),
    path('statistics/hall-stability/', views.StatisticsHallStabilityView.as_view(), name='stats-hall-stability'),
    path('statistics/overview/', views.StatisticsOverviewView.as_view(), name='stats-overview'),
    path('statistics/closed-loop/', views.StatisticsClosedLoopView.as_view(), name='stats-closed-loop'),
    path('statistics/pending-faults/', views.StatisticsPendingFaultsView.as_view(), name='stats-pending-faults'),
    
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    
    path('choices/status/', views.OrderStatusChoicesView.as_view(), name='choices-status'),
    path('choices/fault-level/', views.FaultLevelChoicesView.as_view(), name='choices-fault-level'),
    path('choices/roles/', views.RoleChoicesView.as_view(), name='choices-roles'),
    path('choices/fault-processing-status/', views.FaultProcessingStatusChoicesView.as_view(), name='choices-fault-processing-status'),
    
    path('faults/', views.FaultListView.as_view(), name='fault-list'),
    path('faults/pending/', views.FaultPendingListView.as_view(), name='fault-pending-list'),
    path('faults/<int:pk>/', views.FaultDetailView.as_view(), name='fault-detail'),
    path('faults/<int:pk>/assign/', views.FaultAssignView.as_view(), name='fault-assign'),
    path('faults/<int:pk>/progress/', views.FaultAddProgressView.as_view(), name='fault-add-progress'),
    path('faults/<int:pk>/temp-solution/', views.FaultUpdateTempSolutionView.as_view(), name='fault-update-temp-solution'),
    path('faults/<int:pk>/submit-review/', views.FaultSubmitForReviewView.as_view(), name='fault-submit-review'),
    path('faults/<int:pk>/review/', views.FaultReviewView.as_view(), name='fault-review'),
    path('faults/<int:pk>/close/', views.FaultCloseView.as_view(), name='fault-close'),
    path('faults/<int:pk>/reopen/', views.FaultReopenView.as_view(), name='fault-reopen'),

    path('orders/<int:pk>/reminders/', views.OrderReminderListView.as_view(), name='order-reminder-list'),
    path('orders/<int:pk>/remind/', views.OrderReminderCreateView.as_view(), name='order-reminder-create'),
    path('faults/<int:pk>/reminders/', views.FaultReminderListView.as_view(), name='fault-reminder-list'),
    path('faults/<int:pk>/remind/', views.FaultReminderCreateView.as_view(), name='fault-reminder-create'),
    path('reminders/', views.ReminderListView.as_view(), name='reminder-list'),

    path('escalations/orders/', views.OrderEscalationListView.as_view(), name='escalation-order-list'),
    path('escalations/faults/', views.FaultEscalationListView.as_view(), name='escalation-fault-list'),
    path('escalations/check/', views.EscalationCheckView.as_view(), name='escalation-check'),
    path('reminder-summary/', views.ReminderSummaryView.as_view(), name='reminder-summary'),
]
