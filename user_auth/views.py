from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from .models import Staff
import re

# Create your views here.

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

        return redirect('homeview')  # Replace with your success URL
    return render(request,'user_auth/add_staff.html')