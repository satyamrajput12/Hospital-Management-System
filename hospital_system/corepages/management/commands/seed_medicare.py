import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from departments.models import Department, LabTest
from doctors.models import Doctor, DoctorAvailability
from corepages.models import ProductCategory, Product


class Command(BaseCommand):
    help = "Seeds initial lab tests, pharmacy categories, products, and doctor availabilities."

    def handle(self, *args, **options):
        self.stdout.write("Seeding Medicare Hospital database...")

        # 1. Ensure Departments exist
        depts_data = [
            ("Cardiology", "Heart and cardiovascular care with modern diagnostic labs", "heart"),
            ("Neurology", "Comprehensive brain, spine, and neurological disorders treatment", "activity"),
            ("Orthopedics", "Bone, joint, spine surgery and physiotherapy rehabilitation", "user-check"),
            ("Dermatology", "Clinical dermatology, skin disorders, and therapeutic care", "shield"),
            ("Pediatrics", "Infant, child, and adolescent healthcare and vaccination", "smile"),
            ("General Medicine", "Primary healthcare, preventive medicine, and routine wellness", "plus-circle"),
        ]
        dept_objs = {}
        for name, desc, icon in depts_data:
            dept, _ = Department.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'icon': icon, 'is_active': True}
            )
            dept_objs[name] = dept

        # 2. Seed Lab Tests
        lab_tests_data = [
            {
                'name': 'Imaging Tests Package (X-Ray & Ultrasound)',
                'department': dept_objs.get('Cardiology'),
                'description': 'Comprehensive imaging tests, high-definition X-rays, and abdominal ultrasound diagnostics.',
                'price': Decimal('140.00'),
                'discount_price': Decimal('120.00'),
                'preparation_instructions': 'No special diet required; loose clothing recommended.',
                'duration': 'Same day (4 hours)',
                'sample_type': 'Radiological Imaging',
                'image_fallback': '/static/images/lab_1.jpg',
            },
            {
                'name': 'MRI & High-Resolution CT Scan',
                'department': dept_objs.get('Neurology'),
                'description': 'Advanced high-resolution multi-slice CT diagnostics and 3T MRI neuro imaging.',
                'price': Decimal('140.00'),
                'discount_price': Decimal('120.00'),
                'preparation_instructions': 'Remove metal jewelry; 4 hours fasting before contrast scans.',
                'duration': '24-48 hours',
                'sample_type': 'Magnetic Resonance & CT',
                'image_fallback': '/static/images/lab_2.jpg',
            },
            {
                'name': 'Orthopedists Bone & Joint Health Check',
                'department': dept_objs.get('Orthopedics'),
                'description': 'Bone density DEXA scan, calcium serum, uric acid, and spinal alignment screening.',
                'price': Decimal('140.00'),
                'discount_price': Decimal('120.00'),
                'preparation_instructions': 'Fasting overnight (8-10 hours) for accurate calcium/mineral profile.',
                'duration': '12-24 hours',
                'sample_type': 'Blood & DEXA Imaging',
                'image_fallback': '/static/images/lab_3.jpg',
            },
            {
                'name': 'Complete Blood Count (CBC) & HbA1c',
                'department': dept_objs.get('General Medicine'),
                'description': 'Vital hemoglobin, white blood cells, platelets, and 3-month glycemic HbA1c control profile.',
                'price': Decimal('75.00'),
                'discount_price': Decimal('55.00'),
                'preparation_instructions': '8-10 hours overnight fasting required.',
                'duration': 'Same day (6 hours)',
                'sample_type': 'Venous Blood Sample',
                'image_fallback': '/static/images/lab_1.jpg',
            },
        ]
        for td in lab_tests_data:
            img_fb = td.pop('image_fallback', '')
            test, created = LabTest.objects.get_or_create(name=td['name'], defaults=td)
            if created:
                self.stdout.write(f"  + Created Lab Test: {test.name}")

        # 3. Seed Pharmacy Categories and Products
        cat_nutrition, _ = ProductCategory.objects.get_or_create(name='Nutrition & Supplements', defaults={'description': 'Daily wellness and dietary balance'})
        cat_equipment, _ = ProductCategory.objects.get_or_create(name='Healthcare Equipment', defaults={'description': 'Clinical safety and diagnostics'})
        cat_vitamins, _ = ProductCategory.objects.get_or_create(name='Vitamins & Immunity', defaults={'description': 'Essential vitamins and minerals'})
        cat_hygiene, _ = ProductCategory.objects.get_or_create(name='Hygiene & Wellness', defaults={'description': 'Antiseptic and daily personal care'})
        cat_fever, _ = ProductCategory.objects.get_or_create(name='Fever & Pain Relief', defaults={'description': 'Clinically approved antipyretics and analgesics for fever and pain'})
        cat_calcium, _ = ProductCategory.objects.get_or_create(name='Calcium & Bone Health', defaults={'description': 'Elemental calcium, Vitamin D3, and joint support supplements'})
        cat_cough, _ = ProductCategory.objects.get_or_create(name='Cough & Cold Care', defaults={'description': 'Decongestants, antihistamines, and soothing throat relief'})
        cat_digestive, _ = ProductCategory.objects.get_or_create(name='Digestive & Gastric Care', defaults={'description': 'Antacids, proton-pump inhibitors, and digestive health'})

        products_data = [
            {
                'name': 'Dietary Supplement Health Products',
                'category': cat_nutrition,
                'description': 'Balanced clinical dietary formula supporting vitality, gut microbiome, and cell health.',
                'price': Decimal('80.00'),
                'discount_percent': 20,
                'stock': 85,
                'rating': Decimal('4.5'),
                'image_url_fallback': '/static/images/prod_1.jpg',
            },
            {
                'name': 'Nitrile Disposable Gloves (Box of 100)',
                'category': cat_equipment,
                'description': 'Medical-grade powder-free nitrile examination gloves with high tensile strength.',
                'price': Decimal('140.00'),
                'discount_percent': 0,
                'stock': 120,
                'rating': Decimal('4.8'),
                'image_url_fallback': '/static/images/prod_2.jpg',
            },
            {
                'name': 'Womens Multi Vitamins A & Biotin Cranberry',
                'category': cat_vitamins,
                'description': 'Daily female multivitamins packed with Vitamin A, Biotin, Cranberry extract, and Zinc.',
                'price': Decimal('160.00'),
                'discount_percent': 50,
                'stock': 60,
                'rating': Decimal('4.7'),
                'image_url_fallback': '/static/images/prod_3.jpg',
            },
            {
                'name': 'Antibacterial Liquid Hand Soap (500ml)',
                'category': cat_hygiene,
                'description': 'Hospital-grade antiseptic wash that eliminates 99.9% of bacteria while moisturizing skin.',
                'price': Decimal('80.00'),
                'discount_percent': 0,
                'stock': 150,
                'rating': Decimal('4.6'),
                'image_url_fallback': '/static/images/prod_4.jpg',
            },
            {
                'name': 'Digital Infrared Forehead Thermometer',
                'category': cat_equipment,
                'description': 'Non-contact instant medical reading with color-coded fever warning screen.',
                'price': Decimal('120.00'),
                'discount_percent': 15,
                'stock': 40,
                'rating': Decimal('4.9'),
                'image_url_fallback': '/static/images/prod_2.jpg',
            },
            # 10 Added Fever, Calcium & Essential Medicines
            {
                'name': 'Paracetamol 650mg Fast-Action Tablets (Strip of 15)',
                'category': cat_fever,
                'description': 'Fast-acting antipyretic & analgesic for effective high fever reduction, mild-to-moderate headache, and muscular body ache relief.',
                'price': Decimal('45.00'),
                'discount_percent': 15,
                'stock': 250,
                'rating': Decimal('4.8'),
                'image_url_fallback': '/static/images/prod_1.jpg',
            },
            {
                'name': 'Dolo 650 Fever & Headache Relief (Strip of 15)',
                'category': cat_fever,
                'description': 'Doctor-recommended paracetamol formulation for viral fever, chills, body ache, and seasonal flu temperature management.',
                'price': Decimal('35.00'),
                'discount_percent': 10,
                'stock': 300,
                'rating': Decimal('4.9'),
                'image_url_fallback': '/static/images/prod_3.jpg',
            },
            {
                'name': 'Calcium 500mg + Vitamin D3 Tablets (Bottle of 60)',
                'category': cat_calcium,
                'description': 'High-potency elemental calcium with Vitamin D3 (Cholecalciferol) to support bone mineral density, joint strength, and prevent osteoporosis.',
                'price': Decimal('180.00'),
                'discount_percent': 25,
                'stock': 140,
                'rating': Decimal('4.8'),
                'image_url_fallback': '/static/images/prod_1.jpg',
            },
            {
                'name': 'Shelcal-HD Calcium & Mineral Syrup (200ml)',
                'category': cat_calcium,
                'description': 'Pediatric & adult liquid calcium supplement fortified with Magnesium, Zinc, and Vitamin D3 for optimal skeletal absorption.',
                'price': Decimal('165.00'),
                'discount_percent': 20,
                'stock': 95,
                'rating': Decimal('4.7'),
                'image_url_fallback': '/static/images/prod_4.jpg',
            },
            {
                'name': 'Ibuprofen 400mg Anti-Inflammatory Tablets (Strip of 10)',
                'category': cat_fever,
                'description': 'Fast anti-inflammatory and pain reducer for acute fever, migraine, toothache, muscle sprains, and joint discomfort.',
                'price': Decimal('55.00'),
                'discount_percent': 15,
                'stock': 180,
                'rating': Decimal('4.6'),
                'image_url_fallback': '/static/images/prod_3.jpg',
            },
            {
                'name': 'Cetirizine 10mg Allergy & Cold Relief (Strip of 10)',
                'category': cat_cough,
                'description': 'Rapid 24-hour relief from runny nose, sneezing, pollen allergy, watery eyes, and allergic skin hives.',
                'price': Decimal('40.00'),
                'discount_percent': 20,
                'stock': 210,
                'rating': Decimal('4.7'),
                'image_url_fallback': '/static/images/prod_2.jpg',
            },
            {
                'name': 'Vitamin C 1000mg + Zinc Effervescent Tablets (Tube of 20)',
                'category': cat_vitamins,
                'description': 'Delicious orange effervescent antioxidant drink providing daily immune protection, energy, and viral defense.',
                'price': Decimal('290.00'),
                'discount_percent': 30,
                'stock': 160,
                'rating': Decimal('4.9'),
                'image_url_fallback': '/static/images/prod_1.jpg',
            },
            {
                'name': 'Pantoprazole DSR Gastro-Resistant Capsules (Strip of 10)',
                'category': cat_digestive,
                'description': 'Relieves hyperacidity, acid reflux, heartburn, GERD, nausea, and morning sickness with enteric-coated pellets.',
                'price': Decimal('145.00'),
                'discount_percent': 20,
                'stock': 150,
                'rating': Decimal('4.8'),
                'image_url_fallback': '/static/images/prod_3.jpg',
            },
            {
                'name': 'Oral Rehydration Salts (ORS) Probiotic Sachet (Pack of 5)',
                'category': cat_hygiene,
                'description': 'WHO-standard electrolyte formula with active probiotics to restore fluid balance during high fever, dehydration, and vomiting.',
                'price': Decimal('65.00'),
                'discount_percent': 15,
                'stock': 320,
                'rating': Decimal('4.9'),
                'image_url_fallback': '/static/images/prod_2.jpg',
            },
            {
                'name': 'Herbal Cough & Sore Throat Lozenges (Honey Ginger, Pack of 24)',
                'category': cat_cough,
                'description': 'Soothing Ayurvedic herbal lozenges enriched with Tulsi, Ginger, Honey, and Mulethi to calm throat scratchiness and persistent dry cough.',
                'price': Decimal('50.00'),
                'discount_percent': 10,
                'stock': 220,
                'rating': Decimal('4.8'),
                'image_url_fallback': '/static/images/prod_4.jpg',
            },
        ]
        for pd in products_data:
            prod, created = Product.objects.get_or_create(name=pd['name'], defaults=pd)
            if created:
                self.stdout.write(f"  + Created Product: {prod.name}")

        # 4. Ensure Doctor Availability slots exist for doctors
        doctors = Doctor.objects.all()
        for doc in doctors:
            if not doc.availabilities.exists():
                DoctorAvailability.objects.create(
                    doctor=doc,
                    day_of_week='MON',
                    start_time=datetime.time(9, 0),
                    end_time=datetime.time(13, 0),
                    slot_duration_minutes=30
                )
                DoctorAvailability.objects.create(
                    doctor=doc,
                    day_of_week='WED',
                    start_time=datetime.time(14, 0),
                    end_time=datetime.time(18, 0),
                    slot_duration_minutes=30
                )
                DoctorAvailability.objects.create(
                    doctor=doc,
                    day_of_week='FRI',
                    start_time=datetime.time(9, 0),
                    end_time=datetime.time(13, 0),
                    slot_duration_minutes=30
                )
                self.stdout.write(f"  + Created standard availability schedule for {doc}")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
