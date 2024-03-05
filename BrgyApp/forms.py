from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User, Permission
from .models import Summon, BusinessCertificate, FileAction, CustomUser, DeathClaimCertificate, CertTribal, Brgy, Purok, Resident, Household, Deceased, Ofw, Blotter, Business, BrgyClearance, BusinessClearance, CertSoloParent, CertGoodMoral, CertIndigency, CertNonOperation, CertResidency, Brgy_Officials, JobSeekers, BrgyCertificate
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.forms import ModelChoiceField, ModelMultipleChoiceField

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(CustomPasswordChangeForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',  # Add your CSS classes here
                'placeholder': 'Enter ' + field.replace('_', ' ').capitalize(),
            })

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        fields = ('username', 'first_name', 'last_name')
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Username'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your First Name'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Last Name'})
    )

class SignupForm(UserCreationForm):
    ACCESS_LEVEL_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    access_level = forms.ChoiceField(
        choices=ACCESS_LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2', 'access_level')
        labels = {
            'access_level': 'Access Level',
        }
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Username'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your First Name'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Last Name'})
    )
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Password'})
    )
    password2 = forms.CharField(
        label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat your Password'})
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        access_level = self.cleaned_data.get('access_level')

        if commit:
            user.save()  # Save the user first to obtain an ID

            # Assign permissions based on access level
            if access_level == 'admin':
                admin_permission = Permission.objects.get(codename='can_access_admin_features')
                user.user_permissions.add(admin_permission)
                user.save()  # Save the user again to update permissions

        return user
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Password'})
    )

class BrgyForm(forms.ModelForm):
    class Meta:
        model = Brgy
        fields = ('brgy_name', 'municipality', 'description', 'image')
        widgets = {
            'brgy_name': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'municipality': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
            'class': 'form-control'
            }),
        }
    image = forms.ImageField(
        label="Photo",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )

class PurokForm(forms.ModelForm):
    class Meta:
        model = Purok
        fields = ('brgy', 'purok_name',)
        widgets = {
            'brgy': forms.Select(attrs={
            'class': 'form-select'
            }),
            'purok_name': forms.TextInput(attrs={
            'class': 'form-control'
            }),
        }

