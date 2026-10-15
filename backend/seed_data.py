"""RE:VIVE - expanded demo seed: 5 admins, 5 hospitals, 5 doctors, 5 patients, 5 guardians."""
import asyncio
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

from app.database import connect_db, close_db, get_db
from app.auth.service import hash_password

NOW = datetime.now(timezone.utc)
USER_PASSWORD = hash_password("Test@123")
ADMIN_PASSWORD = hash_password("admin123")

# Deterministic IDs. Keep the first IDs compatible with the original seed.
ADMIN_IDS = [ObjectId(f"fff00000000000000000000{i}") for i in range(1, 6)]
HOSPITAL_IDS = [ObjectId(f"aaa00000000000000000000{i}") for i in range(1, 6)]
HOSP_ADMIN_IDS = [ObjectId(f"bbb00000000000000000000{i}") for i in range(1, 6)]
DOCTOR_IDS = [ObjectId(f"ccc00000000000000000000{i}") for i in range(1, 6)]
PATIENT_IDS = [ObjectId(f"ddd00000000000000000000{i}") for i in range(1, 6)]
GUARDIAN_IDS = [ObjectId(f"eee00000000000000000000{i}") for i in range(1, 6)]

ADMIN_EMAILS = ["admin@revive.com", "admin2@revive.com", "admin3@revive.com", "admin4@revive.com", "admin5@revive.com"]
ADMIN_NAMES = ["RE:VIVE Super Admin", "Aarav Mehta", "Ishita Roy", "Rohan Das", "Neha Kapoor"]

HOSPITALS = [
    ("City Recovery Hospital", "42 Wellness Ave, Recovery City, RC 10001", "+1-555-100-2000", "info@cityrecovery.org"),
    ("Hope Wellness Hospital", "18 Hope Street, Recovery City, RC 10002", "+1-555-100-3000", "info@hopewellness.org"),
    ("Sunrise Rehabilitation Center", "7 Sunrise Road, Recovery City, RC 10003", "+1-555-100-4000", "info@sunriserehab.org"),
    ("Harmony Care Hospital", "91 Harmony Blvd, Recovery City, RC 10004", "+1-555-100-5000", "info@harmonycare.org"),
    ("New Horizons Recovery Hospital", "25 Horizon Drive, Recovery City, RC 10005", "+1-555-100-6000", "info@newhorizons.org"),
]

HOSP_ADMIN_DATA = [
    ("hospital@test.com", "Dr. Sarah Mitchell", "+1-555-100-0001"),
    ("hospital2@test.com", "Dr. Michael Brown", "+1-555-100-0002"),
    ("hospital3@test.com", "Dr. Priya Nair", "+1-555-100-0003"),
    ("hospital4@test.com", "Dr. Daniel Kim", "+1-555-100-0004"),
    ("hospital5@test.com", "Dr. Sofia Rodriguez", "+1-555-100-0005"),
]

DOCTORS = [
    ("doctor1@test.com", "Dr. James Carter", "+1-555-200-0001"),
    ("doctor2@test.com", "Dr. Emily Nguyen", "+1-555-200-0002"),
    ("doctor3@test.com", "Dr. Arjun Mehta", "+1-555-200-0003"),
    ("doctor4@test.com", "Dr. Olivia Wilson", "+1-555-200-0004"),
    ("doctor5@test.com", "Dr. Daniel Anderson", "+1-555-200-0005"),
]

PATIENTS = [
    ("patient1@test.com", "Alex Johnson", "+1-555-300-0001", "Alcohol Use Disorder — moderate", "12-Step + CBT"),
    ("patient2@test.com", "Maria Santos", "+1-555-300-0002", "Opioid Use Disorder", "MAT + Individual Counselling"),
    ("patient3@test.com", "Ryan Cooper", "+1-555-300-0003", "Cannabis Dependence + Insomnia", "Motivational Interviewing + Sleep Hygiene"),
    ("patient4@test.com", "Jordan Lee", "+1-555-300-0004", "Alcohol Use Disorder — mild", "CBT + Group Therapy"),
    ("patient5@test.com", "Aisha Patel", "+1-555-300-0005", "Stimulant Use Disorder", "CBT + Relapse Prevention"),
]

