from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core import serializers
import textwrap
from dal import autocomplete

from .models import CustomUser, BusinessCertificate, FileAction, Summon, DeathClaimCertificate, BrgyCertificate, CertTribal, Brgy, Purok, Resident, Brgy_Officials, Household, Deceased, Ofw, Blotter, Business, BrgyClearance, BusinessClearance, CertResidency, CertGoodMoral, CertIndigency, CertNonOperation, CertSoloParent, JobSeekers
from .forms import SummonForm, FileActionForm, BusinessCertificateForm, DeathClaimCertificateForm, BrgyCertificateForm, CustomUserChangeForm, SignupForm, CertTribalForm, BrgyForm, PurokForm, ResidentForm, brgyOfficialForm, DeceasedForm, OfwForm, BlotterForm, BusinessForm, BrgyClearanceForm, BusinessClearanceForm, CertGoodMoralForm, CertIndigencyForm, CertNonOperationForm, CertResidencyForm, CertSoloParentForm, HouseholdForm, JobSeekersForm
from django.http import JsonResponse, Http404, HttpResponse
from .excel_import import import_residents_from_excel
from io import BytesIO

from .utils import render_to_pdf
from django.views.generic import View
from datetime import datetime, date, timedelta

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from base64 import b64decode
import re
import io
import pytz
from PIL import Image, ImageOps

import os
import operator
from functools import reduce
from django.db.models import Sum, Count, Q, ExpressionWrapper, F, IntegerField, Value, When, Case, BooleanField
from dateutil.relativedelta import relativedelta
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
import pandas as pd
from django.utils import timezone
# Create your views here.
#@login_required
month_names = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}

def AdEd(request, instance=None, form_class=None, template=None, redirect_to=None, additional_context=None):
    try:
        if request.method == 'POST':
            form = form_class(request.POST, request.FILES, instance=instance)
            if form.is_valid():
                form.save()
                return redirect(redirect_to)
        else:
            form = form_class(instance=instance)

        context = {'form': form, 'instance': instance}
        
        # Add additional context if provided
        if additional_context:
            context.update(additional_context)

        return render(request, template, context)
    except Http404:
        if request.method == 'POST':
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect(redirect_to)
        else:
            form = form_class()

        context = {'form': form}

        # Add additional context if provided
        if additional_context:
            context.update(additional_context)

        return render(request, template, context)

def export_residents_to_excel(file_path='residents.xlsx'):
    # Query all residents from the database
    residents = Resident.objects.all().order_by('house_no__purok')

    # Create a DataFrame from the model instances
    residents_data = {
        
        'House No': [resident.house_no.house_no for resident in residents],
        'Zone/Purok': [resident.house_no.purok for resident in residents],
        'Street': [resident.house_no.address for resident in residents],
        'First Name': [resident.f_name for resident in residents],
        'Last Name': [resident.l_name for resident in residents],
        'Middle Name': [resident.m_name for resident in residents],
        'Gender': [resident.gender for resident in residents],
        'Phone Number': [resident.phone_number for resident in residents],
        'Birth Date': [resident.birth_date for resident in residents],
        'Birth Place': [resident.birth_place for resident in residents],
        'Civil Status': [resident.civil_status for resident in residents],
        'Religion': [resident.religion for resident in residents],
        'Citizenship': [resident.citizenship for resident in residents],
        'Profession': [resident.profession for resident in residents],
        'Education': [resident.education for resident in residents],
        'Resident_type': [resident.resident_type for resident in residents],
        'House Type': [resident.house_no.housing_type for resident in residents],
        'Water Source': [resident.house_no.water_source for resident in residents],
        'Lighting Source': [resident.house_no.lighting_source for resident in residents],
        'Toilet Facility': [resident.house_no.toilet_facility for resident in residents],
        # 'family_income': [resident.family_income for resident in residents],
        'Voter': [resident.voter for resident in residents],
        'Precinct No': [resident.precint_no for resident in residents],
        'Solo Parent': [resident.solo_parent for resident in residents],
        'PWD': [resident.pwd for resident in residents],
        'Indigent': [resident.indigent for resident in residents],
        'Four PS': [resident.fourps for resident in residents],
        # Add more fields as needed
    }

    residents_df = pd.DataFrame(residents_data)

    # Create a response object with the Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=residents.xlsx'

    # Save the DataFrame to the response
    residents_df.to_excel(response, index=False)

    return response

def export_blotter_to_excel(file_path='blotters.xlsx'):
    # Query all residents from the database
    blotter = Blotter.objects.prefetch_related('summon_set').all()

    # Create a DataFrame from the model instances
    blotter_data = {
        
        'complainants': [', '.join(str(complainant) for complainant in b.complainants.all()) for b in blotter],
        'respondents': [', '.join(str(respondent) for respondent in b.respondents.all()) for b in blotter],
        'statement': [b.statement for b in blotter],
        'case': [b.case for b in blotter],
        'date_created': [timezone.localtime(b.date_created).replace(tzinfo=None) for b in blotter],  # Convert to timezone unaware
        'status': [b.status for b in blotter],
        'case_no': [b.case_no for b in blotter],  # Join case_no from related Summon objects
        'summon_date': [", ".join([str(timezone.localtime(s.summon_date).replace(tzinfo=None)) for s in b.summon_set.all()]) for b in blotter],  # Convert to timezone unaware and join
        'date_created_summon': [", ".join([str(timezone.localtime(s.date_created).replace(tzinfo=None)) for s in b.summon_set.all()]) for b in blotter],  # Convert to timezone unaware and join
        # Add more fields as needed
    }

    blotter_df = pd.DataFrame(blotter_data)

    # Create a response object with the Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=blotters.xlsx'

    # Save the DataFrame to the response
    blotter_df.to_excel(response, index=False)

    return response

def logout_view(request):
    logout(request)
    #search to par icontains means insensitive text
    #items = items.filter(name__icontains=query)
    return redirect('login')

def Signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})
    
@login_required
@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
def Users(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    users=CustomUser.objects.all()
    return render (request,'Users.html',{'users' : users, 'has_admin_permission': has_admin_permission})

@login_required
@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
def AdEdUsers(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    try:
        user = get_object_or_404(CustomUser, pk=pk)
        if request.method == 'POST':
            form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                return redirect('Users')
        else:
            form = CustomUserChangeForm(instance=user)
        return render(request, 'AdEdUsers.html', {'form': form, 'has_admin_permission': has_admin_permission})
    except Http404:  
        if request.method == 'POST':
            form = SignupForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('Users')
        else:
            form = SignupForm()
        return render(request, 'AdEdUsers.html', {'form': form})

@login_required
@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to update the session with the new password
            messages.success(request, 'Your password was successfully updated!')
            logout(request)
            return redirect('login')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })
# BrgyApp.can_access_admin_features

def has_custom_access(user):
    # Replace 'yourapp.can_access_generate_pdf' with the actual permission you want to check.
    return user.has_perm('BrgyApp.can_access_admin_features')

@login_required
def index(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    months = ["January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
    ]
    today = datetime.now()
    day_Before = today-timedelta(days=1)
    thisMonth = datetime.now().month
    month_Before = datetime.now().date().replace(day=1) - timedelta(days=1)
    thisYear = datetime.now().year

    resident = Resident.objects.filter(resident_type='Resident').exclude(id__in=Deceased.objects.values('resident'))
    household = Household.objects.all().count()
    # household = Resident.objects.exclude(house_no__isnull=True).values('house_no').annotate(total_count=Count('id')).count()
    business = Business.objects.all()
    brgyclearance = BrgyClearance.objects.all()
    businessclearance = BusinessClearance.objects.all()
    residency = CertResidency.objects.all()
    indigency = CertIndigency.objects.all()
    soloparent = CertSoloParent.objects.all()
    goodmoral = CertGoodMoral.objects.all()
    nonoperation = CertNonOperation.objects.all()
    tribal = CertTribal.objects.all()
    jobseekers = JobSeekers.objects.all()

    # date_filter = request.GET.get('elementValue')  # Assuming you're using GET requests
    # final_date = 'Today'
    # if date_filter == 'Today':
    #     final_date = today
    # elif date_filter == 'This Month':
    #     final_date = thisMonth
    # elif date_filter == 'This Year':
    #     final_date = thisYear

    blotter = Blotter.objects.filter(status='Pending').order_by("date_created")

    brgyClearance_total = brgyclearance.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    brgyCert_total = BrgyCertificate.objects.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    total_count_BrgyclearCert = brgyClearance_total['total_count']  + brgyCert_total['total_count']
    total_BrgyclearCert = 0#brgyClearance_total['total_amount']  + brgyCert_total['total_amount']

    businessClearance_total = businessclearance.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    businessCert_total = BusinessCertificate.objects.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    total_count_BusclearCert = brgyClearance_total['total_count']  + brgyCert_total['total_count']
    total_BusclearCert = 0#businessClearance_total['total_amount']  + businessCert_total['total_amount']

    residency_total = residency.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    indigency_total = indigency.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    soloparent_total = soloparent.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    goodmoral_total = goodmoral.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    nonoperation_total = nonoperation.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    tribal_total = tribal.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    jobseekers_total = jobseekers.filter(date_created__year=thisYear).aggregate(total_count=Count('id'))
    deathCert_total = DeathClaimCertificate.objects.filter(date_created__year=thisYear).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))

    # brgyClearance_monthly = brgyclearance.filter(or_date__year=thisYear).annotate(date_month=TruncMonth('or_date')).values('date_month').annotate(total_amount=Sum('or_amount'), total_count=Count('id')).distinct()
    # businessClearance_monthly = businessclearance.filter(or_date__year=thisYear).annotate(date_month=TruncMonth('or_date')).values('date_month').annotate(total_amount=Sum('or_amount')).distinct()

    series1 = []
    series2 = []
    series3 = []
    series4 = []
    series5 = []
    series6 = []
    series7 = []
    series8 = []

    for m in range(1, 13):
        brgyCert = BrgyCertificate.objects.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        values1 = brgyclearance.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        total_brgyClearance = values1['total_amount'] if values1['total_amount'] is not None else 0
        total_BrgyCert = brgyCert['total_amount'] if brgyCert['total_amount'] is not None else 0
        t = total_brgyClearance + total_BrgyCert
        series1.append(t or 0)
        bus_cert = BusinessCertificate.objects.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        values2 = businessclearance.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        total_busClearance = values2['total_amount'] if values2['total_amount'] is not None else 0
        total_total_busCert = bus_cert['total_amount'] if bus_cert['total_amount'] is not None else 0
        t1 = total_busClearance + total_total_busCert
        series2.append(t1 or 0)
        values3 = residency.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        series3.append(values3['total_amount'] or 0)
        values4 = indigency.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        series4.append(values4['total_amount'] or 0)
        values5 = soloparent.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        series5.append(values5['total_amount'] or 0)
        values6 = goodmoral.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        series6.append(values6['total_amount'] or 0)
        values7 = nonoperation.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
        series7.append(values7['total_amount'] or 0)
        values8 = DeathClaimCertificate.objects.filter(or_date__month=m).aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))      
        series8.append(values8['total_amount'] or 0)

    print(series8)
    print(series5)
    # resident_graph_data = resident.values('purok__purok_name').annotate(total_count=Count('purok')).distinct()
    resident_graph_data = Resident.objects.values('house_no__purok__purok_name').annotate(total_count=Count('id'))
    resident_count = resident.count()
    business_active_count = business.filter(status='ACTIVE').count()
    business_inactive_count = business.filter(status='INACTIVE').count()

    context = {
        'resident': resident,'household': household,'resident_count': resident_count,
        'blotter': blotter,'business_active_count': business_active_count,
        'business_inactive_count': business_inactive_count,'brgyClearance_total': brgyClearance_total,
        'businessClearance_total': businessClearance_total,'residency_total': residency_total,
        'indigency_total': indigency_total,'soloparent_total': soloparent_total,
        'goodmoral_total': goodmoral_total,'nonoperation_total': nonoperation_total,
        'tribal_total': tribal_total,'jobseekers_total': jobseekers_total,'months': months,
        'deathCert_total': deathCert_total, 
        'total_count_BrgyclearCert': total_count_BrgyclearCert,
        'total_BrgyclearCert': total_BrgyclearCert,
        'total_count_BusclearCert': total_count_BusclearCert,
        'total_BusclearCert': total_BusclearCert,
        'thisYear': thisYear,'series1': series1,
        'series2': series2,'series3': series3,'series4': series4,
        'series5': series5,'series6': series6,
        'series7': series7,'series8': series8,
        'resident_graph_data': resident_graph_data,
        'has_admin_permission': has_admin_permission,
    }
    return render(request, 'index.html', context)

def calculate_age(birthdate):
    today = date.today()
    
    if birthdate.year == 1900:
        age = ' '
    else:
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age

def get_filtered_clearance_data(request):
    today = datetime.now()
    thisMonth = datetime.now().month
    thisYear = datetime.now().year 
    date_filter = request.GET.get('elementValue')  # Assuming you're using GET requests
    
    print(date_filter)
    brgyclearance = BrgyClearance.objects.all().filter(date_created=thisYear)
    businessclearance = BusinessClearance.objects.all().filter(date_created=thisYear)
    residency = CertResidency.objects.all().filter(date_created=thisYear)
    indigency = CertIndigency.objects.all().filter(date_created=thisYear)
    soloparent = CertSoloParent.objects.all().filter(date_created=thisYear)
    goodmoral = CertGoodMoral.filter(date_created=thisYear)
    nonoperation = CertNonOperation.objects.all().filter(date_created=thisYear)
    tribal = CertTribal.objects.all().filter(date_created=thisYear)
    # else:
    #     pass
        # Handle other cases or default to a specific date filter
    
    brgyClearance_total = brgyclearance.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    businessClearance_total = businessclearance.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    residency_total = residency.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    indigency_total = indigency.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    soloparent_total = soloparent.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    goodmoral_total = goodmoral.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    nonoperation_total = nonoperation.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    tribal_total = tribal.aggregate(total_amount=Sum('or_amount'), total_count=Count('id'))
    response_data = {
        'brgyClearance_total': brgyClearance_total,
        'businessClearance_total': businessClearance_total,
        'residency_total': residency_total,
        'indigency_total': indigency_total,
        'soloparent_total': soloparent_total,
        'goodmoral_total': goodmoral_total,
        'nonoperation_total': nonoperation_total,
        'tribal_total': tribal_total
    }

    return JsonResponse(response_data)

@login_required
class GeneratePDF(View):
    def get(self, request, *args, **kwargs):
        # template = get_template('resident/ResidentList.html')
        resident = Resident.objects.all()
        pdf = render_to_pdf('List.html', {'resident': resident})
        return HttpResponse(pdf, content_type='application/pdf')
    