class ResidentForm(forms.ModelForm): 
    CIVIL_STATUS_CHOICES = (
        ('-----', '-----'),
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
        )
    Educaional_attainment_choices = (
        ('-----', '-----'),
        ("Elementary", "Elementary"),
        ("Secondary", "Secondary"),
        ("College / University Degree", "College / University Degree"),
        ("Vocational", "Vocational"),
        ("Masters degree", "Masters Degree"),
        ("Doctorate degree", "Doctorate Degree"),
        ("none","None")
    )
    Gender_choices = (
        ("Male", "Male"),
        ("Female", "Female"),
    )
    resident_type_choices = (
        ("Resident", "Resident"),
        ("Non-Resident", "Non-Resident"),
    )
    class Meta:
        
        model = Resident   
        fields = ('f_name', 'm_name', 'l_name',
                  'gender','house_no', 'head',
                  'phone_number', 'birth_date', 'birth_place',
                  'civil_status', 'religion', 'citizenship',
                  'profession', 'education', 'voter', 'precint_no', 
                  'solo_parent','pwd','fourps','indigent','resident_type', 'image',
                  'osy','isy',)
    
        widgets = {
                'house_no': forms.Select(attrs={
                'class': 'form-select'
                }),
            }

    f_name = forms.CharField(
        label="First Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter First Name',
            'oninput': 'this.value = this.value.toUpperCase();'
            })
    )
    m_name = forms.CharField(
        label="Middle Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter Middle Name',
            'oninput': 'this.value = this.value.toUpperCase();'
            })
    )
    l_name = forms.CharField(
        label="Last Name",
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter Last Name',
            'oninput': 'this.value = this.value.toUpperCase();'
            })
    )
    gender = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=Gender_choices,
    )
    phone_number = forms.CharField(
        label="Contact Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Phone Number'})
    )
    birth_date = forms.DateField(
        label="Date of Birth",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    birth_place = forms.CharField(
        label="Place of Birth",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Birth Place'})
    )
    civil_status = forms.ChoiceField(
        label="Civil Status",
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=CIVIL_STATUS_CHOICES,
    )
    religion = forms.CharField(
        label="Religion",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Religion'})
    )
    citizenship = forms.CharField(
        label="Citizenship",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Citizenship'})
    )
    profession = forms.CharField(
        label="Profession",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Profession'})
    )
    education = forms.CharField(
        label="Education",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Education'}),
        # choices=Educaional_attainment_choices,
    )
    voter = forms.BooleanField(
        label="Registered Voter",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    precint_no = forms.CharField(
        label="Precint No.",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Precint No.'})
    )
    solo_parent = forms.BooleanField(
        label="Solo Parent",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    pwd = forms.BooleanField(
        label="Person with Disability",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    fourps = forms.BooleanField(
        label="4ps",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    indigent = forms.BooleanField(
        label="Indigent",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    osy = forms.BooleanField(
        label="Out of School Youth",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    isy = forms.BooleanField(
        label="In School Youth",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    head = forms.BooleanField(
        label="Head of the Family",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    resident_type = forms.ChoiceField(
        label="Resident Type",
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=resident_type_choices,
    )
    # family_income = forms.DecimalField(
    #     label="Family Monthly Income",
    #     widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Family Income'})
    # )
    image = forms.ImageField(
        label="Photo",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )

    def clean_f_name(self):
        return self.cleaned_data['f_name'].upper()

    def clean_m_name(self):
        return self.cleaned_data['m_name'].upper()

    def clean_l_name(self):
        return self.cleaned_data['l_name'].upper()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default image if the instance doesn't have an image
        if not self.instance.image:
            self.fields['image'].initial = 'item_images/default.jpg'

class HouseholdForm(forms.ModelForm):

    housing_choice = (
        ('-', '-'),
        # ('1 - Salvage Materials)', '1 - Salvage Materials'),
        # ('2 - Light Materials', '2 - Light Materials'),
        # ('3 - Semi Concrete / Wood Materials', '3 - Semi Concrete / Wood Materials'),
        # ('4 - Concrete Materials', '4 - Concrete Materials'),
        ('1 - Salvage Materials(Owned))', '1 - Salvage Materials(Owned)'),
        ('1 - Salvage Materials(Shared)', '1 - Salvage Materials(Shared)'),
        ('2 - Light Materials(Owned)', '2 - Light Materials(Owned)'),
        ('2 - Light Materials(Shared)', '2 - Light Materials(Shared)'),
        ('3 - Semi Concrete / Wood Materials(Caretaker/Rented)', '3 - Semi Concrete / Wood Materials(Caretaker/Rented)'),  
        ('3 - Semi Concrete / Wood Materials(Owned)', '3 - Semi Concrete / Wood Materials(Owned)'),
        ('3 - Semi Concrete / Wood Materials(Shared)', '3 - Semi Concrete / Wood Materials(Shared)'),
        ('4 - Concrete Materials(Owned)', '4 - Concrete Materials(Owned)'),
        ('4 - Concrete Materials(Shared)', '4 - Concrete Materials(Shared)'),     
        )
    
    water_choice = (
        ('-', '-'),
        # ('1 - Deep Well', '1 - Deep Well'),
        # ('2 - Water Pump', '2 - Water Pump'),
        # ('3 - Nawasa', '3 - Nawasa'),
        ('1 - Deep Well(Owned)', '1 - Deep Well(Owned)'),
        ('1 - Deep Well(Shared)', '1 - Deep Well(Shared)'),
        ('2 - Water Pump(Owned)', '2 - Water Pump(Owned)'),
        ('2 - Water Pump(Shared)', '2 - Water Pump(Shared)'),
        ('3 - Nawasa(Owned)', '3 - Nawasa(Owned)'),
        ('3 - Nawasa(Shared)', '3 - Nawasa(Shared)'),    
        )
    
    lighting_choice = (
        ('-', '-'),
        ('1 - No Electricity', '1 - No Electricity'),
        # ('2 - CAGELCO', '2 - CAGELCO'),
        ('2 - CAGELCO(Owned)', '2 - CAGELCO(Owned)'),
        ('2 - CAGELCO(Shared)', '2 - CAGELCO(Shared)'),
        ('3 - Renewable Energy', '3 - Renewable Energy'),
        )
    
    toilet_choice = (
        ('-', '-'),
        ('1 - Open Pit', '1 - Open Pit'),
        ('2 - Water Sealed', '2 - Water Sealed'),
        ('3 - Flush', '3 - Flush'),
        )
    
    class Meta:
        model = Household
        fields = ('house_no', 'address', 'purok', 'housing_type', 'water_source', 'lighting_source', 'toilet_facility')
    
        widgets = {
            'purok': forms.Select(attrs={
            'class': 'form-select'
            }),
        }

    house_no = forms.CharField(
        label="House No.",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter House No.'})
    )
    address = forms.CharField(
        label="Street",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Street Name'})
    )
    housing_type = forms.ChoiceField(
        label="Housing Type",
        widget=forms.Select(attrs={'class': 'form-control', 'placeholder': 'Enter Housing Type'}),
        choices=housing_choice,   
    )
    water_source = forms.ChoiceField(
        label="Water Source",
        widget=forms.Select(attrs={'class': 'form-control', 'placeholder': 'Enter Water Source'}),
        choices=water_choice,   
    )
    lighting_source = forms.ChoiceField(
        label="Lighting Source",
        widget=forms.Select(attrs={'class': 'form-control', 'placeholder': 'Enter Lighting Source'}),
        choices=lighting_choice,   
    )
    toilet_facility = forms.ChoiceField(
        label="Toilet Facility Type",
        widget=forms.Select(attrs={'class': 'form-control', 'placeholder': 'Enter Toilet Facility Type'}),
        choices=toilet_choice,   
    )
    # def clean(self):
    #     cleaned_data = super().clean()
    #     house_no = cleaned_data.get('house_no')

    #     # Check for duplicate house no
    #     if Household.objects.filter(house_no=house_no).exists():
    #         raise ValidationError('House no. already exists!')

    #     return cleaned_data

class DeceasedForm(forms.ModelForm):
    class Meta:
        model = Deceased
        fields = ('resident', 'date_of_death', 'cause_of_death',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'date_of_death': forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date'
            }),
            'cause_of_death': forms.TextInput(attrs={
            'class': 'form-control'
            }),
        }

class OfwForm(forms.ModelForm):
    class Meta:
        model = Ofw
        fields = ('resident', 'passport_no', 'country',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'passport_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'country': forms.TextInput(attrs={
            'class': 'form-control'
            }),
        }

class brgyOfficialForm(forms.ModelForm):
    class Meta:
        model = Brgy_Officials
        fields = ('brgy_Captain', 'kagawad1', 'kagawad2', 'kagawad3', 'kagawad4', 'kagawad5', 'kagawad6', 'kagawad7', 'sk', 'secretary', 'treasurer')

        widgets = {
            'brgy_Captain': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad1': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad2': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad3': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad4': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad5': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad6': forms.Select(attrs={
            'class': 'form-select'
            }),
            'kagawad7': forms.Select(attrs={
            'class': 'form-select'           
            }),
            'sk': forms.Select(attrs={
            'class': 'form-select'
            }),
            'secretary': forms.Select(attrs={
            'class': 'form-select'
            }),
            'treasurer': forms.Select(attrs={
            'class': 'form-select'           
            }),
        }

    # def clean(self):
    #     cleaned_data = super().clean()
    #     complainants = self.cleaned_data.get('complainants')
    #     respondents = self.cleaned_data.get('respondents')
        
    #     if complainants == respondents:
    #         raise ValidationError("Complainant and respondent cannot be the same!")
        
    #     return cleaned_data

class BlotterForm(forms.ModelForm):
    status_choices = (
        ('-----', '-----'),
        ('Pending', 'Pending'),
        ('Solved', 'Solved'),
        )
    class Meta:
        model = Blotter
        fields = ('complainants', 'respondents', 'statement', 'case_no', 'case', 'status',)

        widgets = {
            'complainants': forms.SelectMultiple(attrs={
            'class': 'form-control select2'
            }),
            'respondents': forms.SelectMultiple(attrs={
            'class': 'form-control select2'
            }),
            'statement': forms.Textarea(attrs={
            'class': 'form-control'
            }),
            'case_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'case': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'status': forms.Select(attrs={
            'class': 'form-select'
            }),
        }
    # complainants = ModelMultipleChoiceField(
    #     queryset=Resident.objects.all(),
    #     widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
    # )

    # respondents = ModelMultipleChoiceField(
    #     queryset=Resident.objects.all()[:100],
    #     widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
    # )
    status = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=status_choices
    )
    labels = {
        'case': 'Case Description:',
    }
    def clean(self):
        cleaned_data = super().clean()
        complainants = self.cleaned_data.get('complainants')
        respondents = self.cleaned_data.get('respondents')
        
        if complainants == respondents:
            raise ValidationError("Complainant and respondent cannot be the same!")
        
        return cleaned_data

class SummonForm(forms.ModelForm):
    class Meta:
        model = Summon
        fields = ('blotter', 'summon_date',)

        widgets = {
            'blotter': forms.Select(attrs={'class': 'form-select'}),
            'summon_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class FileActionForm(forms.ModelForm):
    class Meta:
        model = FileAction
        fields = ('case_no',)

        widgets = {
            'case_no': forms.Select(attrs={'class': 'form-select'}),
        }

class BusinessForm(forms.ModelForm):
    status_choices = (
        ('-----', '-----'),
        ('ACTIVE', 'ACTIVE'),
        ('INACTIVE', 'INACTIVE'),
        )
    class Meta:
        model = Business
        fields = ('business_name', 'business_type', 'purok', 'proprietor', 'address', 'citizenship','status',)
        widgets = {
            'business_name': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'business_type': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'purok': forms.Select(attrs={
            'class': 'form-select'
            }),
            'proprietor': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'address': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'citizenship': forms.TextInput(attrs={
            'class': 'form-control'
            }),
        }
    status = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        choices=status_choices,
    )

class JobSeekersForm(forms.ModelForm):
    class Meta:
        model = JobSeekers
        fields = ('resident',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
        }
    def __init__(self, *args, **kwargs):
        super(JobSeekersForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('f_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class BrgyClearanceForm(forms.ModelForm):
    class Meta:
        model = BrgyClearance
        fields = ('resident', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control',
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
    }
    def __init__(self, *args, **kwargs):
        super(BrgyClearanceForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class BrgyCertificateForm(forms.ModelForm):
    class Meta:
        model = BrgyCertificate
        fields = ('resident', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'place_issued': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
    }
    def __init__(self, *args, **kwargs):
        super(BrgyCertificateForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class DeathClaimCertificateForm(forms.ModelForm):
    class Meta:
        model = DeathClaimCertificate
        fields = ('deceased', 'claimant', 'or_no', 'or_amount', 'or_date',)
        widgets = {
            'deceased': forms.Select(attrs={
            'class': 'form-select'
            }),
            'claimant': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(DeathClaimCertificateForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Deceased.objects.all().order_by('resident')
        
        # Update the queryset for the resident field
        self.fields['deceased'].queryset = residents_queryset

class BusinessClearanceForm(forms.ModelForm):
    type_choices = (
        ('-----', '-----'),
        ('MANAGEMENT BUSINESS', 'MANAGEMENT BUSINESS'),
        ('CORPORATE BUSINESS', 'CORPORATE BUSINESS'),
        )
    class Meta:
        model = BusinessClearance
        fields = ('business', 'clearance_type', 'effective_until', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date', 'place_issued',)
        widgets = {
            'business': forms.Select(attrs={
            'class': 'form-select'
            }),
            'effective_until': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'place_issued': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
        'place_issued': 'Place Issued:',
    }    
    clearance_type = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=type_choices,
    )

class BusinessCertificateForm(forms.ModelForm):
    class Meta:
        model = BusinessCertificate
        fields = ('business', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'business': forms.Select(attrs={
            'class': 'form-select'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
        'place_issued': 'Place Issued:',
    }    

class CertResidencyForm(forms.ModelForm):
    class Meta:
        model = CertResidency
        fields = ('resident', 'resident_since', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'resident_since': forms.TextInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
        'resident_since': 'Resident Since:',
    } 
    def __init__(self, *args, **kwargs):
        super(CertResidencyForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class CertIndigencyForm(forms.ModelForm):
    class Meta:
        model = CertIndigency
        fields = ('resident', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    def __init__(self, *args, **kwargs):
        super(CertIndigencyForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class CertSoloParentForm(forms.ModelForm):
    class Meta:
        model = CertSoloParent
        fields = ('resident', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    def __init__(self, *args, **kwargs):
        super(CertSoloParentForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset

class CertGoodMoralForm(forms.ModelForm):
    class Meta:
        model = CertGoodMoral
        fields = ('resident', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date', 'place_issued',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'place_issued': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    labels = {
        'ctc': 'Community Tax No.:',
    } 
    def __init__(self, *args, **kwargs):
        super(CertGoodMoralForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset
    def clean(self):
        cleaned_data = super().clean()
        respondent = cleaned_data.get('resident')

        # Check for respondent
        if Blotter.objects.filter(respondents=respondent).exists():
            #raise ValidationError('This person has a pending blotter report!')
            self.add_error('resident', 'This person has a pending blotter report!')
        return cleaned_data

class CertTribalForm(forms.ModelForm):
    class Meta:
        model = CertTribal
        fields = ('resident', 'mother', 'tribe', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'resident': forms.Select(attrs={
            'class': 'form-select'
            }),
            'mother': forms.Select(attrs={
            'class': 'form-select'
            }),
            'tribe': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    def __init__(self, *args, **kwargs):
        super(CertTribalForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset
    def clean(self):
        cleaned_data = super().clean()
        resident = self.cleaned_data.get('resident')
        mother = self.cleaned_data.get('mother')
        
        if resident == mother:
            raise ValidationError("Resident and Mother cannot be the same!")
        
        return cleaned_data

class CertNonOperationForm(forms.ModelForm):
    class Meta:
        model = CertNonOperation
        fields = ('business', 'ceased_date', 'purpose', 'or_no', 'or_amount', 'or_date', 'ctc', 'ctc_amount', 'ctc_date',)
        widgets = {
            'business': forms.Select(attrs={
            'class': 'form-select'
            }),
            'ceased_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'purpose': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_no': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'or_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'or_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
            'ctc': forms.TextInput(attrs={
            'class': 'form-control'
            }),
            'ctc_amount': forms.NumberInput(attrs={
            'class': 'form-control'
            }),
            'ctc_date': forms.DateInput(attrs={
            'class': 'form-control', 'type': 'date',
            }),
        }
    def __init__(self, *args, **kwargs):
        super(CertNonOperationForm, self).__init__(*args, **kwargs)
        
        # Sort the residents by some criteria, for example, by name
        residents_queryset = Resident.objects.all().order_by('l_name')
        
        # Update the queryset for the resident field
        self.fields['resident'].queryset = residents_queryset