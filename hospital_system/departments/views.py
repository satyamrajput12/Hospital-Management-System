from django.shortcuts import render, get_object_or_404
from .models import Department
from doctors.models import Doctor


def department_list(request):
    departments = Department.objects.filter(is_active=True)
    return render(request, 'departments/department_list.html', {'departments': departments})


def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk, is_active=True)
    doctors = Doctor.objects.filter(department=department, is_active=True)
    return render(request, 'departments/department_detail.html', {
        'department': department,
        'doctors': doctors,
    })
