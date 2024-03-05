from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.db.models import Q

class CustomUser(AbstractUser):
    # Add your existing fields here

    class Meta:
        permissions = [
            ("can_access_admin_features", "Can access admin features"),
        ]

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_groups',  # Change related_name for groups
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # Change related_name for user_permissions
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
        related_query_name='user',
    )

class Brgy(models.Model):
    brgy_name = models.CharField(max_length=150)
    municipality = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='item_images', blank=True, null=True)
    # image1 = models.ImageField(upload_to='item_images', blank=True, null=True)
    
    def __str__(self):
        return self.brgy_name

class Purok(models.Model):
    brgy = models.ForeignKey(Brgy, on_delete=models.CASCADE)
    purok_name = models.CharField(max_length=150)
    
    def __str__(self):
        return self.purok_name

class Household(models.Model):
    house_no = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    purok = models.ForeignKey(Purok, on_delete=models.CASCADE)
    housing_type = models.CharField(max_length=100)
    water_source = models.CharField(max_length=50)
    lighting_source = models.CharField(max_length=50)
    toilet_facility = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.house_no} {self.address}"

class ResidentManager(models.Manager):
    def search(self, query):
        qs = self.get_queryset()
        if query:
            words = query.split()
            for word in words:
                qs = qs.filter(
                    models.Q(f_name__icontains=word) |
                    models.Q(l_name__icontains=word) |
                    models.Q(m_name__icontains=word)
                )
        return qs

class Resident(models.Model):  
    f_name = models.CharField(max_length=100)
    l_name = models.CharField(max_length=100)
    m_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=15)
    house_no = models.ForeignKey(Household, on_delete=models.CASCADE)
    head = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20)
    birth_date = models.DateField()
    birth_place = models.CharField(max_length=100)
    civil_status = models.CharField(max_length=50)
    religion = models.CharField(max_length=50)
    citizenship = models.CharField(max_length=50)
    profession = models.CharField(max_length=100)
    education = models.CharField(max_length=100)
    voter = models.BooleanField(default=False)
    precint_no = models.CharField(max_length=20)
    solo_parent = models.BooleanField(default=False)
    pwd = models.BooleanField(default=False)
    indigent = models.BooleanField(default=False)
    fourps = models.BooleanField(default=False)
    resident_type = models.CharField(max_length=20)
    osy = models.BooleanField(default=False)
    isy = models.BooleanField(default=False)
    # family_income = models.CharField(max_length=50)
    image = models.ImageField(upload_to='item_images', blank=True, null=True)

    objects = ResidentManager()

    def __str__(self):
        full_name = f"{self.l_name}, {self.f_name} {self.m_name[0]}."
        return full_name

    @property
    def is_respondent(self):
        return self.responses.filter(status='Pending').exists()

class JobSeekers(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.resident

class Brgy_Officials(models.Model):
    brgy_Captain = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='brgy_Captain')
    kagawad1 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad1')
    kagawad2 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad2')
    kagawad3 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad3')
    kagawad4 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad4')
    kagawad5 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad5')
    kagawad6 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad6')
    kagawad7 = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='kagawad7')
    sk = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='sk')
    secretary = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='secretary')
    treasurer = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='treasurer')
    def __str__(self):
        return self.purok_name

class Business(models.Model):
    business_name = models.CharField(max_length=100)
    business_type = models.CharField(max_length=100)
    purok = models.ForeignKey(Purok, on_delete=models.CASCADE)
    proprietor = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    citizenship = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.business_name

class BrgyClearance(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class BrgyCertificate(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    place_issued = models.CharField(max_length=100)
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertResidency(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    resident_since = models.DateField()
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertIndigency(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertSoloParent(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertGoodMoral(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    place_issued = models.CharField(max_length=100)
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertTribal(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='resident')
    mother = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='mother')
    tribe = models.CharField(max_length=100)
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class CertNonOperation(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    ceased_date = models.DateField()
    purpose = models.CharField(max_length=100)
    clearance_type = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.purpose

class BusinessClearance(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    clearance_type = models.CharField(max_length=100)
    effective_until = models.DateField()
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    place_issued = models.CharField(max_length=100)
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.business

class BusinessCertificate(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    purpose = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    ctc = models.CharField(max_length=50)
    ctc_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    ctc_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.business

class Deceased(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    date_of_death = models.DateField()
    cause_of_death = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.resident.l_name}, {self.resident.f_name} {self.resident.m_name}"

class DeathClaimCertificate(models.Model):
    deceased = models.ForeignKey(Deceased, on_delete=models.CASCADE)
    claimant = models.CharField(max_length=100)
    or_no = models.CharField(max_length=50)
    or_amount = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    or_date = models.DateField()
    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.deceased.resident.l_name}, {self.deceased.resident.f_name} {self.deceased.resident.m_name}"

class Ofw(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    passport_no = models.CharField(max_length=100)
    country = models.CharField(max_length=50)
    
    def __str__(self):
        return self.passport_no

class Blotter(models.Model):
    complainants = models.ManyToManyField(Resident, related_name='complaints')
    respondents = models.ManyToManyField(Resident, related_name='responses')
    statement = models.TextField()
    case_no = models.CharField(max_length=100, unique=True)
    case = models.CharField(max_length=100)
    date_created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.case_no}"
    
class Summon(models.Model):
    blotter = models.ForeignKey(Blotter, on_delete=models.CASCADE)
    summon_date = models.DateTimeField()
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return self.blotter.case_no

class FileAction(models.Model):
    case_no = models.ForeignKey(Summon, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return self.case_no



