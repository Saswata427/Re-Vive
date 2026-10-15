<div align="center">

# RE:VIVE

**One shared recovery record for hospitals, doctors, patients and the people who support them.**

🏆 **First place at Healix**, the hackathon at **HEALS'26**, Institute of Engineering and Management

[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-3776ab)](#run-it-locally)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)](#how-its-built)
[![MongoDB](https://img.shields.io/badge/MongoDB-database-47a248)](#run-it-locally)

</div>

---

## A Tuesday night

Riya is six weeks sober. It's a Tuesday night, her cravings hit nine out of ten, and she doesn't
tell anyone. It's late, her next appointment is three weeks away, and by then this will be one bad
night she half remembers.

Her mother can tell something is off but doesn't know what. Her doctor won't hear about it until
the next visit, if at all.

Now play the same night with RE:VIVE. Riya does her two-minute check-in before bed. The craving
spike raises an alert straight away, for her doctor and for her mother. The next morning her
doctor calls, adjusts her care plan and notes what was done. Three weeks later, the appointment
starts from what actually happened, not from what Riya can remember.

*Riya isn't a real patient, but her Tuesday is a very common one.*

## Why we built it

Recovery from addiction mostly happens **between** appointments, and the three people who care
about those days can't see them: the **patient**, who can't easily tell if this week beat last
week; the **doctor**, who only hears about a rough fortnight once the patient walks in; and the
**guardian** (a parent, partner or sponsor), who lives with the recovery every day but sits
outside the clinical system. RE:VIVE gives all three the same picture.

> [!NOTE]
> RE:VIVE is a working prototype running on demo data. It isn't a medical device and hasn't been
> clinically validated.

## How it works

```
Patient checks in  →  Alert engine spots a spike  →  Care team is notified
                                                              ↓
Record is updated  ←  Outcome is logged  ←  Doctor records what they did
```

The patient checks in once a day. That feeds a recovery score, and when the numbers turn bad an
alert goes to the doctor and the guardian. Whatever the doctor does about it goes back into the
record, so the next appointment starts from evidence instead of memory.

## Who uses it

| Role | What they can do |
|------|------------------|
| **Platform admin** | Add hospitals and their admins, see platform stats and the full audit trail |
| **Hospital admin** | Create doctors, patients and guardians, assign doctors, link guardians, see their hospital's audit trail |
| **Doctor** | Triage their caseload, keep notes, medications, vitals and goals, schedule visits, log interventions, write care plans |
| **Patient** | Check in daily, see their score explained in plain words, track progress, try the digital twin |
| **Guardian** | Follow their linked patient's progress, milestones and appointments, and get their alerts |

Every request checks who's asking. A doctor only sees their assigned patients, a guardian only
their linked patient, a hospital admin only their own hospital, and a patient only themselves.

---

## Run it locally

**You'll need** Python 3.12, 3.13 or 3.14, and MongoDB running on its default port.

```bash
git clone https://github.com/soham-newjourney2/Re-Vive.git
cd Re-Vive/backend

python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
```

Open `backend/.env` and give `SECRET_KEY` a long random value. This prints one for you:
`python -c "import secrets; print(secrets.token_urlsafe(48))"`. Then load the demo data and
start the server:

```bash
python seed_data.py
uvicorn app.main:app --reload --port 8000
```

Go to **http://127.0.0.1:8000**. There's nothing to build, because the backend serves the
frontend too. Pick a role on the welcome page and its demo login fills itself in. The API docs
live at **http://127.0.0.1:8000/docs**.

### Demo accounts

`seed_data.py` sets up five hospitals, each with an admin, a doctor, a patient and a guardian,
plus 10 to 14 days of check-ins per patient with notes, goals, medications, appointments and
alerts. Run it again any time to reset the demo data; other accounts are left alone.

| Role | Email | Password |
|------|-------|----------|
| Platform admin | `admin@revive.com` | `admin123` |
| Hospital admin | `hospital@test.com` … `hospital5@test.com` | `Test@123` |
| Doctor | `doctor1@test.com` … `doctor5@test.com` | `Test@123` |
| Patient | `patient1@test.com` … `patient5@test.com` | `Test@123` |
| Guardian | `guardian1@test.com` … `guardian5@test.com` | `Test@123` |

> [!WARNING]
> These passwords are public. The server warns you at startup while the demo admin password or a
> weak `SECRET_KEY` is still in use. Change both before running RE:VIVE anywhere but your own
> machine.

### Optional: the recovery risk AI

The doctor and patient screens have a recovery risk card backed by a small separate service.
Everything else works without it; the card just says it's unavailable. To run it, open a second
terminal:

```bash
cd Re-Vive/recovery-risk-ai
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
uvicorn service:app --host 127.0.0.1 --port 8010
```

Keep it on `127.0.0.1`. The browser never talks to it directly; the backend passes requests from
signed-in users through `/api/ai/predict`.

---

## Under the hood

### The recovery score

A score from 0 to 100 over the last 30 days. It's **worked out fresh on every request and never
stored**, so it can't fall out of step with the check-ins behind it.

| Part | Weight | Comes from |
|------|-------:|------------|
| Craving control | 25% | Average craving level (1–10), lower is better |
| Medication adherence | 20% | How often medication was taken |
| Stress management | 15% | Average stress level (1–10), lower is better |
| Sleep quality | 15% | How close sleep is to 7–9 hours |
| Physical activity | 10% | Daily minutes against a 30-minute target |
| Check-in engagement | 10% | How many days had a check-in |
| Goal progress | 5% | Goals completed out of the total |

Every part comes with its own score and a plain sentence explaining it, because a doctor won't
trust a number they can't question. A patient with fewer than three check-ins gets "not enough
data yet" instead of a zero, so someone new never looks like someone struggling.

### Alerts

| Alert | When it fires | Severity |
|-------|---------------|----------|
| `craving_spike` | craving of 8 or more | high (critical at 10) |
| `stress_spike` | stress of 8 or more | medium |
| `adherence_drop` | 2+ missed doses in the last 3 check-ins | high |
| `missed_checkin` | no check-in for 48 hours | medium |
| `appointment` | a visit is booked, moved or cancelled | low / medium |

Alerts go to the assigned doctors and the linked guardian, at most once per patient per day, and
to their phones if they've registered one. When a doctor logs what they did about an alert, their
copy is marked read. The guardian's copy stays, because the guardian hasn't seen it yet.

### Digital twin

A "what if" view built on the same score. It shows where the patient is today, where they're
heading if nothing changes (based on the last two weeks), and six scenarios that each improve one
part of the score. Since the score is a weighted sum, a scenario moves it by exactly
`(new − old) × weight ÷ 100`, so the twin can never disagree with the real score. The app labels it
as a prototype wherever it appears.

### Recovery risk AI

An XGBoost model that rates risk as LOW, MEDIUM or HIGH and uses SHAP to show which inputs pushed
it there. It's trained on **300 rows of synthetic data**, and most of its inputs (pain,
temperature, oxygen) aren't collected by RE:VIVE, so the app leaves them blank. Think of it as a
demo of the plumbing rather than a real risk score. [docs/structure.md](docs/structure.md#recovery-risk-ai)
explains how it's wired up and how to retrain it.

### Sessions and security

- **Short access tokens, rotating refresh tokens.** Access tokens last 15 minutes, since a JWT
  can't be revoked early. Staying signed in relies on a refresh token that changes on every use
  and is stored only as a hash.
- **Stolen-token detection.** If an old refresh token is used again, every session for that user
  is ended. Signing out on one device doesn't touch the others.
- **Seamless renewal.** When a request gets a 401 the browser renews the session once and retries,
  one renewal at a time so it never trips the check above.
- **Access checks everywhere**, through one shared helper so two routes to the same data can't
  disagree.
- **Safe output.** Anything a user typed is escaped before it reaches the page.
- **The basics.** bcrypt passwords, rate limits on sign-in and refresh, a CORS allowlist, and an
  audit trail for admins.

---

## Configuration

Settings live in `backend/.env`, and `.env.example` explains each one in a line.

| Variable | What it does | Default |
|----------|--------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Database name | `revive_db` |
| `SECRET_KEY` | Signs session tokens. **Change it.** | a public placeholder |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | How long you stay signed in | `30` |
| `CORS_ORIGINS` | Sites allowed to call the API | `localhost:8000, 127.0.0.1:8000` |
| `LOGIN_RATE_LIMIT` | Sign-in and refresh attempts per IP | `5/minute` |
| `RATELIMIT_STORAGE_URI` | Redis URL, for more than one worker | unset (in memory) |
| `PUSH_ENABLED` | Send phone notifications for alerts | `true` |
| `SCHEDULER_ENABLED` | Check for missed check-ins in the background | `true` |
| `AI_SERVICE_URL` | Where the risk AI runs | `http://127.0.0.1:8010` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Platform admin created on first start | `admin@revive.com` / `admin123` |

---

## How it's built

- **Backend:** FastAPI, Motor (async MongoDB), Pydantic v2, JWT, bcrypt, slowapi, APScheduler, httpx
- **Frontend:** plain JavaScript with no build step, a hash router with role checks, and light and
  dark themes that follow your system setting
- **AI service:** FastAPI, XGBoost, scikit-learn, SHAP

The folder layout, how the pieces talk to each other, the database collections and the full API
list are all in **[docs/structure.md](docs/structure.md)**.

## Tests

Run these from the repository root with the backend's virtual environment active:

```bash
# Recovery score and digital twin maths (no database needed)
python tests/test_recovery_and_twin.py

# Refresh tokens, push alerts, devices and the scheduler (uses a throwaway database)
python tests/test_mobile_backend.py

# The browser's session handling, against the running backend on :8000
node tests/test_session_client.mjs
```

Each one prints what it checked and stops with an error on the first failure. The session test
fires four requests with an expired token at once and checks that only one renewal happens.

## Known limitations

- **Review before production.** Set your own secrets. Rate limits are per process unless
  `RATELIMIT_STORAGE_URI` points at Redis.
- **Push alerts are best effort.** An alert is always saved and shown in the app; if a push fails,
  it's logged and nothing else breaks.
- **The digital twin and the risk model are prototypes.** Neither is clinically validated, and the
  app says so wherever they appear.
- **Older records.** Data saved before the current check-in format shows placeholders for the
  newer fields.

---

## The team

<div align="center">
<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/soham-newjourney2">
        <img src="https://github.com/soham-newjourney2.png?size=200" width="110" alt="Soham Chowdhury">
      </a>
      <h3>Soham Chowdhury</h3>
      <sub><b>Team Lead</b> · Backend &amp; AI support</sub><br><br>
      <a href="https://github.com/soham-newjourney2">
        <img src="https://img.shields.io/badge/GitHub-soham--newjourney2-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @soham-newjourney2" height="22">
      </a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/Saswata427">
        <img src="https://github.com/Saswata427.png?size=200" width="110" alt="Saswata Biswas">
      </a>
      <h3>Saswata Biswas</h3>
      <sub>Backend support</sub><br><br>
      <a href="https://github.com/Saswata427">
        <img src="https://img.shields.io/badge/GitHub-Saswata427-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @Saswata427" height="22">
      </a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/srijoyeemisra">
        <img src="https://github.com/srijoyeemisra.png?size=200" width="110" alt="Srijoyee Misra">
      </a>
      <h3>Srijoyee Misra</h3>
      <sub>Frontend</sub><br><br>
      <a href="https://github.com/srijoyeemisra">
        <img src="https://img.shields.io/badge/GitHub-srijoyeemisra-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @srijoyeemisra" height="22">
      </a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/blacksayan6">
        <img src="https://github.com/blacksayan6.png?size=200" width="110" alt="Sayan Roy Chowdhury">
      </a>
      <h3>Sayan Roy Chowdhury</h3>
      <sub>AI &amp; ML</sub><br><br>
      <a href="https://github.com/blacksayan6">
        <img src="https://img.shields.io/badge/GitHub-blacksayan6-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @blacksayan6" height="22">
      </a>
    </td>
  </tr>
</table>

<sub>Ideas, issues and pull requests are welcome.</sub>
</div>