GUARDIANS = [
    ("guardian1@test.com", "Linda Johnson", "+1-555-400-0001"),
    ("guardian2@test.com", "Carlos Santos", "+1-555-400-0002"),
    ("guardian3@test.com", "Rachel Cooper", "+1-555-400-0003"),
    ("guardian4@test.com", "Anita Lee", "+1-555-400-0004"),
    ("guardian5@test.com", "Vikram Patel", "+1-555-400-0005"),
]

# 0 = strong, 1 = steady, 2 = moderate, 3 = fragile, 4 = high concern.
RISK_PROFILES = [0, 1, 4, 0, 2]


def days_ago(n: int) -> datetime:
    return NOW - timedelta(days=n)


def oid_range(ids):
    return {"$in": ids}


async def seed_admins(db):
    users = []
    for i, (uid, email, name) in enumerate(zip(ADMIN_IDS, ADMIN_EMAILS, ADMIN_NAMES)):
        users.append({
            "_id": uid, "email": email, "password_hash": ADMIN_PASSWORD,
            "role": "admin", "full_name": name,
            "phone": f"+1-555-900-000{i+1}", "is_active": True,
            "hospital_id": None, "assigned_patients": [], "linked_patient_id": None,
            "created_at": days_ago(120 - i * 5), "updated_at": NOW,
        })
    # Remove both deterministic IDs and any older demo admin records with the same emails.
    await db.users.delete_many({"$or": [
        {"_id": oid_range(ADMIN_IDS)},
        {"email": {"$in": ADMIN_EMAILS}},
    ]})
    await db.users.insert_many(users)
    print("  ✓ 5 platform admins created")


async def seed_hospitals_and_users(db):
    hospital_docs = []
    for i, (name, address, phone, email) in enumerate(HOSPITALS):
        hospital_docs.append({
            "_id": HOSPITAL_IDS[i], "name": name, "address": address,
            "phone": phone, "email": email, "is_active": True,
            "admin_user_id": HOSP_ADMIN_IDS[i],
            "created_at": days_ago(100 - i * 10), "updated_at": NOW,
        })
    await db.hospitals.delete_many({"_id": oid_range(HOSPITAL_IDS)})
    await db.hospitals.insert_many(hospital_docs)

    users = []
    for i in range(5):
        email, name, phone = HOSP_ADMIN_DATA[i]
        users.append({
            "_id": HOSP_ADMIN_IDS[i], "email": email, "password_hash": USER_PASSWORD,
            "role": "hospital", "full_name": name, "phone": phone, "is_active": True,
            "hospital_id": HOSPITAL_IDS[i], "assigned_patients": [], "linked_patient_id": None,
            "created_at": days_ago(100 - i * 10), "updated_at": NOW,
        })

    for i in range(5):
        email, name, phone = DOCTORS[i]
        users.append({
            "_id": DOCTOR_IDS[i], "email": email, "password_hash": USER_PASSWORD,
            "role": "doctor", "full_name": name, "phone": phone, "is_active": True,
            "hospital_id": HOSPITAL_IDS[i], "assigned_patients": [PATIENT_IDS[i]],
            "linked_patient_id": None, "created_at": days_ago(90 - i * 10), "updated_at": NOW,
        })

    for i in range(5):
        email, name, phone, condition, program = PATIENTS[i]
        users.append({
            "_id": PATIENT_IDS[i], "email": email, "password_hash": USER_PASSWORD,
            "role": "patient", "full_name": name, "phone": phone, "is_active": True,
            "hospital_id": HOSPITAL_IDS[i], "assigned_patients": [], "linked_patient_id": None,
            "created_at": days_ago(60 - i * 5), "updated_at": NOW,
        })

    for i in range(5):
        email, name, phone = GUARDIANS[i]
        users.append({
            "_id": GUARDIAN_IDS[i], "email": email, "password_hash": USER_PASSWORD,
            "role": "guardian", "full_name": name, "phone": phone, "is_active": True,
            "hospital_id": HOSPITAL_IDS[i], "assigned_patients": [],
            "linked_patient_id": PATIENT_IDS[i], "created_at": days_ago(55 - i * 5), "updated_at": NOW,
        })

    all_ids = HOSP_ADMIN_IDS + DOCTOR_IDS + PATIENT_IDS + GUARDIAN_IDS
    all_emails = [row[0] for row in HOSP_ADMIN_DATA] + [row[0] for row in DOCTORS] + [row[0] for row in PATIENTS] + [row[0] for row in GUARDIANS]
    # Remove both deterministic IDs and older demo records with the same emails.
    await db.users.delete_many({"$or": [
        {"_id": oid_range(all_ids)},
        {"email": {"$in": all_emails}},
    ]})
    await db.users.insert_many(users)
    print("  ✓ 5 hospital admins + 5 doctors + 5 patients + 5 guardians created")


