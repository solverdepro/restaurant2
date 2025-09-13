from django.urls import path
from . import views

urlpatterns = [
    path('register_staff/',views.register_staff, name='addStaff'),
    path('',views.login,name='userLogin'),
    path('cashier_dashboard/',views.cashier_dashboard, name='cashierDashboard'),
    path('chef_dashboard/',views.chef_dashboard, name='chefDashboard'),
    path('inventory_dashboard/',views.inventory_dashboard, name='inventoryDashboard'),
    path('change_password',views.change_password,name='changePassword'),
    path('manage_availability',views.manage_availability,name='manageAvailability'),
    path('logout/',views.logout_view,name='logout'),
    path('view_staff/',views.staff_view, name='staffView'),
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('staff/search/', views.search_staff, name='search_staff'),

]