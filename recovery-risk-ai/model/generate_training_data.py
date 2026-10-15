import random, csv, pathlib
random.seed(42)
out=pathlib.Path(__file__).resolve().parent/'training_data.csv'
fields=['days_post_procedure','age','pain_score','temperature_c','heart_rate_bpm','systolic_bp','diastolic_bp','oxygen_saturation_pct','sleep_hours','medication_adherence_pct','exercise_adherence_pct','daily_checkin_adherence_pct','symptom_severity','mood_score','recovery_progress_pct','goal_gap_count','recovery_risk']
rows=[]
for _ in range(300):
    pain=round(random.uniform(0,10),1); temp=round(random.uniform(36.3,38.2),1); hr=round(random.uniform(55,115),1); spo2=round(random.uniform(91,100),1); med=random.uniform(45,100); ex=random.uniform(30,100); check=random.uniform(40,100); symptoms=random.uniform(0,10); mood=random.uniform(3,10); progress=random.uniform(25,100); gaps=random.randint(0,6); days=random.randint(1,120); age=random.randint(18,80); sleep=random.uniform(4,9); sbp=random.uniform(90,160); dbp=random.uniform(55,100)
    score=0
    score += pain>=7; score += temp>=38; score += hr>=100; score += spo2<94; score += med<70; score += ex<55; score += check<65; score += symptoms>=7; score += mood<5; score += progress<50; score += gaps>=3
    risk=int(score>=3)
    rows.append([days,age, pain,temp,hr,sbp,dbp,spo2,round(sleep,1),round(med,1),round(ex,1),round(check,1),round(symptoms,1),round(mood,1),round(progress,1),gaps,risk])
with out.open('w',newline='') as f: csv.writer(f).writerows([fields]+rows)
print(out)
