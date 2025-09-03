from django.urls import path
from . import views

urlpatterns = [
    path('register_staff/',views.register_staff, name='addStaff'),
    path('user_login/',views.login,name='userLogin'),
    path('cashier_dashboard/',views.cashier_dashboard, name='cashierDashboard'),
    path('chef_dashboard/',views.chef_dashboard, name='chefDashboard'),
    path('inventory_dashboard/',views.inventory_dashboard, name='inventoryDashboard'),
    path('change_password',views.change_password,name='changePassword'),

]