async def seed_patient_profiles(db):
    profiles = []
    emergency = ["Linda Johnson", "Carlos Santos", "Rachel Cooper", "Anita Lee", "Vikram Patel"]
    notes = [
        "Improving engagement; continue monitoring cravings and sleep.",
        "Stable on current MAT plan; reinforce medication adherence.",
        "Recent insomnia and high cravings require close follow-up.",
        "Good engagement with CBT and group sessions.",
        "Moderate relapse risk; focus on trigger identification and coping skills.",
    ]
    for i, (_, _, _, condition, program) in enumerate(PATIENTS):
        start = 60 - i * 5
        profiles.append({
            "user_id": PATIENT_IDS[i], "primary_condition": condition,
            "program_start_date": days_ago(start).strftime("%Y-%m-%d"),
            "sobriety_date": days_ago(max(1, start - 2)).strftime("%Y-%m-%d"),
            "therapy_program": program,
            "emergency_contact": f"{emergency[i]} — {GUARDIANS[i][2]}",
            "medical_notes": notes[i], "created_at": days_ago(start),
            "updated_at": NOW, "updated_by": "hospital_seed",
        })
    await db.patient_profiles.delete_many({"user_id": oid_range(PATIENT_IDS)})
    await db.patient_profiles.insert_many(profiles)
    print("  ✓ 5 patient profiles created")