# Get the base directory of the project
FontDIR = os.path.dirname(os.path.abspath(__file__))
    
# Path to the font file
arialbd = os.path.join(FontDIR, 'static', 'fonts', 'arialbd.ttf')
arial = os.path.join(FontDIR, 'static', 'fonts', 'Arial.ttf')

# Register the font with ReportLab
pdfmetrics.registerFont(TTFont('Arial-Black', arialbd))
pdfmetrics.registerFont(TTFont('Arial', arial))

def report_header1(p, y_position):
    # def draw_title(y_position, line_height):
    title_header1 = 'Republic of the Philippines'
    title_header2 = 'Province of Cagayan'
    title_header3 = 'Municipality of Tuguegarao'
    title_header4 = 'BARANGAY UGAC SUR'
    #title = "RESIDENTS LIST"
    p.setFont("Helvetica", 11)  
    p.drawCentredString(290, 800, title_header1)
    p.drawCentredString(290, 788, title_header2)
    p.setFont("Helvetica", 13) 
    p.drawCentredString(290, 768, title_header3)
    p.drawCentredString(290, 748, title_header4)
    # image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media\item_images\brgy_logo.png')
    app_directory = os.path.dirname(os.path.abspath(__file__))
    project_directory = os.path.dirname(app_directory)
    image_path = os.path.join(project_directory, 'media', 'item_images', 'UgacSurLogo.jpg')
    image_path1 = os.path.join(project_directory, 'media', 'item_images', 'tuguegarao_logo.png')
    image_path2 = os.path.join(project_directory, 'media', 'item_images', 'bagong_pilipinas.jpg')
    # Embed the image in the PDF
    p.drawImage(image_path2, 460, 743, width=70, height=70)
    p.drawImage(image_path, 125, 743, width=70, height=70)
    p.drawImage(image_path1, 385, 743, width=70, height=70)
    return p

def report_header2(p, y_position):
    # pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    # # pdfmetrics.registerFont(TTFont('Arial Black', 'Arial.ttf'))
    # pdfmetrics.registerFont(TTFont('Arial-Black', 'arialbd.ttf'))
    brgy = Brgy.objects.first()  
    # def draw_title(y_position, line_height):
    title_header1 = 'Republic of the Philippines'
    title_header2 = 'Province of Cagayan'
    title_header3 = f'{brgy.municipality}'
    title_header4 = f'BARANGAY {brgy.brgy_name.upper()}'
    title_header5 = 'OFFICE OF THE PUNONG BARANGAY'
    #title = "RESIDENTS LIST"
    p.setFont("Arial", 12)  
    p.drawCentredString(290, 800, title_header1)
    p.drawCentredString(290, 788, title_header2)
    p.drawCentredString(290, 776, title_header3)

    p.setFont("Arial-Black", 14)   
    p.setFillColorRGB(0.82, 0.25, 0.63)
    p.drawCentredString(290, 757, title_header4)
    p.setFont("Helvetica-Bold", 9)  
    p.setFillColorRGB(0, 0, 0)
    p.drawCentredString(290, 745, title_header5)
    # image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media\item_images\brgy_logo.png')
    app_directory = os.path.dirname(os.path.abspath(__file__))
    project_directory = os.path.dirname(app_directory)
    image_path = os.path.join(project_directory, 'media', 'item_images', 'UgacSurLogo.jpg') #os.path.basename(brgy.image.name)
    image_path1 = os.path.join(project_directory, 'media', 'item_images', 'tuguegarao_logo.png')
    image_path2 = os.path.join(project_directory, 'media', 'item_images', 'bagong_pilipinas.jpg')
    # Embed the image in the PDF
    p.drawImage(image_path2, 460, 743, width=70, height=70)
    p.drawImage(image_path, 125, 743, width=70, height=70)
    p.drawImage(image_path1, 385, 743, width=70, height=70)
    # image_path = "/path/to/your/image.jpg"
    # pdf.drawImage(image_path, 0, 0, width=letter[0], height=letter[1])
    return p

def report_header(p, y_position):
    # pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    # # pdfmetrics.registerFont(TTFont('Arial Black', 'Arial.ttf'))
    # pdfmetrics.registerFont(TTFont('Arial-Black', 'arialbd.ttf'))
    brgy = Brgy.objects.first()  
    # def draw_title(y_position, line_height):
    title_header1 = 'Republic of the Philippines'
    title_header2 = 'Province of Cagayan'
    title_header3 = f'{brgy.municipality}'
    title_header4 = f'BARANGAY {brgy.brgy_name.upper()}'
    title_header5 = 'Tel. # (078) 377 – 2619/ CP. # 0915-608-2549'
    #title = "RESIDENTS LIST"
    p.setFont("Arial", 12)  
    p.drawCentredString(350 + 3, 800, title_header1)
    p.drawCentredString(350 + 3, 788, title_header2)
    p.drawCentredString(350 + 3, 776, title_header3)

    p.setFont("Arial-Black", 14)   
    p.setFillColorRGB(0.82, 0.25, 0.63)
    p.drawCentredString(350 + 3, 757, title_header4)
    p.setFont("Helvetica-Bold", 9)  
    p.setFillColorRGB(0, 0, 0)
    p.drawCentredString(350 + 3, 745, title_header5)
    # image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media\item_images\brgy_logo.png')
    app_directory = os.path.dirname(os.path.abspath(__file__))
    project_directory = os.path.dirname(app_directory)
    image_path = os.path.join(project_directory, 'media', 'item_images', 'UgacSurLogo.jpg') #os.path.basename(brgy.image.name)
    image_path1 = os.path.join(project_directory, 'media', 'item_images', 'tuguegarao_logo.png')
    image_path2 = os.path.join(project_directory, 'media', 'item_images', 'bagong_pilipinas.jpg')
    # Embed the image in the PDF
    p.drawImage(image_path2, 510 + 5, 743, width=70, height=70)
    p.drawImage(image_path, 185 + 5, 743, width=70, height=73)
    p.drawImage(image_path1, 445, 743, width=70, height=70)
    # image_path = "/path/to/your/image.jpg"
    # pdf.drawImage(image_path, 0, 0, width=letter[0], height=letter[1])
    return p

def report_header_landscape(p, y_position):
    brgy = Brgy.objects.first()
    # def draw_title(y_position, line_height):
    title_header1 = 'Republic of the Philippines'
    title_header2 = 'Province of Cagayan'
    title_header3 = f'Municipality of {brgy.municipality}'
    title_header4 = f'BARANGAY {brgy.brgy_name.upper()}'
    title_header5 = 'Tel. # (078) 377 – 2619/ CP. # 0915-608-2549'
    #title = "RESIDENTS LIST"
    p.setFont("Helvetica", 11)  
    p.drawCentredString(440, 800 - 240, title_header1)
    p.drawCentredString(440, 788 - 240, title_header2)
    p.setFont("Helvetica", 13) 
    p.drawCentredString(440, 768 - 240, title_header3)
    p.drawCentredString(440, 748 - 240, title_header4)
    p.setFont("Helvetica", 9)  
    p.drawCentredString(440, 735 - 240, title_header5)
    # image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media\item_images\brgy_logo.png')
    app_directory = os.path.dirname(os.path.abspath(__file__))
    project_directory = os.path.dirname(app_directory)
    image_path = os.path.join(project_directory, 'media', 'item_images', os.path.basename(brgy.image.name))
    # Embed the image in the PDF
    p.drawImage(image_path, 275, 743 - 240, width=70, height=70)

    return p

