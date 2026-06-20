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
    
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    
    path('choices/status/', views.OrderStatusChoicesView.as_view(), name='choices-status'),
    path('choices/fault-level/', views.FaultLevelChoicesView.as_view(), name='choices-fault-level'),
    path('choices/roles/', views.RoleChoicesView.as_view(), name='choices-roles'),
]
