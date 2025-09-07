from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login,logout,update_session_auth_hash
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Staff
from customer.models import Recipe
from django.contrib import messages
import re
import logging
from django.contrib.auth.decorators import login_required


# Create your views here.
logger = logging.getLogger(__name__)

def register_staff(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')

        # Basic validation
        if not all([first_name, last_name, username, password, confirm_password, role, phone_number]):
            return render(request, 'user_auth/add_staff.html', {
                'error': 'Required fields are missing.'
            })

        # Validate username (letters and numbers only)
        if not re.match(r'^[a-zA-Z0-9]+$', username):
            return render(request, 'user_auth/add_staff.html', {
                'error': 'Username must contain only letters and numbers.'
            })

        # Validate password length
        if len(password) < 8:
            return render(request, 'user_auth/add_staff.html', {
                'error': 'Password must be at least 8 characters long.'
            })

        # Validate password confirmation
        if password != confirm_password:
            return render(request, 'user_auth/add_staff.html', {
                'error': 'Passwords do not match.'
            })

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'user_auth/add_staff.html', {
                'error': 'Username already exists.'
            })

        # Create User
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            user.save()
        except ValidationError as e:
            return render(request, 'user_auth/add_staff.html', {
                'error': str(e)
            })

        # Create Staff
        try:
            staff = Staff(
                user=user,
                role=role,
                phone_number=phone_number,
                address=address,
                city=city
            )
            staff.full_clean()
            staff.save()
        except ValidationError as e:
            user.delete()  # Roll back user creation if staff creation fails
            return render(request, 'user_auth/add_staff.html', {
                'error': str(e)
            })

        # Optionally log in the user (if desired)
        # login(request, user)

        return redirect('home')  # Replace with your success URL
    return render(request,'user_auth/add_staff.html')


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate user
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'user_auth/login.html')

        # Log in the user
        auth_login(request, user)

        # Get the user's role from Staff model
        try:
            staff = user.staff_profile
            role = staff.role
        except Staff.DoesNotExist:
            messages.error(request, 'No staff profile found for this user.')
            return render(request, 'user_auth/login.html')

        # Redirect based on role
        if role == 'Admin':
            return redirect('admindashboard')
        elif role == 'Chef':
            return redirect('chef_dashboard')
        elif role == 'Cashier':
            return redirect('menu')
        elif role == 'Inventory':
            return redirect('inventory_dashboard')
        else:
            messages.error(request, 'Unknown role.')
            return render(request, 'user_auth/login.html')

    return render(request, 'user_auth/login.html')

def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return render(request, 'user_auth/change_password.html')

        if new_password != confirm_password:
            messages.error(request, 'New password and confirm password do not match.')
            return render(request, 'user_auth/change_password.html')

        user = request.user
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'user_auth/change_password.html')

        try:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Password updated successfully.')
            return redirect('cashierDashboard')
        except ValidationError as e:
            messages.error(request, str(e))
            return render(request, 'user_auth/change_password.html')

    return render(request, 'user_auth/change_password.html')


def manage_availability(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to access this page.')
        return redirect('userLogin')
    
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        recipe_ids = request.POST.getlist('recipe_ids[]')
        try:
            for recipe in Recipe.objects.all():
                is_available = str(recipe.id) in recipe_ids
                recipe.is_available = is_available
                recipe.save()
            messages.success(request, 'Recipe availability updated successfully.')
            return redirect('cashierDashboard')
        except Exception as e:
            logger.error(f"Error updating availability: {str(e)}")
            messages.error(request, f'Failed to update availability: {str(e)}')
            return redirect('cashierDashboard')
    
    return redirect('cashierDashboard')
    
@login_required
def cashier_dashboard(request):
    # Check role
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.role != 'Cashier':
        messages.error(request, 'You are not authorized to access this page.')
        return redirect('login_view')  # use your login route name
    
    recipes = Recipe.objects.all()
    return render(request, 'user_auth/cashier_dashboard.html', {'recipes': recipes})

def chef_dashboard(request):
    return render(request,'user_auth/chef_dashboard.html')

def inventory_dashboard(request):
    return render(request,'user_auth/inventory_dashboard.html')

def admin_dashboard(request):
    return render(request,'customer/admin_dashboard.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('menu')
