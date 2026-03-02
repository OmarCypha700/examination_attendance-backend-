from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("invigilator", "Invigilator"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_name = None 
    last_name = None 

    REQUIRED_FIELDS = ["role"]

    class Meta:
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def can_scan(self):
        return self.role in ("invigilator", "admin")
