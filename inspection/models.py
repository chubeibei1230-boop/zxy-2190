from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_PROJECTIONIST = 'projectionist'
    ROLE_REVIEWER = 'reviewer'
    
    ROLE_CHOICES = [
        (ROLE_ADMIN, '管理员'),
        (ROLE_PROJECTIONIST, '放映员'),
        (ROLE_REVIEWER, '技术复核员'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PROJECTIONIST)
    phone = models.CharField(max_length=20, blank=True, null=True)
    real_name = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'system_users'
    
    def __str__(self):
        return self.username