async def seed_checkins(db):
    checkins = []
    for i, patient_id in enumerate(PATIENT_IDS):
        level = RISK_PROFILES[i]
        total_days = 10 if level >= 3 else 14
        for day in range(total_days):
            d = days_ago(total_days - 1 - day)
            if level == 0:
                mood = "good" if day >= 5 else "neutral"
                stress = max(1, 4 - day // 5)
                sleep = round(7.0 + (day % 3) * 0.3, 1)
                craving = max(1, 3 - day // 6)
                meds = True
                activity = 30 + (day % 4) * 5
            elif level == 1:
                mood = ["neutral", "good", "neutral"][day % 3]
                stress = 4 + day % 3
                sleep = round(6.2 + (day % 4) * 0.3, 1)
                craving = 3 + day % 3
                meds = day != 5
                activity = 20 + (day % 5) * 5
            elif level == 2:
                mood = ["neutral", "poor", "good"][day % 3]
                stress = 5 + day % 3
                sleep = round(5.5 + (day % 3) * 0.3, 1)
                craving = 5 + day % 3
                meds = day % 4 != 0
                activity = 10 + (day % 4) * 5
            elif level == 3:
                mood = "poor" if day < 6 else "neutral"
                stress = min(10, 7 + day % 3)
                sleep = round(4.0 + (day % 3) * 0.4, 1)
                craving = min(10, 7 + day % 4)
                meds = day % 2 == 0
                activity = 5 + (day % 3) * 3
            else:
                mood = "poor" if day < 7 else "neutral"
                stress = min(10, 8 + day % 2)
                sleep = round(3.5 + (day % 3) * 0.3, 1)
                craving = min(10, 8 + day % 3)
                meds = day % 3 == 0
                activity = day % 3 * 3
            checkins.append({
                "patient_id": patient_id, "date": d.strftime("%Y-%m-%d"),
                "mood": mood, "stress_level": stress, "sleep_hours": sleep,
                "craving_level": craving, "medication_taken": meds,
                "physical_activity_minutes": activity,
                "notes": "Needs follow-up." if level >= 3 and day == total_days - 1 else None,
                "created_at": d,
            })
    await db.daily_checkins.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.daily_checkins.insert_many(checkins)
    print(f"  ✓ {len(checkins)} daily check-ins created")


async def seed_clinical_notes(db):
    texts = [
        ("progress", "Patient is engaging well with treatment. Continue the current plan and monitor recovery trends."),
        ("observation", "Discussed coping strategies and reinforced the importance of completing daily check-ins."),
    ]
    notes = []
    for i, patient_id in enumerate(PATIENT_IDS):
        for j, (note_type, content) in enumerate(texts):
            notes.append({
                "patient_id": patient_id, "doctor_id": DOCTOR_IDS[i],
                "doctor_name": DOCTORS[i][1],
                "content": f"{PATIENTS[i][1]}: {content}",
                "note_type": "concern" if RISK_PROFILES[i] >= 3 and j == 1 else note_type,
                "created_at": days_ago(7 - j * 4),
            })
    await db.clinical_notes.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.clinical_notes.insert_many(notes)
    print(f"  ✓ {len(notes)} clinical notes created")


async def seed_recovery_goals(db):
    titles = [
        ("Complete weekly therapy sessions", "Attend every scheduled therapy session."),
        ("Maintain medication adherence", "Take prescribed medication according to the treatment plan."),
        ("Build a daily wellness routine", "Use exercise, sleep hygiene, and coping strategies consistently."),
    ]
    goals = []
    for i, patient_id in enumerate(PATIENT_IDS):
        level = RISK_PROFILES[i]
        statuses = ["completed", "in_progress", "in_progress"] if level == 0 else \
                   ["completed", "in_progress", "not_started"] if level == 1 else \
                   ["in_progress", "not_started", "not_started"] if level >= 3 else \
                   ["completed", "in_progress", "not_started"]
        for j, (title, desc) in enumerate(titles):
            goals.append({
                "patient_id": patient_id, "doctor_id": DOCTOR_IDS[i],
                "title": title, "description": desc, "status": statuses[j],
                "target_date": (NOW + timedelta(days=7 + j * 7)).strftime("%Y-%m-%d"),
                "notes": "Completed successfully." if statuses[j] == "completed" else None,
                "created_at": days_ago(30 + j * 3), "updated_at": days_ago(j + 1),
            })
    await db.recovery_goals.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.recovery_goals.insert_many(goals)
    print(f"  ✓ {len(goals)} recovery goals created")


async def seed_medications(db):
    meds = []
    medication_names = [
        ("Naltrexone", "50mg", "Once daily"),
        ("Buprenorphine/Naloxone", "8mg/2mg", "Once daily, sublingual"),
        ("Melatonin", "3mg", "Once nightly"),
        ("Acamprosate", "666mg", "Three times daily"),
        ("Bupropion", "150mg", "Once daily"),
    ]
    for i, patient_id in enumerate(PATIENT_IDS):
        name, dosage, frequency = medication_names[i]
        meds.append({
            "patient_id": patient_id, "doctor_id": DOCTOR_IDS[i],
            "doctor_name": DOCTORS[i][1], "name": name, "dosage": dosage,
            "frequency": frequency, "start_date": days_ago(30).strftime("%Y-%m-%d"),
            "end_date": None, "notes": "Demo medication record for testing.",
            "is_active": True, "created_at": days_ago(30), "updated_at": NOW,
        })
    await db.medications.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.medications.insert_many(meds)
    print(f"  ✓ {len(meds)} medications created")


async def seed_vitals(db):
    vitals = []
    for i, patient_id in enumerate(PATIENT_IDS):
        for j, day in enumerate([12, 6, 1]):
            base_hr = 72 + i * 2 + (4 if RISK_PROFILES[i] >= 3 else 0)
            vitals.append({
                "patient_id": patient_id, "recorded_by": DOCTOR_IDS[i],
                "recorded_by_name": DOCTORS[i][1], "recorded_at": days_ago(day),
                "blood_pressure": f"{118 + i + j * 2}/{76 + j}",
                "heart_rate": base_hr + j * 2, "temperature": 36.5 + (0.1 if i == 2 else 0),
                "weight": 65.0 + i * 6.5 - j * 0.2,
                "notes": "Monitor closely" if RISK_PROFILES[i] >= 3 and j == 2 else None,
            })
    await db.vitals.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.vitals.insert_many(vitals)
    print(f"  ✓ {len(vitals)} vital readings created")


async def seed_appointments(db):
    appointments = []
    for i, patient_id in enumerate(PATIENT_IDS):
        appointments.extend([
            {
                "patient_id": patient_id, "patient_name": PATIENTS[i][1],
                "doctor_id": DOCTOR_IDS[i], "doctor_name": DOCTORS[i][1],
                "hospital_id": HOSPITAL_IDS[i], "date_time": days_ago(5),
                "duration_minutes": 45, "reason": "Recovery progress review",
                "status": "completed", "notes": "Reviewed recovery progress and goals.",
                "created_at": days_ago(12), "updated_at": days_ago(5),
            },
            {
                "patient_id": patient_id, "patient_name": PATIENTS[i][1],
                "doctor_id": DOCTOR_IDS[i], "doctor_name": DOCTORS[i][1],
                "hospital_id": HOSPITAL_IDS[i], "date_time": NOW + timedelta(days=2 + i),
                "duration_minutes": 45, "reason": "Follow-up appointment",
                "status": "scheduled", "notes": None,
                "created_at": days_ago(2), "updated_at": days_ago(2),
            },
        ])
    await db.appointments.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.appointments.insert_many(appointments)
    print(f"  ✓ {len(appointments)} appointments created")


async def seed_alerts(db):
    alerts = []
    for i, patient_id in enumerate(PATIENT_IDS):
        level = RISK_PROFILES[i]
        alerts.append({
            "target_user_id": DOCTOR_IDS[i], "patient_id": patient_id,
            "patient_name": PATIENTS[i][1],
            "alert_type": "recovery_risk" if level >= 2 else "progress_update",
            "severity": "critical" if level == 4 else "high" if level == 3 else "medium" if level == 2 else "low",
            "message": "Recovery indicators require closer monitoring." if level >= 2 else "Recovery trend is stable; continue routine monitoring.",
            "is_read": False if level >= 2 else True, "created_at": days_ago(1),
        })
        alerts.append({
            "target_user_id": GUARDIAN_IDS[i], "patient_id": patient_id,
            "patient_name": PATIENTS[i][1], "alert_type": "checkin_update",
            "severity": "medium" if level >= 2 else "low",
            "message": "Patient recovery activity has been updated in RE:VIVE.",
            "is_read": False, "created_at": days_ago(0),
        })
    await db.alerts.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.alerts.insert_many(alerts)
    print(f"  ✓ {len(alerts)} alerts created")


async def seed_interventions(db):
    interventions = []
    for i, patient_id in enumerate(PATIENT_IDS):
        level = RISK_PROFILES[i]
        interventions.append({
            "patient_id": patient_id, "doctor_id": DOCTOR_IDS[i],
            "doctor_name": DOCTORS[i][1],
            "intervention_type": "escalation" if level >= 3 else "check_in_call",
            "description": "Care team contacted patient and reviewed coping strategies." if level < 3 else "Priority follow-up initiated due to concerning recovery indicators.",
            "alert_id": None,
            "outcome": None if level >= 3 else "Patient engaged with the care plan.",
            "outcome_status": "pending" if level >= 3 else "improved",
            "follow_up_date": (NOW + timedelta(days=2)).strftime("%Y-%m-%d"),
            "created_at": days_ago(2), "updated_at": days_ago(1),
        })
    await db.interventions.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.interventions.insert_many(interventions)
    print(f"  ✓ {len(interventions)} interventions created")


async def seed_treatment_plans(db):
    plans = []
    focus = [
        ["craving management", "social support", "exercise"],
        ["medication adherence", "trigger identification", "anxiety management"],
        ["sleep hygiene", "craving management", "exercise"],
        ["CBT", "group participation", "relapse prevention"],
        ["trigger management", "coping skills", "relapse prevention"],
    ]
    for i, patient_id in enumerate(PATIENT_IDS):
        plans.append({
            "patient_id": patient_id, "doctor_id": DOCTOR_IDS[i],
            "doctor_name": DOCTORS[i][1],
            "summary": f"Current recovery plan for {PATIENTS[i][1]}. Continue the assigned therapy program and monitor daily recovery indicators.",
            "focus_areas": focus[i],
            "review_date": (NOW + timedelta(days=14)).strftime("%Y-%m-%d"),
            "version": 1, "is_current": True, "created_at": days_ago(20), "superseded_at": None,
        })
    await db.treatment_plans.delete_many({"patient_id": oid_range(PATIENT_IDS)})
    await db.treatment_plans.insert_many(plans)
    print(f"  ✓ {len(plans)} treatment plans created")



async def seed_audit_logs(db):
    logs = []
    for i in range(5):
        logs.append({
            "user_id": HOSP_ADMIN_IDS[i], "actor_name": HOSP_ADMIN_DATA[i][1],
            "actor_role": "hospital", "actor_email": HOSP_ADMIN_DATA[i][0],
            "action": "create_user", "resource_type": "patient",
            "resource_id": str(PATIENT_IDS[i]),
            "details": {"patient": PATIENTS[i][1], "doctor": DOCTORS[i][1]},
            "ip_address": "127.0.0.1", "created_at": days_ago(20 + i),
        })
    for i in range(5):
        logs.append({
            "user_id": DOCTOR_IDS[i], "actor_name": DOCTORS[i][1],
            "actor_role": "doctor", "actor_email": DOCTORS[i][0],
            "action": "create_note", "resource_type": "clinical_note",
            "resource_id": None, "details": {"patient_id": str(PATIENT_IDS[i])},
            "ip_address": "127.0.0.1", "created_at": days_ago(3),
        })
    await db.audit_logs.delete_many({"user_id": {"$in": HOSP_ADMIN_IDS + DOCTOR_IDS}})
    await db.audit_logs.insert_many(logs)
    print(f"  ✓ {len(logs)} audit log entries created")


async def main():
    print("\n🌱 RE:VIVE — Seeding 5 profiles per module...\n")
    await connect_db()
    db = get_db()
    try:
        await seed_admins(db)
        await seed_hospitals_and_users(db)
        await seed_patient_profiles(db)
        await seed_checkins(db)
        await seed_clinical_notes(db)
        await seed_recovery_goals(db)
        await seed_medications(db)
        await seed_vitals(db)
        await seed_appointments(db)
        await seed_alerts(db)
        await seed_interventions(db)
        await seed_treatment_plans(db)
        await seed_audit_logs(db)
    finally:
        await close_db()

    print("\n" + "=" * 60)
    print("  ✅ ALL 5×5 RE:VIVE DEMO DATA SEEDED SUCCESSFULLY")
    print("=" * 60)
    print("\nPLATFORM ADMINS (password: admin123)")
    for email in ADMIN_EMAILS:
        print(f"  {email} / admin123")
    print("\nHOSPITAL ADMINS, DOCTORS, PATIENTS & GUARDIANS (password: Test@123)")
    for i in range(5):
        print(f"  Hospital {i+1}: {HOSP_ADMIN_DATA[i][0]}")
        print(f"  Doctor   {i+1}: {DOCTORS[i][0]}")
        print(f"  Patient  {i+1}: {PATIENTS[i][0]}")
        print(f"  Guardian {i+1}: {GUARDIANS[i][0]}")


if __name__ == "__main__":
    asyncio.run(main())
