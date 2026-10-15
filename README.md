<div align="center">

# RE:VIVE

🏆 **First place at Healix** · HEALS'26 · Institute of Engineering and Management

*Recovery doesn't stop between appointments. Care shouldn't either.*

</div>

---

Riya is six weeks sober. One Tuesday night her cravings hit 9 out of 10, and she tells no one.
Her mum can tell something's wrong but not what. Her doctor won't hear about it for three weeks,
until the next appointment, if at all.

Now the same night with RE:VIVE.

## How it works

**1. Riya checks in.** Before bed she spends two minutes logging her mood, cravings, stress,
sleep, medication and activity.

**2. Her recovery score updates.** RE:VIVE turns her last 30 days into a score from 0 to 100, and
explains every part of it in plain words, so she can see whether this week is better than last.

**3. The right people hear about it.** A craving of 9 crosses the line, so an alert goes straight
to her doctor and her mum. Missed doses, high stress and missed check-ins work the same way.

**4. Her doctor acts.** The next morning her doctor opens the alert, calls her, adjusts her care
plan and logs what was done.

**5. The loop closes.** All of it lands in one shared record. Three weeks later, the appointment
starts from what actually happened, not from what Riya can remember.

Along the way, a **digital twin** shows Riya and her doctor where her score is heading and what
would help most, and a **recovery risk model** (XGBoost with SHAP) flags who might need attention
and why.

Everyone sees the same record, but only their part of it. A hospital admin manages their own
hospital, a doctor sees their own patients, a guardian sees the person they support, and the
platform admin looks after the hospitals.

## Run it

You'll need Python 3.12–3.14 and MongoDB running locally.

```bash
git clone https://github.com/soham-newjourney2/Re-Vive.git
cd Re-Vive/backend

python -m venv venv
venv\Scripts\activate              # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
```

Put a long random `SECRET_KEY` in `backend/.env`
(`python -c "import secrets; print(secrets.token_urlsafe(48))"` makes one), then load the demo
data and start the server:

```bash
python seed_data.py
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** and pick a role. The demo login fills itself in, or use these:

| Role | Email | Password |
|------|-------|----------|
| Platform admin | `admin@revive.com` | `admin123` |
| Hospital admin | `hospital@test.com` | `Test@123` |
| Doctor | `doctor1@test.com` | `Test@123` |
| Patient | `patient1@test.com` | `Test@123` |
| Guardian | `guardian1@test.com` | `Test@123` |

There are five of each (`doctor1` to `doctor5`, and so on), all running on demo data.

To turn on the risk model as well, open a second terminal:

```bash
cd Re-Vive/recovery-risk-ai
python -m venv venv
venv\Scripts\activate              # macOS / Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn service:app --host 127.0.0.1 --port 8010
```

Everything else works without it.

## Built with

- **Backend:** FastAPI, MongoDB (Motor), Pydantic, JWT, APScheduler
- **Frontend:** plain JavaScript with no build step, in light and dark themes
- **AI:** XGBoost, SHAP, scikit-learn

The score maths, alert rules, security, configuration, API and tests are all written up in
**[docs/structure.md](docs/structure.md)**.

## The team

<div align="center">
<table>
  <tr>
    <td align="center" width="25%">
      <a href="https://github.com/soham-newjourney2">
        <img src="https://github.com/soham-newjourney2.png?size=200" width="110" alt="Soham Chowdhury">
      </a>
      <h3>Soham Chowdhury</h3>
      <sub><b>Team Lead</b> · Backend &amp; AI support</sub><br>
      <a href="https://github.com/soham-newjourney2">@soham-newjourney2</a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/Saswata427">
        <img src="https://github.com/Saswata427.png?size=200" width="110" alt="Saswata Biswas">
      </a>
      <h3>Saswata Biswas</h3>
      <sub>Backend support</sub><br>
      <a href="https://github.com/Saswata427">@Saswata427</a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/srijoyeemisra">
        <img src="https://github.com/srijoyeemisra.png?size=200" width="110" alt="Srijoyee Misra">
      </a>
      <h3>Srijoyee Misra</h3>
      <sub>Frontend</sub><br>
      <a href="https://github.com/srijoyeemisra">@srijoyeemisra</a>
    </td>
    <td align="center" width="25%">
      <a href="https://github.com/blacksayan6">
        <img src="https://github.com/blacksayan6.png?size=200" width="110" alt="Sayan Roy Chowdhury">
      </a>
      <h3>Sayan Roy Chowdhury</h3>
      <sub>AI &amp; ML</sub><br>
      <a href="https://github.com/blacksayan6">@blacksayan6</a>
    </td>
  </tr>
</table>

<sub>Ideas, issues and pull requests are welcome.</sub>
</div>
