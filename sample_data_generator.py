# sample_data_generator.py
import random
from datetime import datetime, timedelta
from django.utils import timezone
from faker import Faker
from BrgyApp.models import Brgy, Purok, Household, Resident

fake = Faker('en_PH')  # Using Philippines locale

def generate_sample_data():
    # Get existing Brgy
    try:
        brgy = Brgy.objects.first()  # Get the first brgy in the database
        if not brgy:
            raise Exception("No existing Brgy found in the database")
    except Exception as e:
        print(f"Error: {e}")
        return

    # Create 10 Puroks
    puroks = []
    for i in range(1, 11):
        purok = Purok.objects.create(
            brgy=brgy,
            purok_name=f"Purok {i}"
        )
        puroks.append(purok)
        print(f"Created Purok {i}")

    # Housing types, water sources, lighting sources, and toilet facilities
    housing_types = ['Concrete', 'Semi-concrete', 'Light Materials', 'Mixed Materials']
    water_sources = ['Water District', 'Deep Well', 'Spring', 'Communal Faucet']
    lighting_sources = ['Electric', 'Solar', 'Generator', 'Kerosene']
    toilet_facilities = ['Water-sealed', 'Antipolo', 'Communal', 'None']

    # Create 30 Households
    households = []
    for i in range(1, 31):
        household = Household.objects.create(
            house_no=f"{random.randint(1, 999):03d}",
            address=fake.street_address(),
            purok=random.choice(puroks),
            housing_type=random.choice(housing_types),
            water_source=random.choice(water_sources),
            lighting_source=random.choice(lighting_sources),
            toilet_facility=random.choice(toilet_facilities)
        )
        households.append(household)
        print(f"Created Household {i}")

    # Education levels and professions
    education_levels = ['Elementary', 'High School', 'College', 'Vocational', 'Post Graduate']
    professions = ['Teacher', 'Farmer', 'Fisher', 'Driver', 'Vendor', 'Office Worker', 'Business Owner', 'Student', 'Retired', 'Unemployed']
    resident_types = ['Permanent', 'Temporary', 'Transient']

    # Create 100 Residents
    for i in range(100):
        birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)
        
        Resident.objects.create(
            f_name=fake.first_name(),
            l_name=fake.last_name(),
            m_name=fake.last_name(),
            gender=random.choice(['Male', 'Female']),
            house_no=random.choice(households),
            head=random.choice([True, False]),
            phone_number=fake.phone_number(),
            birth_date=birth_date,
            birth_place=fake.city(),
            civil_status=random.choice(['Single', 'Married', 'Widowed', 'Separated']),
            religion=random.choice(['Roman Catholic', 'Islam', 'Protestant', 'INC', 'Others']),
            citizenship='Filipino',
            profession=random.choice(professions),
            education=random.choice(education_levels),
            voter=random.choice([True, False]),
            precint_no=f"{random.randint(1, 999):03d}A",
            solo_parent=random.choice([True, False]),
            pwd=random.choice([True, False]),
            indigent=random.choice([True, False]),
            fourps=random.choice([True, False]),
            resident_type=random.choice(resident_types),
            osy=random.choice([True, False]),
            isy=random.choice([True, False])
        )
        print(f"Created Resident {i+1}")

    print("Sample data generation completed!")