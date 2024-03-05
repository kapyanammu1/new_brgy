import pandas as pd
from django.db import transaction
from .models import Resident, Household, Purok, Brgy
from datetime import datetime

def import_residents_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)  # Read Excel file using pandas
        households = []
        residents = []
        with transaction.atomic():
            for index, row in df.iterrows():
                # household = row['house_no']
                # brgy_instance = Brgy.objects.get(brgy_name='Ugac Sur')
                # purok_instance, created = Purok.objects.get_or_create(brgy=brgy_instance, purok_name=row['purok'])
                # household_instance, created = Household.objects.get_or_create(
                #     house_no=household, 
                #     address=row['address'] + ' St.',
                #     purok=purok_instance,
                #     housing_type=row['housing_type'],
                #     water_source=row['water_source'],
                #     lighting_source=row['lighting_source'],
                #     toilet_facility=row['toilet_facility'],
                #     )
                brgy_instance = Brgy.objects.get(brgy_name='Ugac Sur')
                purok_instance, created = Purok.objects.get_or_create(brgy=brgy_instance, purok_name=row['purok'])

                # Check if the Household with the same house_no, address, and purok already exists
                household_instance = Household.objects.filter(
                    house_no=row['house_no'],
                    address=row['address'] + ' St.',
                    purok=purok_instance
                ).first()

                if household_instance is None:
                    household_instance, created = Household.objects.get_or_create(
                        house_no=row['house_no'],
                        address=row['address'] + ' St.',
                        purok=purok_instance,
                        housing_type=row['housing_type'],
                        water_source=row['water_source'],
                        lighting_source=row['lighting_source'],
                        toilet_facility=row['toilet_facility'],
                    )

                Resident.objects.create(
                    f_name=row['f_name'],
                    l_name=row['l_name'],
                    m_name=row['m_name'],
                    gender=row['gender'],
                    house_no =household_instance,
                    # address =row['address'],
                    # purok=purok_instance,
                    phone_number = row['phone_number'],
                    birth_date = row['birth_date'],
                    birth_place = row['birth_place'],
                    civil_status = row['civil_status'],
                    religion = row['religion'],
                    citizenship = row['citizenship'],
                    profession = row['profession'],   
                    education = row['education'],
                    voter = row['voter'],
                    precint_no = row['precint_no'],
                    solo_parent = row['solo_parent'],
                    pwd = row['pwd'],
                    indigent = row['indigent'],
                    fourps = row['fourps'],
                    resident_type = row['resident_type'],
                    osy = row['osy'],
                    isy = row['isy'],
                    head = row['head'],
                    # family_income = row['family_income'],
                    image = row['image'],
                )
            
            return True  # Import successful
    except Exception as e:
        return str(e)  # Return error message

# def import_household_from_excel(file_path):
#     try:
#         df = pd.read_excel(file_path)  # Read Excel file using pandas

#         for index, row in df.iterrows():
            
#             Resident.objects.create(
#                 house_no=row['house_no'],
#                 address=row['address'],
#                 purok=row['purok'],
#                 housing_type=row['housing_type'],
#                 water_source=row['water_source'],
#                 lighting_source=row['lighting_source'],
#                 toilet_facility=row['toilet_facility'],
#             )
        
#         return True  # Import successful
#     except Exception as e:
#         return str(e)  # Return error message