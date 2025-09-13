from django.db import models
from django.contrib.auth.models import User

class Staff(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Chef', 'Chef'),
        ('Cashier', 'Cashier'),
        ('Inventory', 'Inventory'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"
# class Staff(models.Model):
#     ROLE_CHOICES = [
#         ('Manager', 'Manager'),
#         ('Chef', 'Chef'),
#         ('Waiter', 'Waiter'),
#         ('Cashier', 'Cashier'),
#         ('Cleaner', 'Cleaner'),
#     ]
#     STATUS_CHOICES = [
#         ('Active', 'Active'),
#         ('Inactive', 'Inactive'),
#         ('On Leave', 'On Leave'),
#     ]
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     role = models.CharField(max_length=50, choices=ROLE_CHOICES)
#     phone_number = models.CharField(max_length=15, blank=True)
#     city = models.CharField(max_length=100, blank=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

#     def __str__(self):
#         return f"{self.user.get_full_name() or self.user.username} ({self.role})"

    class Meta:
        verbose_name_plural = "Staff"