def report_body(p, y_position, line_height, purok_id, residenden):
    titulo = ""
    boter = False
    resident_wo_deceased = Resident.objects.all().exclude(id__in=Deceased.objects.values('resident'))
    if purok_id != '0':
        if residenden == "Sr":
            residents = resident_wo_deceased.filter(
                Q(house_no__purok=purok_id) &
                Q(birth_date__lt=date.today() - relativedelta(years=+60)) &
                Q(birth_date__year__gt=1900)
            )
            titulo = "All Senior Citizens in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif residenden == "Solo":
            residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(solo_parent=True))
            titulo = "All Solo Parents in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif residenden == "pwd":
             residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(pwd=True))
             titulo = "All Persons with disability in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif residenden == "voter":
            residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(voter=True))
            titulo = "All Registered Voters in " + Purok.objects.filter(pk=purok_id).first().purok_name
            boter = True
        elif residenden == "indigent":
            residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(indigent=True))
            titulo = "All Indigent in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif residenden == "resident":
            residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(resident_type='Resident'))
            titulo = "All Resident in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif residenden == "non-resident":
            residents = resident_wo_deceased.filter(Q(house_no__purok=purok_id) & Q(resident_type='Non-Resident'))
            titulo = "All Non-Resident in " + Purok.objects.filter(pk=purok_id).first().purok_name
        else:
            residents = resident_wo_deceased.filter(house_no__purok=purok_id)
            titulo = Purok.objects.filter(pk=purok_id).first().purok_name
        # residents = Resident.objects.filter(house_no__purok=purok_id)
    else:
        if residenden == "Sr":
            residents = resident_wo_deceased.filter(Q(birth_date__lt=date.today() - relativedelta(years=+60)) & Q(birth_date__year__gt=1900)) 
            titulo = "All Senior Citizens"
        elif residenden == "Solo":
            residents = resident_wo_deceased.filter(solo_parent=True)
            titulo = "All Solo Parents"
        elif residenden == "pwd":
             residents = resident_wo_deceased.filter(pwd=True)
             titulo = "All Persons with disability"
        elif residenden == "voter":
            residents = resident_wo_deceased.filter(voter=True)
            titulo = "All Registered Voters"
            boter = True
        elif residenden == "indigent":
            residents = resident_wo_deceased.filter(indigent=True)
            titulo = "All Indigent"
        elif residenden == "resident":
            residents = resident_wo_deceased.filter(resident_type='Resident')
            titulo = "All Resident"
        elif residenden == "non-resident":
            residents = resident_wo_deceased.filter(resident_type='Non-Resident')
            titulo = "All Non-Resident"
        else:
            residents = resident_wo_deceased.all()
            titulo =""
  
    
    # residents = Resident.objects.all()
    total = residents.count()
    current_date = datetime.now().date()
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.setFillColorRGB(0.82, 0.25, 0.63)
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "RESIDENTS LIST")          
        p.setFont("Helvetica", 12)
        p.setFillColorRGB(0, 0, 0)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(450, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        if boter:
            p.drawString(50, y_position, "NAME")
            p.drawString(340, y_position, "PRECINT NO.")
            p.line(50, y_position - 5, 550, y_position - 5)  
        else:
            p.drawString(50, y_position, "NAME")
            p.drawString(280, y_position, "AGE")
            p.drawString(310, y_position, "GENDER")
            p.drawString(380, y_position, "ADDRESS")
            p.line(50, y_position - 5, 550, y_position - 5)  
          
          
    draw_header()
    y_position -= line_height
        
    
    for i, resident in enumerate(residents, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        if boter:
            p.drawString(50, y_position, f"{i}. {resident.l_name}, {resident.f_name} {resident.m_name}")
            p.drawString(340, y_position, f"{resident.precint_no}")
        else:
            p.drawString(50, y_position, f"{i}. {resident.l_name}, {resident.f_name} {resident.m_name}")
            p.drawString(285, y_position, f"{calculate_age(resident.birth_date)}")
            p.drawString(310, y_position, f"{resident.gender}")
            p.drawString(380, y_position, f"{resident.house_no.purok} | {resident.house_no}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p 

def report_body_brgyClearance_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    brgyClearance = BrgyClearance.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = brgyClearance.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = brgyClearance.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "BRGY CERTIFICATION WITH ID LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(brgyClearance, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_brgyCertificate_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    brgycertificate = BrgyCertificate.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = brgycertificate.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = brgycertificate.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "BRGY CERTIFICATION WITH PUROK LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(brgycertificate, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_deathclaimcert_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    deathclaimcert = DeathClaimCertificate.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = deathclaimcert.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = deathclaimcert.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "DEATH PERSON CLAIM OF RELATIVE LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "DECEASED NAME")
        p.drawString(230, y_position, "CLAIMANT")
        p.drawString(370, y_position, "DATE CREATED")
        p.drawString(480, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(deathclaimcert, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.deceased}")
        p.drawString(230, y_position, f"{clearance.claimant}")
        p.drawString(370, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(480, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_Indigency_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certIndigency = CertIndigency.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certIndigency.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certIndigency.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF INDIGENCY LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certIndigency, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_SoloParent_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certSoloParent = CertSoloParent.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certSoloParent.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certSoloParent.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF SOLO PARENT LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certSoloParent, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_JobSeekers_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    jobseekers = JobSeekers.objects.filter(date_created__range=[dateFrom, dateTo])
    # total_amount = certGoodMoral.aggregate(total_amount=Sum('or_amount'))
    # total_amount_value = total_amount.get('total_amount', 0)
    total = jobseekers.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "FIRST TIME JOB SEEKERS LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        # p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "DATE")
        p.drawString(120, y_position, "NAME")
        p.drawString(230, y_position, "AGE")
        p.drawString(280, y_position, "GENDER")
        p.drawString(350, y_position, "ADDRESS")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, seekers in enumerate(jobseekers, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {seekers.date_created.strftime('%Y-%m-%d')}")
        p.drawString(120, y_position, f"{seekers.resident}")
        p.drawString(230, y_position, f"{calculate_age(seekers.resident.birth_date)}")
        # p.drawString(320, y_position, f"{seekers.date_created.strftime('%Y-%m-%d')}")
        p.drawString(280, y_position, f"{seekers.resident.gender}")
        p.drawString(350, y_position, f"{seekers.resident.house_no.address}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_GoodMoral_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certGoodMoral = CertGoodMoral.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certGoodMoral.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certGoodMoral.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF GOOD MORAL LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certGoodMoral, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_Tribal_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certTribal = CertTribal.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certTribal.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certTribal.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF TRIBAL MEMBERSHIP LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certTribal, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_Summon_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    summon = Summon.objects.filter(summon_date__range=[dateFrom, dateTo])
    total = summon.count()
    current_date = datetime.now().date()
    def draw_header():
        # p.setLineWidth(2)
        # p.line(80, y_position + 80, 550, y_position + 80)
        # p.setLineWidth(1)
        p.drawCentredString(290, y_position + 37, titulo)
        p.setFont("Helvetica-Bold", 16)    
        p.drawCentredString(290, y_position + 55, "SUMMON LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(700, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "Compainant")
        p.drawString(200, y_position, "Respondent")
        p.drawString(320, y_position, "Case No.")
        p.drawString(380, y_position, "Case")
        p.drawString(450, y_position, "Date/Time")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, summon in enumerate(summon, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height
        summon_date = summon.summon_date.strftime("%Y-%m-%d %H:%M:%S")
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{','.join(str(complainant) for complainant in summon.blotter.complainants.all())}")
        p.drawString(200, y_position, f"{','.join(str(respondent) for respondent in summon.blotter.respondents.all())}")
        p.drawString(340, y_position, f"{summon.blotter.case_no}")
        p.drawString(380, y_position, f"{summon.blotter.case}")
        p.drawString(450, y_position, f"{summon_date}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_FileAction_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    if dateFrom == dateTo:
        filecation = FileAction.objects.filter(date_created=dateFrom)
    else:
        filecation = FileAction.objects.filter(date_created__range=[dateFrom, dateTo])

    
    total = filecation.count()
    current_date = datetime.now().date()
    def draw_header():
        # p.setLineWidth(2)
        # p.line(80, y_position + 80, 550, y_position + 80)
        # p.setLineWidth(1)
        p.drawCentredString(290, y_position + 37, titulo)
        p.setFont("Helvetica-Bold", 16)    
        p.drawCentredString(290, y_position + 55, "FILE ACTION CERTIFICATE LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(700, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "Compainant")
        p.drawString(200, y_position, "Respondent")
        p.drawString(320, y_position, "Case No.")
        p.drawString(380, y_position, "Case")
        p.drawString(450, y_position, "Date Created")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, filecation in enumerate(filecation, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y positsion for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {','.join(str(complainant) for complainant in filecation.case_no.blotter.complainants.all())}")
        p.drawString(200, y_position, f"{','.join(str(respondent) for respondent in filecation.case_no.blotter.respondents.all())}")
        p.drawString(340, y_position, f"{filecation.case_no}")
        p.drawString(380, y_position, f"{filecation.case_no.blotter.case}")
        p.drawString(450, y_position, f"{filecation.case_no.date_created.strftime('%Y-%m-%d')}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_NonOperation_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certNonOperation = CertNonOperation.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certNonOperation.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certNonOperation.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF NON-OPERATION OF BUSINESS LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "BUSINESS NAME")
        p.drawString(200, y_position, "CEASED DATE")
        p.drawString(300, y_position, "PURPOSE")
        p.drawString(380, y_position, "DATE CREATED")
        p.drawString(495, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certNonOperation, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.business}")
        p.drawString(200, y_position, f"{clearance.ceased_date.strftime('%Y-%m-%d')}")
        p.drawString(300, y_position, f"{clearance.purpose}")
        p.drawString(380, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(495, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_Residency_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    certResidency = CertResidency.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = certResidency.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = certResidency.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "CERTIFICATE OF RESIDENCY LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(230, y_position, "PURPOSE")
        p.drawString(320, y_position, "DATE CREATED")
        p.drawString(450, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(certResidency, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.resident}")
        p.drawString(230, y_position, f"{clearance.purpose}")
        p.drawString(320, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(450, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_businessClearance_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    businessClearance = BusinessClearance.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = businessClearance.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = businessClearance.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "BUSINESS CLEARANCE LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "BUSINESS NAME")
        p.drawString(230, y_position, "BUSINESS TYPE")
        p.drawString(350, y_position, "DATE CREATED")
        p.drawString(470, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(businessClearance, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.business}")
        p.drawString(230, y_position, f"{clearance.business.business_type}")
        p.drawString(350, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(470, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_businessCertificate_list(p, y_position, line_height, dateFrom, dateTo):
    titulo = ""
    if dateFrom != dateTo:
        titulo = "(" + str(dateFrom) + ")" + " to " + "(" + str(dateTo) + ")"
    else:
        titulo = "(" + str(dateFrom) + ")"
    
    businessCert = BusinessCertificate.objects.filter(date_created__range=[dateFrom, dateTo])
    total_amount = businessCert.aggregate(total_amount=Sum('or_amount'))
    total_amount_value = total_amount.get('total_amount', 0)
    total = businessCert.count()
    # current_date = datetime.now().date()
    
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "BUSINESS CERTIFICATE FOR SMALL BUSINESS LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(420, y_position + 20, f"Total Amount: {total_amount_value}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "BUSINESS NAME")
        p.drawString(250, y_position, "DATE CREATED")
        p.drawString(470, y_position, "AMOUNT")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, clearance in enumerate(businessCert, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {clearance.business}")
        p.drawString(250, y_position, f"{clearance.date_created.strftime('%Y-%m-%d')}")
        p.drawString(470, y_position, f"{clearance.or_amount}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_household(p, y_position, line_height, purok_id):
    titulo = ""
    if purok_id != '0':
        households = Household.objects.filter(purok=purok_id).order_by("house_no")
        # residents = Resident.objects.filter(house_no=purok_id).order_by("house_no")
        titulo = Purok.objects.filter(pk=purok_id).first().purok_name
        # residents = Resident.objects.filter(house_no__purok=purok_id)
    else:
        households = Household.objects.all().order_by("house_no")
        # residents = Resident.objects.filter(house_no=purok_id).order_by("house_no")
        # titulo = Purok.objects.filter(pk=purok_id).first().purok_name
        # residents = Resident.objects.all().order_by("house_no")
        titulo = ""
    
    # residents = Resident.objects.all()
    total = households.count()
    current_date = datetime.now().date()
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "HOUSEHOLD LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(450, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "ZONE")
        p.drawString(100, y_position, "Address")
        p.drawString(220, y_position, "NAME")
        p.drawString(430, y_position, "AGE")
        p.drawString(470, y_position, "GENDER")

        p.line(50, y_position - 5, 550, y_position - 5)    
        
        
        
         
    draw_header()
    y_position -= line_height
    no = 0    
    # previous_house_no = None  # Initialize previous_house_no
    for i, household in enumerate(households, start=1):
        house_no = household.house_no
        residents = Resident.objects.filter(house_no=household).order_by("house_no__purok")
        for resident in residents:
            no += 1
            if y_position <= 50:
                p.showPage()  # Start a new page
                y_position = 650  # Reset Y position for the new page
                draw_header()  # Draw row header for the new page
                report_header1(p, y_position)
                y_position -= line_height
            p.setFont("Helvetica", 10)
            p.drawString(50, y_position, f"{household.purok}")
            p.drawString(100, y_position, f"{house_no} {household.address}")
            p.drawString(220, y_position, f"{resident.l_name}, {resident.f_name} {resident.m_name}")
            p.drawString(430, y_position, f"{calculate_age(resident.birth_date)}")
            p.drawString(470, y_position, f"{resident.gender}")

            # if previous_house_no != f"{resident.house_no}":
            
                # previous_house_no = f"{resident.house_no}"
            # p.line(50, y_position - 5, 550, y_position - 5)
            y_position -= line_height
        p.line(50, y_position + 15, 550, y_position + 15)
    return p

def report_body_blotter(p, y_position, line_height, status):
    titulo = ""
    if status != 'all':
        if status == "Pending":
            blotter = Blotter.objects.filter(status=status)
            titulo = "Pending"
        else:
            blotter = Blotter.objects.filter(status=status)
            titulo = "Solved"
        # residents = Resident.objects.filter(house_no__purok=purok_id)
    else:
            blotter = Blotter.objects.all()
            titulo =""
  
    # residents = Resident.objects.all()
    total = blotter.count()
    current_date = datetime.now().date()
    def draw_header():
        p.drawCentredString(440, y_position + 37, titulo)
        p.setFont("Helvetica-Bold", 16)    
        p.drawCentredString(440, y_position + 55, "BLOTTER LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(700, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 800, y_position + 15)
        p.drawString(50, y_position, "Case No.")
        p.drawString(130, y_position, "Compainant")
        p.drawString(350, y_position, "Respondent")
        p.drawString(550, y_position, "Case")
        # p.drawString(560, y_position, "Location")
        p.drawString(720, y_position, "Date")
        p.line(50, y_position - 5, 800, y_position - 5)    
          
    draw_header()
    y_position -= line_height
    # complainants_list = blotter.complainants.all()
    # complainants= "\n".join(str(complainant) for complainant in complainants_list)
    # respondents_list = blotter.respondents.all()
    # respondents= "\n".join(str(respondent) for respondent in respondents_list)
    
    for i, blotter in enumerate(blotter, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {blotter.case_no}")
        # p.drawString(130, y_position, f"{i}. {blotter.complainants}")
        # p.drawString(350, y_position, f"{blotter.respondents}")
        p.drawString(130, y_position, f"{','.join(str(complainant) for complainant in blotter.complainants.all())}")
        p.drawString(350, y_position, f"{','.join(str(respondent) for respondent in blotter.respondents.all())}")
        p.drawString(550, y_position, f"{blotter.case}")
        # p.drawString(560, y_position, f"{blotter.location}")
        p.drawString(720, y_position, f"{blotter.date_created.strftime('%Y-%m-%d')}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_ofw(p, y_position, line_height, purok_id):
    titulo = ""
    if purok_id != '0':
        ofw = Ofw.objects.filter(resident__purok=purok_id)
        titulo = "All OFW in " + Purok.objects.filter(pk=purok_id).first().purok_name
    else:
        ofw = Ofw.objects.all()
        titulo = ""
  
    # residents = Resident.objects.all()
    total = ofw.count()
    current_date = datetime.now().date()
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "OFW LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(450, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(240, y_position, "PASSPORT NUMBER")
        p.drawString(430, y_position, "COUNTRY")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, resident in enumerate(ofw, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {resident.resident}")
        p.drawString(240, y_position, f"{resident.passport_no}")
        p.drawString(430, y_position, f"{resident.country}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_deceased(p, y_position, line_height, purok_id):
    titulo = ""
    if purok_id != '0':
        deceased = Deceased.objects.filter(resident__purok=purok_id)
        titulo = "All Deceased in " + Purok.objects.filter(pk=purok_id).first().purok_name
    else:
        deceased = Deceased.objects.all()
        titulo = ""
  
    # residents = Resident.objects.all()
    total = deceased.count()
    current_date = datetime.now().date()
    def draw_header():
        p.setFont("Helvetica-Bold", 16) 
        p.drawCentredString(290, y_position + 37, titulo)
        p.drawCentredString(290, y_position + 55, "DECEASED LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(450, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "NAME")
        p.drawString(260, y_position, "DATE OF DEATH")
        p.drawString(400, y_position, "CAUSE OF DEATH")
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, resident in enumerate(deceased, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {resident.resident}")
        p.drawString(260, y_position, f"{resident.date_of_death}")
        p.drawString(400, y_position, f"{resident.cause_of_death}")
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_body_deathclaimcert(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo_path = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    # Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")  
    p.drawImage(brgy_logo_path, 105, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    deathclaimcert = DeathClaimCertificate.objects.get(pk=pk)
    current_date = datetime.now()
    formatted_day = get_day_with_suffix(deathclaimcert.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        # p.setFont("Helvetica-Bold", 13) 
        # p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        # p.setFont("Helvetica-Bold", 12)
        p.setLineWidth(2)
        p.line(50, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        p.setFont("Times-Bold", 25)
        p.drawCentredString(290, y_position + 30, "C E R T I F I C A T I O N")
        x, y = 50, y_position  # Starting position
        p.setFont("Helvetica-Bold", 15.25)
        p.drawString(50, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b> <b><u>{deathclaimcert.deceased}</u></b> is a bona-fide resident of <b><u>{deathclaimcert.deceased.resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This certifies further</b> that <b><u>{deathclaimcert.deceased}</u></b> died last {deathclaimcert.deceased.date_of_death}.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This certification</b> is issued upon the request of <b><u>{deathclaimcert.claimant}</u></b> whatever purpose/s it may serve.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(deathclaimcert.date_created.month)}</b></u>, <u><b>{deathclaimcert.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=15.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 22,
        )
        draw_paragraph(p, content_text, x, y, 500, 800, justified_style)

        p.setFont("Helvetica-Bold", 15)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 300, 208, 80, 70)
        p.drawString(190, 325 - 130, f'HON. AARON ROBERT A. BINARAO')
        p.line(190, 322 - 130, 447, 322  - 130)
        p.drawString(247, 310 - 130, "Punong Barangay")
    draw_header()
    y_position -= line_height

    return p

def report_body_business(p, y_position, line_height, purok_id, status):
    titulo = ""
    if purok_id != '0':
        if status == "ACTIVE":
            business = Business.objects.filter(Q(house_no__purok=purok_id) & Q(status='ACTIVE'))
            titulo = "All Active Business in " + Purok.objects.filter(pk=purok_id).first().purok_name
        elif status == "INACTIVE":
            business = Business.objects.filter(Q(house_no__purok=purok_id) & Q(status='INACTIVE'))
            titulo = Purok.objects.filter(pk=purok_id).first().purok_name
        else:
            business = Business.objects.filter(purok=purok_id)
            titulo = Purok.objects.filter(pk=purok_id).first().purok_name
        # residents = Resident.objects.filter(house_no__purok=purok_id)
    else:
        if status == "ACTIVE":
            business = Business.objects.filter(status='ACTIVE')
            titulo = "All Active Business"
        elif status == "INACTIVE":
            business = Business.objects.filter(status='INACTIVE')
            titulo = "All Inactive Business"
        else:
            business = Business.objects.all()
            titulo = ""
  
    # residents = Resident.objects.all()
    total = business.count()
    current_date = datetime.now().date()
    def draw_header():
        p.drawCentredString(290, y_position + 37, titulo)
        p.setFont("Helvetica-Bold", 16)      
        p.drawCentredString(290, y_position + 55, "BUSINESS LIST")          
        p.setFont("Helvetica", 12)
        p.drawString(50, y_position + 20, f"Total Count: {total}")
        p.drawString(450, y_position + 20, f"As of: {current_date}")
        p.setFont("Helvetica-Bold", 12)
        p.line(50, y_position + 15, 550, y_position + 15)
        p.drawString(50, y_position, "BUSINESS NAME")
        # p.drawString(180, y_position, "BUSINESS TYPE")
        p.drawString(290, y_position, "ADDRESS")
        p.drawString(400, y_position, "PROPRIETOR'S NAME")
        
        p.line(50, y_position - 5, 550, y_position - 5)    
          
    draw_header()
    y_position -= line_height
        
    
    for i, business in enumerate(business, start=1):
        if y_position <= 50:
            p.showPage()  # Start a new page
            y_position = 650  # Reset Y position for the new page
            draw_header()  # Draw row header for the new page
            report_header1(p, y_position)
            y_position -= line_height

        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"{i}. {business.business_name}")
        # p.drawString(180, y_position, f"{business.business_type}")
        p.drawString(290, y_position, f"{business.address}")
        p.drawString(400, y_position, f"{business.proprietor}")
        
        # p.line(50, y_position - 5, 550, y_position - 5)
        y_position -= line_height
    return p

def report_brgyOfficials(p, y_position, footer_text):
    officials = Brgy_Officials.objects.first()  
    twelve_space = 12
    current_file_path = os.path.abspath(__file__)
    image_filename = "sidepanel.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    image_path = os.path.join(media_folder, image_filename)

    # Construct the full path to the image file
    # image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    p.drawImage(image_path, 30, 20, width=160, height=800)
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0.12, 0.29, 0.49)
    p.drawCentredString(112, y_position + 50, "BARANGAY OFFICIALS")
    p.drawCentredString(112, y_position + 30, "2023-2025")
    
    p.setFont("Helvetica-Bold", 10)
    p.setFillColorRGB(0.12, 0.29, 0.49)
    p.drawCentredString(112, y_position, "AARON ROBERT A. BINARAO")
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(112, y_position - (twelve_space * 4), "Glenmore D. Arao")
    p.drawCentredString(112, y_position - (twelve_space * 9), "Arthur M. Maddara")
    p.drawCentredString(112, y_position - (twelve_space * 14), "Garet P. Soriano")
    p.drawCentredString(112, y_position - (twelve_space * 21), "Remelin M. Addun")
    p.drawCentredString(112, y_position - (twelve_space * 28), "Alberto B. Balubal")
    p.drawCentredString(112, y_position - (twelve_space * 32), "Isidro A. Tamayao")
    p.drawCentredString(112, y_position - (twelve_space * 38), "Mikejor G. De Ramos")
    p.drawCentredString(112, y_position - (twelve_space * 42), "Justine Claire E. Talay")
    p.drawCentredString(112, y_position - (twelve_space * 47), "Romel T. Flores")
    p.drawCentredString(112, y_position - (twelve_space * 50), "Francis C. Gonzales")


    p.setFont("Helvetica-Bold", 10)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(68, y_position - twelve_space, "Punong Barangay")
    
    p.setFont("Helvetica", 10)
    p.drawString(68, y_position - (twelve_space * 5), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 10), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 15), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 22), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 29), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 33), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 39), "Barangay Kagawad")
    p.drawString(68, y_position - (twelve_space * 43), "   SK Chairman")
    p.drawString(68, y_position - (twelve_space * 48), "Barangay Secretary")
    p.drawString(68, y_position - (twelve_space * 51), "Barangay Treasurer")
    p.setFont("Helvetica", 8)
    p.drawString(50, y_position - (twelve_space * 2), "Chairman, Comm. On Agriculture")
    p.drawString(40, y_position - (twelve_space * 6), "Chairman, Comm. On Peace and Order")
    p.drawString(80, y_position - (twelve_space * 7), "And Public Safety")
    p.drawString(40, y_position - (twelve_space * 11), "Chairman, Comm. On Social, Education,")
    p.drawString(84, y_position - (twelve_space * 12), " And Culture")
    p.drawString(40, y_position - (twelve_space * 16), "     Chairman, Comm. On Health and")
    p.drawString(84, y_position - (twelve_space * 17), "   Sanitation")
    p.drawString(40, y_position - (twelve_space * 18), "        Chairman, Comm. On Justice")
    p.drawString(40, y_position - (twelve_space * 19), "Chairman, Comm. On Bids and Awards")
    p.drawString(40, y_position - (twelve_space * 23), "      Chairman, Comm. Finance and")
    p.drawString(84, y_position - (twelve_space * 24), "  Appropriation")
    p.drawString(40, y_position - (twelve_space * 25), "   Chairman, Comm. On Women and")
    p.drawString(84, y_position - (twelve_space * 26), "       Family")
    p.drawString(40, y_position - (twelve_space * 30), "  Chairman, Comm. On Infrastructure")
    p.drawString(40, y_position - (twelve_space * 34), "      Chairman, Comm. On Ecology/")
    p.drawString(84, y_position - (twelve_space * 35), "  Environment")
    p.drawString(38, y_position - (twelve_space * 36), "Chairman, Comm. On Transportation")
    p.drawString(38, y_position - (twelve_space * 40), "Chairman, Comm. On Ways and Means")
    p.drawString(40, y_position - (twelve_space * 44), "     Chairman, Comm. On Sports and")
    p.drawString(80, y_position - (twelve_space * 45), "Developement")
    p.setFont("Helvetica", 7)
    p.drawCentredString(480, footer_text, "NOTE: NOT VALID WITHOUT DRY SEAL")
    # p.setFont("Helvetica", 10)
    # p.drawCentredString(115, footer_text - 20, "Valid for 6 months from this date.")

def report_body_Oath(p, y_position, line_height, pk):
    
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    jobseekers = JobSeekers.objects.get(pk=pk)
    brgy = Brgy.objects.first()
    current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(current_date.day)
    p.setStrokeColor(colors.black)  # Set the frame color
    p.rect(30, 40, 530, 655)
    def draw_header():
        p.setFont("Helvetica-Bold", 13) 
        p.drawCentredString(290, y_position + 50, "OFFICE OF THE PUNONG BARANGAY")       
        p.setFont("Helvetica-Bold", 12)
        p.line(30, y_position + 80, 560, y_position + 80)
        p.line(40, y_position + 77, 550, y_position + 77)     
        p.setFont("Times-Bold", 25)
        p.drawCentredString(290, y_position, "OATH OF UNDERTAKING")
        # p.line(200, y_position + 20, 560, y_position + 20) 
        # p.line(200, 695, 200, 40)
         # Set the width and height for the paragraph
        x, y = 50, y_position  # Starting position
        
        # p.setFont("Helvetica", 11.25)
        # p.drawString(205, y_position, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is to certify that, Mr/Mrs. <b><u>{jobseekers.resident}</u></b>, a resident of <b><u>{jobseekers.resident.house_no}</u></b>, <b><u>{brgy.brgy_name}</u></b>, <b><u>{brgy.municipality}</u></b> for (years/months) availing the benefits of Republic Act 11261.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Otherwise known as the first Time jobseekers Act of 2019 do hereby declare, agree and undertake to abide and be bound by the following:
        
        1. That this is the first time that I will actively look for a job, and  therefore requesting that a Barangay Certificate be issued in my favor to avail the benefit of the law;
        2. That I am aware that the benefit anmd priviledge/s under said law shall be valid only for one (1) year from the date that the barangay issued.
        3. That I can avail the benefits of the law only once;
        4. That I understand that my personal information shall be included in the Roster/List of first Time Jobseekers and will not be used for any unlawful purpose;
        5. That I will inform and/or report to the Barangay personally, through text or the other means, or through my family/relatives once I get employed; and
        6. That iam not beneficiary of the jobstart program under R.A. No. 10889 and other laws give me similar exemptions for the documents or transactions exempted under R.A. 11261
        7. That if issued the request Certification, I will not use the same in any fraud, neither falsity nor help and/or assist in the fabrication of the said certification.
        8. That this undertaking is made solely for the purpose of obtaining a Barangay Certificate consistent with the objective of R.A. 11261 and not for any other purpose.
        9. That this consent to the use of my personal information pursuant of the Data Privacy Act and other applicable laws, rules, and regulations.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(current_date.month)}</b></u>, <u><b>{current_date.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 500, 800, justified_style)


        p.setFont("Helvetica-Bold", 12)
        # Calculate the width of the text
        text_width = p.stringWidth(f"HON. ", "Helvetica", 12)

        # Calculate the starting position to center the text
        x_position = 215 + ((180 - text_width) / 2)

        # Draw the centered text
        # p.drawCentredString(290, 305, f"HON. {captain_name}")  
        # p.drawString(x_position, 305, f"HON. {captain_name}")
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(115, 160, "First Time Job Seeker")
        # p.drawString(250, 290, "PUNONG BARANGAY")
        p.line(50, 170, 180, 170)

        p.setFont("Helvetica-Oblique", 8.25)
        p.drawString(50, 125, "Witnessed by:")
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(115, 90, "Barangay Officials")  
        # p.drawString(265, 200, "Barangay Officials")
        p.line(50, 100, 180, 100)
        
    draw_header()
    y_position -= line_height

    return p

def add_signature(p, signature_path, x, y, width, height):
    signature = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", signature_path)

    # Open the image using Pillow
    img = Image.open(signature)

    # Convert the image to RGBA mode
    img = img.convert("RGBA")

    # Create a new image with a transparent background
    new_img = Image.new("RGBA", img.size, (0, 0, 0, 0))

    # Paste the signature image onto the new image
    new_img.paste(img, (0, 0))

    # Resize the image to fit the specified width and height
    new_img = new_img.resize((width, height))

    # Create an Image object in ReportLab
    p.drawImage(ImageReader(new_img), x, y, width=width, height=height)

def report_body_JobSeekers(p, y_position, line_height, pk):
    
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    jobseekers = JobSeekers.objects.get(pk=pk)
    brgy = Brgy.objects.first()
    current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(current_date.day)
    p.setStrokeColor(colors.black)  # Set the frame color
    p.rect(30, 40, 530, 655)
    def draw_header():
        p.setFont("Helvetica-Bold", 13) 
        p.drawCentredString(290, y_position + 50, "OFFICE OF THE PUNONG BARANGAY")       
        p.setFont("Helvetica-Bold", 12)
        p.line(30, y_position + 80, 560, y_position + 80)
        p.line(40, y_position + 77, 550, y_position + 77)     
        p.setFont("Times-Bold", 25)
        p.drawCentredString(290, y_position, "C E R T I F I C A T I O N")
        # p.line(200, y_position + 20, 560, y_position + 20) 
        # p.line(200, 695, 200, 40)
         # Set the width and height for the paragraph
        x, y = 50, y_position  # Starting position
        
        # p.setFont("Helvetica", 11.25)
        # p.drawString(205, y_position, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is to certify that, Mr/Mrs. <b><u>{jobseekers.resident}</u></b>, a resident of <b><u>{jobseekers.resident.house_no}</u></b>, <b><u>{brgy.brgy_name}</u></b>, <b><u>{brgy.municipality}</u></b>, Cagayan, and is qualified to avail of R.A. 11261 or the First Time Job Seekers Assistance Act of 2019.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is to certify further that the holder/bearer was informed of his/her rights, including the duties and responsibilities accorded bt R.A. 11261 through the oath of undertaking he/she has signed and executed in the presence of Barangay Officials.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(current_date.month)}</b></u>, <u><b>{current_date.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 500, 800, justified_style)

        p.setFont("Helvetica-Bold", 13)
        # Add e-signature above the paragraph
        add_signature(p, "media/item_images/cap_esig-fotor.png", 290, 334, 80, 70)
        p.drawString(190, 355 - 30, f'HON. AARON ROBERT A. BINARAO')
        p.line(190, 352 - 30, 413, 352 - 30)
        p.drawString(247, 340 - 30, "Punong Barangay")

        p.setFont("Helvetica", 10)
        p.drawCentredString(300, 200, "Barangay Officials")  
        # p.drawString(265, 200, "Barangay Officials")
        p.line(190, 210, 413, 210)
        
    draw_header()
    y_position -= line_height

    return p

def report_body_Summon(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    # Frame = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "frame.png")
    p.drawImage(brgy_logo, 120, 200, width=380, height=380) #brgy logo
    # p.drawImage(Frame, 120, 273, width=A4[0], height=A4[1]) #Frame
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 100, y_position + 20, width=400, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    summon = Summon.objects.get(pk=pk)
    # resident = brgyclearance.resident
    current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(current_date.day)
    summon_date_utc = summon.summon_date.replace(tzinfo=pytz.UTC)
    summon_date_local = summon_date_utc.astimezone(pytz.timezone('Asia/Manila'))
    summon_day = get_day_with_suffix(summon_date_local.day)
    summon_time = summon_date_local.strftime("%I:%M %p")
    # Fetch all complainants related to the blotter
    complainants_list = summon.blotter.complainants.all()
    complainants_text = "\n".join(str(complainant) for complainant in complainants_list)
    respondents_list = summon.blotter.respondents.all()
    respondents_text = "\n".join(str(respondents) for respondents in respondents_list)
    summons_to = ", ".join(str(respondents) for respondents in respondents_list)
    plus_y = 0
    if complainants_list.count() > 1:
        plus_y += 15 * (complainants_list.count()-1)
        print(plus_y)
    if respondents_list.count() > 1:
        plus_y += 15 * (respondents_list.count()-1)
        print(plus_y)
    
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        p.setLineWidth(2)
        p.line(50, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 50, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        # p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        content_text = f"""<b><u>{complainants_text}</u>
        Complainant/s&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;For: <u>{summon.blotter.case}</u>

        <u>-against-</u>

        <u>{respondents_text}</u> 
        Respondent/s                                                                  

        S U M M O N S
        TO: <u>{summons_to}</u>

        Respondent/s

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;You  are  hereby  summoned  to  appear  before  me  in  person on, together with your  witnesses on the <u>{summon_day}</u> day of <u>{month_names.get(summon.summon_date.month)}</u>, <u>{summon.summon_date.year}</u> at <u>{summon_time}</u>, then and there to answer the complaint  made before me, a copy of which is attached hereto, for mediation/conciliation of your dispute with the complainant/s.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Your failure to appear is a manifestation that you are not willing for an amicable settlement. Hence, this office will issue a certification to file action.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u>{formatted_day}</u> day of <u>{month_names.get(current_date.month)}</u>, <u>{current_date.year}</u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.</b> 
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'CustomJustified',
            parent=styles['BodyText'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 510, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(340, 620, f'Barangay Case No.: {summon.blotter}')
        p.line(453, 618, 510, 618)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 160 - plus_y, 80, 70)
        p.drawString(340, (190 - 40) - plus_y, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, (202 - 55) - plus_y, 552, (202 - 55) - plus_y)
        p.drawString(390, (190 - 55) - plus_y, "Punong Barangay")

        footer_text = 110
        
    draw_header()
    y_position -= line_height

    return p

def report_body_FileAction(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    # Frame = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "frame.png")
    p.drawImage(brgy_logo, 120, 200, width=380, height=380) #brgy logo
    # p.drawImage(Frame, 120, 273, width=A4[0], height=A4[1]) #Frame
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 100, y_position + 20, width=400, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    fileaction = FileAction.objects.get(pk=pk)
    # resident = brgyclearance.resident
    current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(current_date.day)
    fileaction_date_utc = fileaction.date_created.replace(tzinfo=pytz.UTC)
    fileaction_date_local = fileaction.date_created.astimezone(pytz.timezone('Asia/Manila'))
    # Fetch all complainants related to the blotter
    complainants_list = fileaction.case_no.blotter.complainants.all()
    complainants_text = "\n".join(str(complainant) for complainant in complainants_list)
    respondents_list = fileaction.case_no.blotter.respondents.all()
    respondents_text = "\n".join(str(respondents) for respondents in respondents_list)
    plus_y = 0
    title = 0
    if complainants_list.count() > 1:
        plus_y += 10 * (complainants_list.count()-1)
        title += 10 * (complainants_list.count())
        print(plus_y)
    if respondents_list.count() > 1:
        plus_y += 10 * (respondents_list.count()-1)
        title += 10 * (complainants_list.count())
        print(plus_y)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        p.setLineWidth(2)
        p.line(50, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 50, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        # p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        content_text = f"""<b>{complainants_text}</b>
        <b></b>
        Complainant/s

        <b><u>-against-</u></b>

        <b>{respondents_text}</b>
        <b></b> 
        Respondent/s


        This is to certify that:

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;1. The respondent was summoned three times but of no compliance.
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2. There had been several scheduled confrontations made between both parties but never settled.
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3. Therefore, the corresponding complaint for the dispute is being endorsed to Higher Court / other concerned government Office.

        Made this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(current_date.month)}</b></u>, <u><b>{current_date.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'CustomJustified',
            parent=styles['BodyText'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 510, 800, justified_style)

        p.setFont("Helvetica-Bold", 15)
        p.drawString(200, 465 - title, 'CERTIFICATE TO FILE ACTION')

        p.setFont("Helvetica-Bold", 13)
        p.drawString(340, 620, f'Barangay Case No.: {fileaction.case_no}')
        
        p.line(453, 618 - plus_y, 510, 618 - plus_y)
        # add_signature(p, "media/item_images/cap_esig-fotor.png", 400, 200 - 20, 120, 50)
        p.drawString(394, (220 - 20) - (plus_y), f'ROMEL FLORES')
        p.line(382, (232 - 35) - plus_y, 510, (232 - 35) - plus_y)
        p.drawString(390, (220 - 35) - plus_y, "Pangkat Secretary")

        # add_signature(p, "media/item_images/cap_esig-fotor.png", 400, 200 - 20, 120, 50)
        
        p.drawString(80, (130 - 20) - plus_y, f'Hon. AARON ROBERT A. BINARAO')
        p.line(70, (132 - 25) - plus_y, 313, (132 - 25) - plus_y)
        p.drawString(138, (130 - 35) - plus_y, "Pangkat Chairman")

        p.setFont("Helvetica", 13)
        p.drawString(50, 150 - plus_y, f'Attested:')
        footer_text = 110

    draw_header()
    y_position -= line_height

    return p

def report_body_brgyClearance(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")
    
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    brgyclearance = BrgyClearance.objects.get(pk=pk)
    resident = brgyclearance.resident
    # current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(brgyclearance.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;I hereby certify that the stated name below resides at <u>{resident.house_no}</u>, Ugac Sur, Tuguegarao City, Cagayan for six (6) consecutive months and/over.
        
        <b>First Name: <u>{resident.f_name}</u>
        Middle Name: <u>{resident.m_name}</u>
        Last Name: <u>{resident.l_name}</u>
        Date of Birth: <u>{resident.birth_date}</u>
        Place of birth: <u>{resident.birth_place}</u>
        Civil Status: <u>{resident.civil_status}</u>
        Gender: <u>{resident.gender}</u></b>

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certification is issued upon the request of above mentioned name person for whatever purpose/s it may serve.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(brgyclearance.date_created.month)}</b></u>, <u><b>{brgyclearance.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.  
        
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'CustomJustified',
            parent=styles['BodyText'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)
        p.setFont("Helvetica", 8.25)
        p.setStrokeColor(colors.black)
        p.rect(430, 460, 100, 80)
        p.drawString(420, 430, "Applicant's signature/Thumb mark")
        p.line(400, 440, 560, 440)

        # p.setFont("Helvetica", 8.25)
        # p.drawString(290, 250, "Recommending Approval:")
        # p.setFont("Helvetica", 10)
        # p.drawString(370, 210, "Barangay Secretary")
        # p.line(330, 220, 500, 220)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 200, 80, 80)
        p.drawString(340, 190, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 202 - 15, 552, 202 - 15)
        p.drawString(390, 190 - 15, "Punong Barangay")

        footer_text = 110
        # p.drawString(205, footer_text, f"Paid under O.R. No.:{brgyclearance.or_no}")
        # p.drawString(205, footer_text - 12, f"Amount Paid:{brgyclearance.or_amount}")
        # p.drawString(205, footer_text - 24, f"Date:{brgyclearance.or_date}")
        # p.drawString(205, footer_text - 36, f"CTC No.:{brgyclearance.ctc}")
        # p.drawString(205, footer_text - 48, f"Amount Paid:{brgyclearance.ctc_amount}")
        # p.drawString(205, footer_text - 60, f"Date:{brgyclearance.ctc_date}")

        
        
    draw_header()
    y_position -= line_height

    return p

def report_body_brgyCertificate(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")  
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    brgyCert = BrgyCertificate.objects.get(pk=pk)
    resident = brgyCert.resident
    current_date = datetime.now()
    formatted_day = get_day_with_suffix(brgyCert.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        # p.setFont("Helvetica-Bold", 13) 
        # p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        # p.setFont("Helvetica-Bold", 12)
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b> <b><u>{brgyCert.resident}</u></b>, of legal age, <b><u>{resident.civil_status}</u></b>, is a bona-fide resident of <b><u>{resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certifies further that <b><u>{brgyCert.resident}</u></b> is a law abiding citizen of the Barangay and possesses good moral character.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(brgyCert.date_created.month)}</b></u>, <u><b>{brgyCert.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        
        <b>PURPOSE: <u>{brgyCert.purpose}</u></b>
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 220, 80, 70)
        p.drawString(340, 215 - 5, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212 - 5, 552, 212 - 5)
        p.drawString(390, 200 -5, "Punong Barangay")
        footer_text = 82
        p.drawString(205, footer_text, f"Clearance Fee: {brgyCert.or_amount}")
        p.drawString(205, footer_text - 12, f"Receipt No.: {brgyCert.or_no}")
        p.drawString(205, footer_text - 24, f"Date: {brgyCert.or_date}")
        p.drawString(205, footer_text - 36, f"Community Tax No.: {brgyCert.ctc}")
        p.drawString(205, footer_text - 48, f"Date Issued: {brgyCert.ctc_date}")
        p.drawString(205, footer_text - 60, f"Place Issued: {brgyCert.place_issued}")
        p.setFont("Helvetica", 7)
        p.drawCentredString(480, footer_text - 20, ": NOT VALID FOR RENEWAL OF MAYOR'S PERMIT")
    draw_header()
    y_position -= line_height

    return p

def report_body_deathCert(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")  
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    deathCert = DeathClaimCertificate.objects.get(pk=pk)
    resident = deathCert.resident
    current_date = datetime.now()
    formatted_day = get_day_with_suffix(deathCert.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        # p.setFont("Helvetica-Bold", 13) 
        # p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        # p.setFont("Helvetica-Bold", 12)
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b> <b><u>{brgyCert.resident}</u></b>, of legal age, <b><u>{resident.citizenship}</u></b>, is a bona-fide resident of <b><u>{resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certifies further that <b><u>{brgyCert.resident}</u></b> is a law abiding citizen of the Barangay and possesses good moral character.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(brgyCert.date_created.month)}</b></u>, <u><b>{brgyCert.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        
        <b>PURPOSE: <u>{brgyCert.purpose}</u></b>
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 400, 220, 120, 100)
        p.drawString(340, 215, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212, 552, 212)
        p.drawString(390, 200, "Punong Barangay")
        footer_text = 82
        p.drawString(205, footer_text, f"Clearance Fee: {brgyCert.or_amount}")
        p.drawString(205, footer_text - 12, f"Receipt No.: {brgyCert.or_no}")
        p.drawString(205, footer_text - 24, f"Date: {brgyCert.or_date}")
        p.drawString(205, footer_text - 36, f"Community Tax No.: {brgyCert.ctc}")
        p.drawString(205, footer_text - 48, f"Date Issued: {brgyCert.ctc_date}")
        p.drawString(205, footer_text - 60, f"Place Issued: {brgyCert.place_issued}")
        p.setFont("Helvetica", 7)
        p.drawCentredString(480, footer_text - 20, ": NOT VALID FOR RENEWAL OF MAYOR'S PERMIT")
    draw_header()
    y_position -= line_height

    return p

def report_body_tribal(p, y_position, line_height, pk):
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    tribal = CertTribal.objects.get(pk=pk)
    resident = tribal.resident
    current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(current_date.day)
    p.setStrokeColor(colors.black)  # Set the frame color
    p.rect(30, 40, 530, 655)
    def draw_header():
        p.setFont("Helvetica-Bold", 13) 
        p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        p.setFont("Helvetica-Bold", 12)
        p.line(30, y_position + 80, 560, y_position + 80)
        p.line(40, y_position + 77, 550, y_position + 77)     
        p.setFont("Times-Bold", 17)
        p.drawString(210, y_position + 25, "CERTIFICATE OF TRIBAL MEMBERSHIP")
        p.line(200, y_position + 20, 560, y_position + 20) 
        p.line(200, 695, 200, 40)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        
        p.setFont("Helvetica", 11.25)
        p.drawString(205, y_position, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        
        content_lines = [
            f"This is to certify that, Mr/Mrs. {tribal.resident}, 23 years old, of legal age, {resident.civil_status} and a resident of Camasi, Peñablanca, Cagayan, {resident.house_no.purok} Belongs to {tribal.tribe} of INDIGENOUS CULTURAL COMMUNITTIES / INDIGENOUS PEOPLE.",
            f"This is to certify further that {tribal.mother} mother of {tribal.resident} as well as their ancestors are all recognized members of {tribal.tribe} known to be natives of Camasi Peñablanca, Cagayan.",
            f"Issued this {formatted_day} day of {month_names.get(current_date.month)}, {current_date.year}. at Barangay Camasi, Peñablanca, Cagayan.",
        ]
        indentation = "              "     
        text = p.beginText(170, y)
        text.setFont("Helvetica", 11.25)
        max_width = 355
        # Write wrapped text to the canvas
        for line in content_lines:
            words = line.split()  # Split the line into words
            if not words:
                continue  # Skip empty lines
            current_line = indentation  # Start with the first word
            for word in words[0:]:
                test_line = current_line + " " + word
                width = p.stringWidth(test_line, "Helvetica", 11.25)
                if width <= max_width:
                    current_line = test_line  # Add word if within width
                else:
                    p.setFont("Helvetica", 11.25)
                    p.drawString(x, y, current_line)  # Draw the line
                    y -= line_height  # Move to the next line
                    current_line = word  # Start a new line with the current word
            p.drawString(x, y, current_line)
            y -= 30
        # Add the content lines to the TextObject
        # for line in content_lines:
        #     text.textLine(line)
        
        # Draw the TextObject on the canvas
        p.drawText(text)

        p.setStrokeColor(colors.black)
        p.rect(400, 300, 100, 80)
        p.drawString(405, 290, "Right Thumbmark")
        p.line(370, 270, 530, 270)

        p.setFont("Helvetica", 8.25)
        p.drawString(290, 250, "Recommending Approval:")
        p.setFont("Helvetica", 10)
        p.drawString(370, 210, "Barangay Secretary")
        p.line(330, 220, 500, 220)

        p.setFont("Helvetica", 8.25)
        p.drawString(290, 180, "APPROVED:")
        p.setFont("Helvetica", 10)
        p.drawString(375, 150, "Punong Barangay")
        p.line(330, 160, 500, 160)

        footer_text = 110
        p.drawString(205, footer_text, f"Paid under O.R. No.:{tribal.or_no}")
        p.drawString(205, footer_text - 12, f"Amount Paid:{tribal.or_amount}")
        p.drawString(205, footer_text - 24, f"Date:{tribal.or_date}")
        p.drawString(205, footer_text - 36, f"CTC No.:{tribal.ctc}")
        p.drawString(205, footer_text - 48, f"Amount Paid:{tribal.ctc_amount}")
        p.drawString(205, footer_text - 60, f"Date:{tribal.ctc_date}")

        
        
    draw_header()
    y_position -= line_height

    return p

def report_body_goodmoral(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")  
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    goodmoral = CertGoodMoral.objects.get(pk=pk)
    resident = goodmoral.resident
    current_date = datetime.now()
    formatted_day = get_day_with_suffix(goodmoral.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        # p.setFont("Helvetica-Bold", 13) 
        # p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        # p.setFont("Helvetica-Bold", 12)
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>THIS IS TO CERTIFY</b> that <b><u>{goodmoral.resident}</u></b> is a resident of <b><u>{resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>THIS CERTIFIES</b> further that there are no complaints against him/her in our office, or pending case involving him/her that may affect his/ her reputation and no derogatory record.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>THIS CERTIFICATION</b> is Issued upon the request of above-named mention for {goodmoral.purpose} purposes.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>Issued this</b> <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(goodmoral.date_created.month)}</b></u>, <u><b>{goodmoral.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 380, 220, 80, 70)
        p.drawString(290, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(280, 212 - 3, 504, 212 - 3)
        p.drawString(340, 200 - 3, "Punong Barangay")
        footer_text = 82
        # p.drawString(205, footer_text, f"Clearance Fee: {goodmoral.or_amount}")
        # p.drawString(205, footer_text - 12, f"Receipt No.: {goodmoral.or_no}")
        # p.drawString(205, footer_text - 24, f"Date: {goodmoral.or_date}")
        # p.drawString(205, footer_text - 36, f"Community Tax No.: {goodmoral.ctc}")
        # p.drawString(205, footer_text - 48, f"Date Issued: {goodmoral.ctc_date}")
        # p.drawString(205, footer_text - 60, f"Place Issued: {goodmoral.place_issued}")
        # p.setFont("Helvetica", 7)
        # p.drawCentredString(480, footer_text - 20, ": NOT VALID FOR RENEWAL OF MAYOR'S PERMIT")
    draw_header()
    y_position -= line_height

    return p

def report_body_residency(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "residencyTitle.png")  
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    residency = CertResidency.objects.get(pk=pk)
    resident = residency.resident
    # current_date = datetime.now()
    formatted_day = get_day_with_suffix(residency.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b>, <b><u>{residency.resident}</u></b>, of legal age, <b><u>{resident.civil_status}</u></b>, is a bona-fide resident of <b><u>{resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certifies further that <b><u>{residency.resident}</u></b> is a resident of this Barangay since <b><u>{residency.resident_since}</u></b>.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certification is issued upon request of the above stated individual for <b><u>{residency.purpose}</u></b> purposes it may serve.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(residency.date_created.month)}</b></u>, <u><b>{residency.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        
        # Add indentation to the first line of each paragraph
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 220, 80, 70)
        p.drawString(340, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212 - 3, 552, 212 - 3)
        p.drawString(390, 200 - 3, "Punong Barangay")

        footer_text = 110
        # p.drawString(205, footer_text, f"Paid under O.R. No.:{residency.or_no}")
        # p.drawString(205, footer_text - 12, f"Amount Paid:{residency.or_amount}")
        # p.drawString(205, footer_text - 24, f"Date:{residency.or_date}")
        # p.drawString(205, footer_text - 36, f"CTC No.:{residency.ctc}")
        # p.drawString(205, footer_text - 48, f"Amount Paid:{residency.ctc_amount}")
        # p.drawString(205, footer_text - 60, f"Date:{residency.ctc_date}")
        
    draw_header()
    y_position -= line_height

    return p

def draw_paragraph(canvas, msg, x, y, max_width, max_height, style):
    
    # Custom style for justified text
    
    message = msg.replace('\n', '<br />')
    message = message.replace('indent', '       ')
    paragraph = Paragraph(message, style=style)
    w, h = paragraph.wrap(max_width, max_height)
    paragraph.drawOn(canvas, x, y - h)

def report_body_soloparent(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    p.drawImage(brgy_logo, 205, 273, width=380, height=380)  # Brgy logo

    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"

    soloparent = CertSoloParent.objects.get(pk=pk)
    resident = soloparent.resident
    # current_date = datetime.now()
    formatted_day = get_day_with_suffix(soloparent.date_created.day)

    def draw_header():
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
        p.setFont("Times-Bold", 20)
        p.drawString(220, y_position + 40, "  CERTIFICATE OF SOLO PARENT")

        x, y = 205, y_position
        p.setFont("Helvetica-Bold", 11.25)
        p.drawString(205, y_position, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height

        content_text = f"""<b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This is to certify that</b>, <u><b>{soloparent.resident}</b></u>, <u><b>{resident.civil_status}</b></u>, of legal age, <u><b>{resident.gender}</b></u>, and a resident of <u><b>{resident.house_no}</b></u> Ugac Sur, Tuguegaraco City, whose specimen signature appears below is a SOLO PARENT who solely provides parental / maternal care and support to her/his child/children.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certification is issued upon request of the above-named person for <u><b>{soloparent.purpose}</b></u> purposes.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(soloparent.date_created.month)}</b></u>, <u><b>{soloparent.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        # Add indentation to the first line of each paragraph
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'CustomJustified',
            parent=styles['BodyText'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        # p.drawString(x, y, paragraph)
        p.setFont("Helvetica-Bold", 13)
        
        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 220, 80, 70)
        p.drawString(340, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212 - 3, 552, 212 - 3)
        p.drawString(390, 200 - 3, "Punong Barangay")
    draw_header()
    y_position -= line_height

    return p

def report_body_indigency(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "IndigencyTitle.jpg")
    
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)

    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    indigency = CertIndigency.objects.get(pk=pk)
    resident = indigency.resident
    # current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(indigency.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():      
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)       
        p.drawString(205, y_position - 15, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b>, Mr/Mrs. <b><u>{indigency.resident}</u></b>, <b><u>{calculate_age(resident.birth_date)}</u></b>, <b><u>{resident.civil_status}</u></b>, of legal age, is a bonafide resident of <b><u>{resident.house_no}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certifies further that this person belongs to an indigent category of families in our barangay.
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;This certification is issued upon request of the above-named person for <b><u>{indigency.purpose}</u></b> purposes..
        
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(indigency.date_created.month)}</b></u>, <u><b>{indigency.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)
    
        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 220, 80, 70)
        p.drawString(340, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212 - 3, 552, 212 - 3)
        p.drawString(390, 200 - 3, "Punong Barangay")
        

        footer_text = 110
    def draw_text_with_underline(canvas, x, y, text, underline_offset):
        canvas.setFont("Helvetica", 11.25)
        canvas.drawString(x, y, text)  # Draw the line without the trailing space
        canvas.line(x, y - underline_offset, x + canvas.stringWidth(text, "Helvetica", 11.25), y - underline_offset)  # Draw the underline
    draw_header()
    y_position -= line_height

    return p

def report_body_businessClearance(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyClearanceTitle.jpg")  
    p.drawImage(brgy_logo, 205, 273, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    business_clearance = BusinessClearance.objects.get(pk=pk)
    business = business_clearance.business
    # current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(business_clearance.date_created.day)
    def draw_header():
        p.setLineWidth(2)
        p.line(225, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)   
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position

        content_text = f"""<b>Clearance is hereby issued to
        <u>{business.proprietor}</u>
        in connection with his/her application for Mayor's Permit with the
        registered business name
        <u>{business.business_name}</u>
        located at <u>{business.address}</u>
        Ugac Sur, Tuguegarao City.
        This Barangay Clearance is effective ony until <u>{business_clearance.effective_until}</u>.
        Issued this <u>{formatted_day}</u> day of <u>{month_names.get(business_clearance.date_created.month)}</u>, <u>{business_clearance.date_created.year}</u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.  
        </b>
        """
        # Add indentation to the first line of each paragraph
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'CustomJustified',
            parent=styles['BodyText'],
            alignment=1,  # 0 for left, 1 for center, 2 for right, 3 for justify
            fontSize=11.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 24,
        )
        draw_paragraph(p, content_text, x, y, 355, 800, justified_style)

        # p.drawString(x, y, paragraph)
        p.line(205, 352, 321, 352)
        p.drawString(205, 340, "   Signature of Applicant")
        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430, 220, 80, 70)
        p.drawString(340, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(330, 212 - 3, 552, 212 - 3)
        p.drawString(390, 200 - 3, "Punong Barangay")
        p.setFont("Helvetica", 10)

        footer_text = 80
        p.drawString(205, footer_text, f"Clearance Fee: {business_clearance.or_amount}")
        p.drawString(205, footer_text - 12, f"Receipt No.: {business_clearance.or_no}")
        p.drawString(205, footer_text - 24, f"Community Tax No.: {business_clearance.ctc}")
        p.drawString(205, footer_text - 36, f"Date Issued: {business_clearance.ctc_date}")
        p.drawString(205, footer_text - 48, f"Place Issued: {business_clearance.place_issued}")
        p.setFont("Helvetica", 7)
        p.drawCentredString(480, footer_text - 20, ": NOT VALID WITHOUT THE OFFICIAL RECEIPT")
    draw_header()
    y_position -= line_height

    return p

def report_body_businessCertificate(p, y_position, line_height, pk):
    current_file_path = os.path.abspath(__file__)
    image_filename = "LogoBackground.png"
    media_folder = os.path.join(os.path.dirname(current_file_path), '..', 'media', 'item_images')

    # Construct the full path to the image file
    brgy_logo = os.path.join(media_folder, image_filename)
    # brgy_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, image_filename)
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "summonTitle.png")
    Title = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", media_folder, "brgyCertTitle.jpg")  
    p.drawImage(brgy_logo, 120, 290, width=380, height=380) #brgy logo
    # p.drawImage(municipality_logo, 500, 273, width=380, height=380) #Municipality logo
    # p.drawImage(Title, 240, y_position + 20, width=300, height=40)
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    businessCert = BusinessCertificate.objects.get(pk=pk)
    current_date = datetime.now()
    formatted_day = get_day_with_suffix(businessCert.date_created.day)
    # p.setStrokeColor(colors.black)  # Set the frame color
    # p.rect(30, 40, 530, 655)
    def draw_header():
        # p.setFont("Helvetica-Bold", 13) 
        # p.drawCentredString(290, y_position + 50, "OFFICE OF THE SANGGUNIANG BARANGAY")       
        # p.setFont("Helvetica-Bold", 12)
        p.setLineWidth(2)
        p.line(50, y_position + 80, 560, y_position + 80)
        p.setLineWidth(1)
         # Set the width and height for the paragraph
        p.setFont("Times-Bold", 25)
        p.drawCentredString(290, y_position + 30, "C E R T I F I C A T I O N")
        x, y = 50, y_position  # Starting position
        p.setFont("Helvetica-Bold", 11.25)
        y -= line_height
        content_text = f"""&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This is to certify that</b> <b><u>{businessCert.business.proprietor}</u></b>, is a resident of <b><u>{businessCert.business.address}</u></b>, Ugac Sur, Tuguegarao City, Cagayan.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This certifies further that</b> <b><u>{businessCert.business.proprietor}</u></b> is a small business owner of <b><u>{businessCert.business}</u></b>.
    
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>This certification</b> is issued upon the request of the above-named person for <b>{businessCert.purpose}</b> purposes.

        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Issued this <u><b>{formatted_day}</b></u> day of <u><b>{month_names.get(businessCert.date_created.month)}</b></u>, <u><b>{businessCert.date_created.year}</b></u>. at Barangay Ugac Sur, Tuguegarao City, Cagayan.
        """
        styles = getSampleStyleSheet()
        justified_style = ParagraphStyle(
            'Justified',
            parent=styles['Normal'],
            alignment=0,  # 0 for left, 1 for center, 2 for right, 4 for justify
            fontSize=12.25,
            # firstLineIndent = 50, 
            LeftIndent=24,
            leading = 16,
        )
        draw_paragraph(p, content_text, x, y, 510, 800, justified_style)

        p.setFont("Helvetica-Bold", 12)
        add_signature(p, "media/item_images/cap_esig-fotor.png", 430-150, 220, 80, 70)
        p.drawString(340-150, 215 - 3, f'HON. AARON ROBERT A. BINARAO')
        p.line(330-150, 212 - 3, 552-150, 212 - 3)
        p.drawString(390-150, 200 - 3, "Punong Barangay")
        footer_text = 82
    draw_header()
    y_position -= line_height

    return p

def report_body_nonOperation(p, y_position, line_height, pk):
    def get_day_with_suffix(day):
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{day}{suffix}"
    nonoperation = CertNonOperation.objects.get(pk=pk)
    business = nonoperation.business
    # current_date = datetime.now().date()
    formatted_day = get_day_with_suffix(nonoperation.date_created.day)
    p.setStrokeColor(colors.black)  # Set the frame color
    p.rect(30, 40, 530, 655)
    def draw_header():
        p.setFont("Helvetica-Bold", 13) 
        p.drawCentredString(290, y_position + 50, "OFFICE OF THE BARANGAY CHAIRMAN")       
        p.setFont("Helvetica-Bold", 12)
        p.line(30, y_position + 80, 560, y_position + 80)
        p.line(40, y_position + 77, 550, y_position + 77)     
        p.setFont("Times-Bold", 20)
        p.drawString(205, y_position + 25, "CERTIFICATE OF NON-OPERATION")
        p.line(200, y_position + 20, 560, y_position + 20) 
        p.line(200, 695, 200, 40)
         # Set the width and height for the paragraph
        x, y = 205, y_position  # Starting position
        p.setFont("Helvetica", 11.25)
        p.drawString(205, y_position, "TO WHOM IT MAY CONCERN:")
        y -= line_height
        y -= line_height
        content_lines = [

            f"THIS IS TO CERTIFY THAT {nonoperation.business} a business enterprise with principal address {business.purok}, barangay Camasi, Peñablanca, represented by {business.proprietor} of legal age, {business.citizenship} citizen, with residence at {business.address} whose specimen signature appears, below, has not transacted any business and ceased operation since {nonoperation.ceased_date} up to present.",

            f"This certification is issued upon request of the above-named person for {nonoperation.purpose} purposes.",

            f"Issued this {formatted_day} day of {month_names.get(nonoperation.date_created.month)}, {nonoperation.date_created.year}. at Barangay Camasi, Peñablanca, Cagayan.",

        ]
        
        indentation = "              "     
        text = p.beginText(170, y)
        text.setFont("Helvetica", 11.25)
        max_width = 355
        # Write wrapped text to the canvas
        for line in content_lines:
            words = line.split()  # Split the line into words
            if not words:
                continue  # Skip empty lines
            current_line = indentation  # Start with the first word
            for word in words[0:]:
                test_line = current_line + " " + word
                width = p.stringWidth(test_line, "Helvetica", 11.25)
                if width <= max_width:
                    current_line = test_line  # Add word if within width
                else:
                    p.setFont("Helvetica", 11.25)
                    p.drawString(x, y, current_line)  # Draw the line
                    y -= 15  # Move to the next line
                    current_line = word  # Start a new line with the current word
            p.drawString(x, y, current_line)
            y -= 30


        p.drawString(210, 390, "Specimen Signature:")
        p.line(210, 370, 350, 370)

        p.setStrokeColor(colors.black)
        p.rect(400, 300, 100, 80)
        p.drawString(405, 290, "Right Thumbmark")
        p.line(370, 270, 530, 270)

        p.setFont("Helvetica", 8.25)
        p.drawString(290, 250, "Recommending Approval:")
        p.setFont("Helvetica", 10)
        p.drawString(370, 210, "Barangay Secretary")
        p.line(330, 220, 500, 220)

        p.setFont("Helvetica", 8.25)
        p.drawString(290, 180, "APPROVED:")
        p.setFont("Helvetica", 10)
        p.drawString(375, 150, "Punong Barangay")
        p.line(330, 160, 500, 160)

        footer_text = 110
        p.drawString(205, footer_text, f"Paid under O.R. No.:{nonoperation.or_no}")
        p.drawString(205, footer_text - 12, f"Amount Paid:{nonoperation.or_amount}")
        p.drawString(205, footer_text - 24, f"Date:{nonoperation.or_date}")
        p.drawString(205, footer_text - 36, f"CTC No.:{nonoperation.ctc}")
        p.drawString(205, footer_text - 48, f"Amount Paid:{nonoperation.ctc_amount}")
        p.drawString(205, footer_text - 60, f"Date:{nonoperation.ctc_date}")

        
        
    draw_header()
    y_position -= line_height

    return p

def pdf_report_view(pdf_buffer):
    # pdf_buffer = generate_pdf_report()
    # pdf_report_view(pdf_buffer)
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="resident_report.pdf"'
    
    return response

def pdf_ofw_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    purok = request.GET.get('purok')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_ofw(p, y_position, line_height, purok)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_JobSeekers(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_JobSeekers(p, y_position, line_height, pk)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_Oath(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_Oath(p, y_position, line_height, pk)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_deceased_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    purok = request.GET.get('purok')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_deceased(p, y_position, line_height, purok)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_business_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    purok = request.GET.get('purok')
    status = request.GET.get('status')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_business(p, y_position, line_height, purok, status)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_FileAction_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_FileAction_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_summon_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_Summon_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_Summon(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   
    report_body_Summon(p, y_position, line_height, pk)
    # report_brgyOfficials(p, 750, 50)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_FileAction(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   
    report_body_FileAction(p, y_position, line_height, pk)
    # report_brgyOfficials(p, 750, 50)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_resident_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    purok = request.GET.get('purok')
    residenden = request.GET.get('residenden')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body(p, y_position, line_height, purok, residenden)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_brgyClearance_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_brgyClearance_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_brgyCertificate_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_brgyCertificate_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_deathclaimcert_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_deathclaimcert_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_JobSeekers_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_JobSeekers_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certResidency_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_Residency_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certIndigency_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_Indigency_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certSoloParent_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_SoloParent_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certGoodMoral_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_GoodMoral_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certTribal_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_Tribal_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_certNonOperation_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_NonOperation_list(p, y_position, line_height, fromDate, toDate)
     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_businessClearance_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_businessClearance_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_businessCertificate_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    fromDate = request.GET.get('fromDate')
    toDate = request.GET.get('toDate')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_businessCertificate_list(p, y_position, line_height, fromDate, toDate)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_household_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    purok = request.GET.get('purok')
    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header1(p, y_position)   

    report_body_household(p, y_position, line_height, purok)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_blotter_list(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    p.setFont("Helvetica", 12)
    status = request.GET.get('status')
    y_position = 400  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header_landscape(p, y_position)   

    report_body_blotter(p, y_position, line_height, status)

     
    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_brgyClearance(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_brgyClearance(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 50)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_goodmoral(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_goodmoral(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 70)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_brgyCertificate(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_brgyCertificate(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 70)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_deathclaimcert(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header2(p, y_position)   
    report_body_deathclaimcert(p, y_position, line_height, pk)
    # report_brgyOfficials(p, 750, 70)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_residency(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_residency(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 50)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_indigency(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_indigency(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 45)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_soloparent(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_soloparent(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 50)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_tribal(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_tribal(p, y_position, line_height, pk)
    report_brgyOfficials(p, y_position, 110)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_businessClearance(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_businessClearance(p, y_position, line_height, pk)
    report_brgyOfficials(p, 750, 70)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_businessCertificate(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header2(p, y_position)   
    report_body_businessCertificate(p, y_position, line_height, pk)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

def pdf_nonOperation(request, pk):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica", 12)   

    y_position = 650  # Starting Y position for the first line
    line_height = 20  # Height of each line  

    report_header(p, y_position)   
    report_body_nonOperation(p, y_position, line_height, pk)
    report_brgyOfficials(p, y_position, 110)

    p.save()
    buffer.seek(0)
    return pdf_report_view(buffer)

@login_required
def brgy_list(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    brgy = Brgy.objects.all()
    return render(request, 'brgy/brgyList.html', {'brgy': brgy, 'has_admin_permission': has_admin_permission})

@login_required
def BlotterList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    blotter = Blotter.objects.all().order_by("-date_created")
    return render(request, 'blotter/BlotterList.html', {'blotter': blotter, 'has_admin_permission': has_admin_permission})

@login_required
def JobSeekersList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    jobseekers = JobSeekers.objects.annotate(
        age=ExpressionWrapper(
            date.today().year - F('resident__birth_date__year') - 
            Case(
                When(
                    resident__birth_date__month__gt=date.today().month,
                    then=Value(1)
                ),
                When(
                    resident__birth_date__month=date.today().month,
                    resident__birth_date__day__gt=date.today().day,
                    then=Value(1)
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            output_field=IntegerField()
        )
    ).order_by('-id')
    return render(request, 'jobseekers/JobSeekersList.html', {'jobseekers': jobseekers, 'has_admin_permission': has_admin_permission})

@login_required
def BrgyClearanceList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    brgyclearance = BrgyClearance.objects.all().order_by('-id')
    return render(request, 'brgyclearance/BrgyClearanceList.html', {'brgyclearance': brgyclearance, 'has_admin_permission': has_admin_permission})

@login_required
def BrgyCertificateList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    brgycertificate = BrgyCertificate.objects.all().order_by('-id')
    return render(request, 'brgyclearance/BrgyCertList.html', {'brgycertificate': brgycertificate, 'has_admin_permission': has_admin_permission})

@login_required
def DeathClaimCertificateList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    deathclaimCert = DeathClaimCertificate.objects.all().order_by('-id')
    return render(request, 'deceased/DeathClaimCertificateList.html', {'deathclaimCert': deathclaimCert, 'has_admin_permission': has_admin_permission})

@login_required
def CertIndigencyList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    certindigency = CertIndigency.objects.all().order_by('-id')
    return render(request, 'certindigency/CertIndigencyList.html', {'certindigency': certindigency, 'has_admin_permission': has_admin_permission})

@login_required
def CertResidencyList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    certresidency = CertResidency.objects.all().order_by('-id')
    return render(request, 'certresidency/CertResidencyList.html', {'certresidency': certresidency, 'has_admin_permission': has_admin_permission})

@login_required
def CertSoloParentList(request):   
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')   
    certsoloparent = CertSoloParent.objects.all().order_by('-id')
    return render(request, 'certsoloparent/CertSoloparentList.html', {'certsoloparent': certsoloparent, 'has_admin_permission': has_admin_permission})

@login_required
def CertNonOperationList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')   
    certnonoperation = CertNonOperation.objects.all().order_by('-id')
    return render(request, 'certnonoperation/CertNonoperationList.html', {'certnonoperation': certnonoperation, 'has_admin_permission': has_admin_permission})

@login_required
def CertGoodMoralList(request):   
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')   
    certgoodmoral = CertGoodMoral.objects.all().order_by('-id')
    return render(request, 'certgoodmoral/CertGoodmoralList.html', {'certgoodmoral': certgoodmoral, 'has_admin_permission': has_admin_permission})

@login_required
def CertTribalList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    tribal = CertTribal.objects.all().order_by('-id')
    return render(request, 'certtribal/CertTribalList.html', {'tribal': tribal, 'has_admin_permission': has_admin_permission})

@login_required
def BusinessCertificateList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    businesscert = BusinessCertificate.objects.all().order_by('-id')
    return render(request, 'businessclearance/BusinessCertList.html', {'businesscert': businesscert, 'has_admin_permission': has_admin_permission})

@login_required
def BusinessClearanceList(request):      
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    businessclearance = BusinessClearance.objects.all().order_by('-id')
    return render(request, 'businessclearance/BusinessClearanceList.html', {'businessclearance': businessclearance, 'has_admin_permission': has_admin_permission})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def BusinessList(request):   
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')   
    business = Business.objects.all()
    purok_list= Purok.objects.all().order_by("purok_name") 
    return render(request, 'business/BusinessList.html', {'business': business, 'purok_list': purok_list, 'has_admin_permission': has_admin_permission})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def PurokList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    purok = Purok.objects.all()
    return render(request, 'purok/PurokList.html', {'purok': purok, 'has_admin_permission': has_admin_permission})

@login_required
def ResidentList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    purok_list= Purok.objects.all().order_by("purok_name") 
    
    # page = request.GET.get('page', 1)
    resident = Resident.objects.values('pk', 'f_name', 'm_name', 'l_name', 'gender', 'house_no__purok__purok_name', 'house_no__house_no', 'house_no__address').annotate(
        age=ExpressionWrapper(
            date.today().year - F('birth_date__year') - 
            Case(
                When(
                    birth_date__month__gt=date.today().month,
                    then=Value(1)
                ),
                When(
                    birth_date__month=date.today().month,
                    birth_date__day__gt=date.today().day,
                    then=Value(1)
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            output_field=IntegerField()
        )
    ).order_by("l_name")

    # Search functionality
    last_name = request.GET.get('lastname', '')
    first_name = request.GET.get('firstname', '')
    middle_name = request.GET.get('middlename', '')
    query_filters = Q()
    # query_filters |= Q(l_name__iexact=last_name, f_name__iexact=first_name, m_name__iexact=middle_name)
    if last_name:
        query_filters &= Q(l_name__icontains=last_name)
    if first_name:
        query_filters &= Q(f_name__icontains=first_name)
    if middle_name:
        query_filters &= Q(m_name__icontains=middle_name)
    # residents = resident.filter(l_name__icontains=last_name, m_name__icontains=first_name, f_name__icontains=middle_name)    
    residents = resident.filter(query_filters)

    residents_per_page = 10
    paginator = Paginator(residents, residents_per_page)
    page = request.GET.get('page', 1)

    try:
        # Retrieve the requested page
        residents = paginator.page(page)
    except PageNotAnInteger:
        # If the page parameter is not an integer, show the first page
        residents = paginator.page(1)
    except EmptyPage:
        # If the requested page is out of range, show the last page
        residents = paginator.page(paginator.num_pages)   
    return render(request, 'resident/ResidentList.html', {'resident': residents,'purok_list': purok_list, 'has_admin_permission': has_admin_permission, 'last_name': last_name, 'first_name': first_name, 'middle_name': middle_name})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def HouseholdList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    # resident = Resident.objects.exclude(house_no__isnull=True)
    purok_list = Purok.objects.all().order_by("purok_name") 
    # members = resident.values('house_no').annotate(total_count=Count('id')).order_by('house_no')
    household = Household.objects.all().order_by("purok", "address", "house_no")
    member_count = household.annotate(resident_count=Count('resident'))
    
    # Search functionality
    house_no = request.GET.get('houseno', '')
    street_ = request.GET.get('street', '')
    purok_ = request.GET.get('purok', '')
    query_filters = Q()
 
    if house_no:
        query_filters &= Q(house_no__icontains=house_no)
    if street_:
        query_filters &= Q(address__icontains=street_)
    if purok_:
        query_filters &= Q(purok__purok_name__icontains=purok_)
   
    households = member_count.filter(query_filters)

    households_per_page = 10
    paginator = Paginator(households, households_per_page)
    page = request.GET.get('page', 1)

    try:
        # Retrieve the requested page
        households = paginator.page(page)
    except PageNotAnInteger:
        # If the page parameter is not an integer, show the first page
        households = paginator.page(1)
    except EmptyPage:
        # If the requested page is out of range, show the last page
        households = paginator.page(paginator.num_pages)
    
    return render(request, 'household/HouseholdList.html', {'member_count': member_count, 'households': households, 'purok_list': purok_list, 'household': households, 'has_admin_permission': has_admin_permission, 'house_no': house_no, 'street_': street_, 'purok_': purok_})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def filter_resident(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    purok = request.GET.get('purok')
    
    if purok != '':
        resident = Resident.objects.filter(purok=purok)  
    else:
        resident = Resident.objects.all()
       
    try:   
        # Prepare the order items data as a list of dictionaries
        order_items_data = []
        for r in resident:
            order_items_data.append({
                'pk': r.pk,
                'name': r.f_name + ' ' + r.m_name + ' ' + r.l_name,
                'gender': r.gender,
                'kontak': r.phone_number,
                'address': r.address,
            })
        # print(order_items_data)
        return JsonResponse({'residents': order_items_data, 'has_admin_permission': has_admin_permission} )
    
    except Resident.DoesNotExist:
        return JsonResponse({'residents': []})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def get_members(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    house_id = request.GET.get('house_id')
    
    try:
        resident = Resident.objects.filter(house_no=house_id).order_by('id')
        
        residents = []
        for r in resident:
            residents.append({
                'id': r.id,
                'name': r.l_name + ', ' + r.f_name + ' ' + r.m_name,
                'gender': r.gender,
                'age': f"{calculate_age(r.birth_date)}",
                'head': f"{r.head}",
            })
        return JsonResponse({'residents': residents, 'has_admin_permission': has_admin_permission} )
    
    except Resident.DoesNotExist:
        return JsonResponse({'residents': []})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def DeceasedList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    deceased = Deceased.objects.all()
    purok_list= Purok.objects.all().order_by("purok_name") 
    return render(request, 'deceased/DeceasedList.html', {'deceased': deceased, 'purok_list': purok_list, 'has_admin_permission': has_admin_permission})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def OfwList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')     
    ofw = Ofw.objects.all()
    purok_list= Purok.objects.all().order_by("purok_name") 
    return render(request, 'ofw/OfwList.html', {'ofw': ofw, 'purok_list': purok_list, 'has_admin_permission': has_admin_permission})

@login_required
def Edit_brgy(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    brgy_count  = Brgy.objects.all().count()

    if brgy_count > 0:
        brgy = Brgy.objects.first()       
        if request.method == 'POST':
            form = BrgyForm(request.POST, request.FILES, instance=brgy)
            if form.is_valid():
                form.save()
                return redirect('Edit_brgy')
        else:
            form = BrgyForm(instance=brgy)

    else:
        if request.method == 'POST':
            form = BrgyForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('Edit_brgy')
        else:
            form = BrgyForm()
    return render(request, 'brgy/Edit_brgy.html', {'form': form, 'has_admin_permission': has_admin_permission})

@login_required
def SummonList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    summon = Summon.objects.all()
    return render(request, 'Summon/SummonList.html', {'summon': summon, 'has_admin_permission': has_admin_permission})

@login_required
def FileActionList(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    fileaction = FileAction.objects.all()
    return render(request, 'Summon/FileActionList.html', {'fileaction': fileaction, 'has_admin_permission': has_admin_permission})

@login_required
def brgy_list(request, pk):
    try:
        brgy = get_object_or_404(Brgy, pk=pk)
        if request.method == 'POST':
            form = BrgyForm(request.POST, request.FILES, instance=brgy)
            if form.is_valid():
                form.save()
                return redirect('brgy_list')
        else:
            form = BrgyForm(instance=brgy)
        return render(request, 'brgy/Edit_brgy.html', {'form': form, 'brgy': brgy})
    except Http404:  
        if request.method == 'POST':
            form = BrgyForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('brgy_list')
        else:
            form = BrgyForm()
        return render(request, 'brgy/Edit_brgy.html', {'form': form})
    
@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdPurok(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')     
    try:
        purok = get_object_or_404(Purok, pk=pk)
    except Http404:
        purok=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=purok,
        form_class=PurokForm, 
        template='purok/AdEdPurok.html',
        redirect_to='PurokList',
        additional_context=additional_context
    )

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdHousehold(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')        
    try:
        household = get_object_or_404(Household, pk=pk)
    except Http404:
        household=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=household,
        form_class=HouseholdForm, 
        template='household/AdEdHousehold.html',
        redirect_to='HouseholdList',
        additional_context=additional_context
    )

@login_required
def AdEdJobSeekers(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        jobseekers = get_object_or_404(JobSeekers, pk=pk)
    except Http404:
        jobseekers=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=jobseekers,
        form_class=JobSeekersForm, 
        template='jobseekers/AdEdJobSeekers.html',
        redirect_to='JobSeekersList',
        additional_context=additional_context
    )

@login_required
def AdEdBrgyClearance(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        brgyclearance = get_object_or_404(BrgyClearance, pk=pk)
    except Http404:
        brgyclearance=None

    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=brgyclearance,
        form_class=BrgyClearanceForm, 
        template='brgyclearance/AdEdBrgyClearance.html',
        redirect_to='BrgyClearanceList',
        additional_context=additional_context
    )

@login_required    
def AdEdBrgyCertificate(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        brgycertificate = get_object_or_404(BrgyCertificate, pk=pk)
    except Http404:
        brgycertificate=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=brgycertificate,
        form_class=BrgyCertificateForm, 
        template='brgyclearance/AdEdBrgyCert.html',
        redirect_to='BrgyCertificateList',
        additional_context=additional_context
    )

@login_required    
def AdEdDeathClaimCertificate(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        deathclaimCertificate = get_object_or_404(DeathClaimCertificate, pk=pk)
    except Http404:
        deathclaimCertificate=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=deathclaimCertificate,
        form_class=DeathClaimCertificateForm, 
        template='deceased/AdEdDeathclaimCertificate.html',
        redirect_to='DeathClaimCertificateList',
        additional_context=additional_context
    )

@login_required    
def AdEdTribal(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        tribal = get_object_or_404(CertTribal, pk=pk)
    except Http404:
        tribal=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=tribal,
        form_class=CertTribalForm, 
        template='certtribal/AdEdCertTribal.html',
        redirect_to='CertTribalList',
        additional_context=additional_context
    )

@login_required
def AdEdCertGoodMoral(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        certgoodmoral = get_object_or_404(CertGoodMoral, pk=pk)
    except Http404:
        certgoodmoral=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=certgoodmoral,
        form_class=CertGoodMoralForm, 
        template='certgoodmoral/AdEdCertGoodmoral.html',
        redirect_to='CertGoodMoralList',
        additional_context=additional_context
    )

@login_required
def AdEdCertResidency(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        certresidency = get_object_or_404(CertResidency, pk=pk)
    except Http404:
        certresidency=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=certresidency,
        form_class=CertResidencyForm, 
        template='certresidency/AdEdCertResidency.html',
        redirect_to='CertResidencyList',
        additional_context=additional_context
    )

@login_required
def AdEdCertIndigency(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        certindigency = get_object_or_404(CertIndigency, pk=pk)
    except Http404:
        certindigency=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=certindigency,
        form_class=CertIndigencyForm, 
        template='certindigency/AdEdCertIndigency.html',
        redirect_to='CertIndigencyList',
        additional_context=additional_context
    )

@login_required
def AdEdCertSoloParent(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        certsoloparent = get_object_or_404(CertSoloParent, pk=pk)
    except Http404:
        certsoloparent=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=certsoloparent,
        form_class=CertSoloParentForm, 
        template='certsoloparent/AdEdCertSoloparent.html',
        redirect_to='CertSoloParentList',
        additional_context=additional_context
    )

@login_required
def AdEdCertNonOperation(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        certnonoperation = get_object_or_404(CertNonOperation, pk=pk)
    except Http404:
        certnonoperation=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=certnonoperation,
        form_class=CertNonOperationForm, 
        template='certnonoperation/AdEdCertNonoperation.html',
        redirect_to='CertNonOperationList',
        additional_context=additional_context
    )

@login_required
def AdEdBusinessClearance(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        businessclearance = get_object_or_404(BusinessClearance, pk=pk)
    except Http404:
        businessclearance=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=businessclearance,
        form_class=BusinessClearanceForm, 
        template='businessclearance/AdEdBusinessClearance.html',
        redirect_to='BusinessClearanceList',
        additional_context=additional_context
    )

@login_required
def AdEdBusinessCertificate(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        businesscert = get_object_or_404(BusinessCertificate, pk=pk)
    except Http404:
        businesscert=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=businesscert,
        form_class=BusinessCertificateForm, 
        template='businessclearance/AdEdBusinessCert.html',
        redirect_to='BusinessCertificateList',
        additional_context=additional_context
    )

@login_required
def AdEdBlotter(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        blotter = get_object_or_404(Blotter, pk=pk)
        if request.method == 'POST':
            form = BlotterForm(request.POST, request.FILES, instance=blotter)
            if form.is_valid():
                form.save()
                return redirect('BlotterList')
        else:
            initial = {
                'complainants': blotter.complainants.all(),
                'respondents': blotter.respondents.all()
            }
            form = BlotterForm(instance=blotter, initial=initial)
            
        return render(request, 'blotter/AdEdBlotter.html', {
            'form': form, 
            'blotter': blotter, 
            'has_admin_permission': has_admin_permission, 
        })
    except Http404:  
        if request.method == 'POST':
            form = BlotterForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('BlotterList')
        else:
            form = BlotterForm()
        return render(request, 'blotter/AdEdBlotter.html', {'form': form, 'has_admin_permission': has_admin_permission})

@login_required
def AdEdSummon(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        summon = get_object_or_404(Summon, pk=pk)
    except Http404:
        summon=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=summon,
        form_class=SummonForm, 
        template='Summon/AdEdSummon.html',
        redirect_to='SummonList',
        additional_context=additional_context
    )

@login_required
def AdEdFileAction(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features') 
    try:
        filecation = get_object_or_404(FileAction, pk=pk)
    except Http404:
        filecation=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=filecation,
        form_class=FileActionForm, 
        template='Summon/AdEdFileAction.html',
        redirect_to='FileActionList',
        additional_context=additional_context
    )

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdBusiness(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')  
    try:
        business = get_object_or_404(Business, pk=pk)
    except Http404:
        business=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=business,
        form_class=BusinessForm, 
        template='business/AdEdBusiness.html',
        redirect_to='BusinessList',
        additional_context=additional_context
    )

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdResident(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')  
    purok_list= Purok.objects.all().order_by("purok_name") 
    try:
        resident = get_object_or_404(Resident, pk=pk)
    except Http404:
        resident=None
    
    additional_context = {'purok_list': purok_list, 'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=resident,
        form_class=ResidentForm, 
        template='resident/AdEdResident.html',
        redirect_to='ResidentList',
        additional_context=additional_context
    )

@login_required
def filter_house_no(request, purok_id):
    
    house_no = Household.objects.filter(purok_id=purok_id).order_by("address", "house_no")
    house_no_json = list(house_no.values())
    return JsonResponse({'house_no': house_no_json})

@login_required
def AdEdBrgyOfficials(request):
    officials_count  = Brgy_Officials.objects.all().count()

    if officials_count > 0:
        officials = Brgy_Officials.objects.first()       
        if request.method == 'POST':
            form = brgyOfficialForm(request.POST, request.FILES, instance=officials)
            if form.is_valid():
                form.save()
                return redirect('AdEdBrgyOfficials')
        else:
            form = brgyOfficialForm(instance=officials)

    else:
        if request.method == 'POST':
            form = brgyOfficialForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return redirect('AdEdBrgyOfficials')
        else:
            form = brgyOfficialForm()
    return render(request, 'officials.html', {'form': form})

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdDeceased(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')  
    try:
        deceased = get_object_or_404(Deceased, pk=pk)
    except Http404:
        deceased=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=deceased,
        form_class=DeceasedForm, 
        template='deceased/AdEdDeceased.html',
        redirect_to='DeceasedList',
        additional_context=additional_context
    )

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def AdEdOfw(request, pk):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')  
    try:
        ofw = get_object_or_404(Ofw, pk=pk)
    except Http404:
        ofw=None
    
    additional_context = {'has_admin_permission': has_admin_permission}  # Add any additional context data here
    return AdEd(
        request,
        instance=ofw,
        form_class=OfwForm, 
        template='ofw/AdEdOfw.html',
        redirect_to='OfwList',
        additional_context=additional_context
    )

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_brgy(request, pk):
    if request.method == 'POST':
        brgy = get_object_or_404(Brgy, pk=pk)
        brgy.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_purok(request, pk):
    if request.method == 'POST':
        purok = get_object_or_404(Purok, pk=pk)
        purok.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_resident(request, pk):
    if request.method == 'POST':
        resident = get_object_or_404(Resident, pk=pk)
        #resident.delete()
        Resident.objects.all().delete()
        # resident.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_household(request, pk):
    if request.method == 'POST':
        household = get_object_or_404(Household, pk=pk)
        # household.delete()
        Household.objects.all().delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_deceased(request, pk):
    if request.method == 'POST':
        deceased = get_object_or_404(Deceased, pk=pk)
        deceased.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_ofw(request, pk):
    if request.method == 'POST':
        ofw = get_object_or_404(Ofw, pk=pk)
        ofw.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_blotter(request, pk):
    if request.method == 'POST':
        blotter = get_object_or_404(Blotter, pk=pk)
        blotter.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_business(request, pk):
    if request.method == 'POST':
        business = get_object_or_404(Business, pk=pk)
        business.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_brgyclearance(request, pk):
    if request.method == 'POST':
        brgyclearance = get_object_or_404(BrgyClearance, pk=pk)
        brgyclearance.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_brgycertificate(request, pk):
    if request.method == 'POST':
        brgycertificate = get_object_or_404(BrgyCertificate, pk=pk)
        brgycertificate.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_tribal(request, pk):
    if request.method == 'POST':
        tribal = get_object_or_404(CertTribal, pk=pk)
        tribal.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_businessclearance(request, pk):
    if request.method == 'POST':
        businessclearance = get_object_or_404(BusinessClearance, pk=pk)
        businessclearance.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_certgoodmoral(request, pk):
    if request.method == 'POST':
        certgoodmoral = get_object_or_404(CertGoodMoral, pk=pk)
        certgoodmoral.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_certindigency(request, pk):
    if request.method == 'POST':
        certindigency = get_object_or_404(CertIndigency, pk=pk)
        certindigency.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_certresidency(request, pk):
    if request.method == 'POST':
        certresidency = get_object_or_404(CertResidency, pk=pk)
        certresidency.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_certnonoperation(request, pk):
    if request.method == 'POST':
        certnonoperation = get_object_or_404(CertNonOperation, pk=pk)
        certnonoperation.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_certsoloparent(request, pk):
    if request.method == 'POST':
        certsoloparent = get_object_or_404(CertSoloParent, pk=pk)
        certsoloparent.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

@user_passes_test(lambda user: user.is_authenticated and has_custom_access(user))
@login_required
def Delete_jobseekers(request, pk):
    if request.method == 'POST':
        jobseekers = get_object_or_404(JobSeekers, pk=pk)
        jobseekers.delete()
        return JsonResponse({'message': 'Item deleted successfully.'})
    return JsonResponse({'message': 'Invalid request method.'}, status=400)

def import_residents(request):
    if request.method == 'POST' and request.FILES['file']:
        file = request.FILES['file']
        result = import_residents_from_excel(file)
        if result is True:
            message = 'Import successful'
        else:
            message = f'Import failed: {result}'
    else:
        message = 'Upload an Excel file'

    return render(request, 'import_residents.html', {'message': message})

@login_required
def SearchResident(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    resident = Resident.objects.annotate(
    is_respondent=Case(
        When(responses__isnull=False, then=Value(True)),
        default=Value(False),
        output_field=BooleanField()
    )).values(
        'pk',
        'f_name',
        'm_name',
        'l_name',
        'house_no__purok__purok_name',
        'house_no__house_no',
        'house_no__address',
        'is_respondent'
    ).order_by("l_name")

    # Search functionality
    last_name = request.GET.get('lastname', '')
    first_name = request.GET.get('firstname', '')
    middle_name = request.GET.get('middlename', '')
    query_filters = Q()
    # query_filters |= Q(l_name__iexact=last_name, f_name__iexact=first_name, m_name__iexact=middle_name)
    if last_name:
        query_filters &= Q(l_name__icontains=last_name)
    if first_name:
        query_filters &= Q(f_name__icontains=first_name)
    if middle_name:
        query_filters &= Q(m_name__icontains=middle_name)
    
    residents = resident.filter(query_filters)

    residents_per_page = 10
    paginator = Paginator(residents, residents_per_page)
    page = request.GET.get('page', 1)
    try:
        # Retrieve the requested page
        residents_page  = paginator.page(page)
    except PageNotAnInteger:
        # If the page parameter is not an integer, show the first page
        residents_page  = paginator.page(1)
    except EmptyPage:
        # If the requested page is out of range, show the last page
        residents_page  = paginator.page(paginator.num_pages)

    residents_list = list(residents_page.object_list)  
    
    response_data = {
        'residents': residents_list,
        'has_admin_permission': has_admin_permission,
        'has_previous': residents_page.has_previous(),
        'has_next': residents_page.has_next(),
        'current_page': residents_page.number,
        'num_pages': paginator.num_pages
    }
    return JsonResponse(response_data)

@login_required
def SearchDeceased(request):
    has_admin_permission = request.user.has_perm('BrgyApp.can_access_admin_features')
    resident = Deceased.objects.values().order_by("resident__l_name")

    # Search functionality
    last_name = request.GET.get('lastname', '')
    first_name = request.GET.get('firstname', '')
    middle_name = request.GET.get('middlename', '')
    query_filters = Q()
    # query_filters |= Q(l_name__iexact=last_name, f_name__iexact=first_name, m_name__iexact=middle_name)
    if last_name:
        query_filters &= Q(l_name__icontains=last_name)
    if first_name:
        query_filters &= Q(f_name__icontains=first_name)
    if middle_name:
        query_filters &= Q(m_name__icontains=middle_name)

    
    residents = resident.filter(query_filters)
    # print(f"residents: {residents}")

    residents_per_page = 10
    paginator = Paginator(residents, residents_per_page)
    page = request.GET.get('page', 1)
    try:
        # Retrieve the requested page
        residents_page  = paginator.page(page)
    except PageNotAnInteger:
        # If the page parameter is not an integer, show the first page
        residents_page  = paginator.page(1)
    except EmptyPage:
        # If the requested page is out of range, show the last page
        residents_page  = paginator.page(paginator.num_pages)

    residents_list = list(residents_page.object_list)  
    
    response_data = {
        'residents': residents_list,
        'has_admin_permission': has_admin_permission,
        'has_previous': residents_page.has_previous(),
        'has_next': residents_page.has_next(),
        'current_page': residents_page.number,
        'num_pages': paginator.num_pages
    }
    return JsonResponse(response_data)

def ajax_complainants(request):
    # Logic to fetch complainants data, for example:
    complainants = Resident.objects.all()  # Assuming Resident is your model
    data = [{'id': complainant.id, 'name': complainant.__str__} for complainant in complainants]
    return JsonResponse(data, safe=False)

def resident_search(request):
    if 'q' in request.GET:
        query = request.GET['q']
        residents = Resident.objects.search(query)
        items = [{'id': resident.id, 'text': str(resident)} for resident in residents]
        return JsonResponse({'items': items, 'total_count': len(items)})
    else:
        return JsonResponse({'items': [], 'total_count': 0})