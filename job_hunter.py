import os
import time
import requests
from google import genai
from jobspy import scrape_jobs

# ১. ক্রেডেনশিয়াল
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("--- প্রসেস শুরু হচ্ছে ---")
print(f"Checking Secrets: Bot Token={'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}, Chat ID={'OK' if TELEGRAM_CHAT_ID else 'MISSING'}")

client = genai.Client(api_key=GEMINI_API_KEY)

# গুগল প্রস্তাবিত মূল মডেল এবং ব্যাকআপ মডেল
MODELS_TO_TRY = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

# ২. সার্চ কিওয়ার্ড ও দেশসমূহ
TARGET_ROLES = (
    "Automation Technician OR PLC Programmer OR Industrial Electrician OR "
    "Electrician OR Technician OR AC Technician OR HVAC Technician OR Machine Operator"
)

LOCATIONS = [
    "Serbia",
    "Latvia",
    "Romania",
    "Lithuania",
    "Slovenia",
    "Bangladesh",
]

all_jobs = []

for loc in LOCATIONS:
    print(f"\n🔍 Searching jobs for: {loc} ...")
    try:
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=TARGET_ROLES,
            location=loc,
            results_wanted=3,
            hours_old=8
        )
        if not jobs.empty:
            print(f" Found {len(jobs)} jobs in {loc}")
            all_jobs.append(jobs)
        else:
            print(f"⚪ No new jobs found in {loc}")
    except Exception as e:
        print(f"⚠️ Error fetching for {loc}: {e}")

# ৩. এআই ভেরিফিকেশন ও মেসেজ প্রস্তুতকরণ
verified_jobs = []

def evaluate_with_ai(prompt_text):
    for model_name in MODELS_TO_TRY:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt_text
            )
            return res.text.strip()
        except Exception:
            continue
    return None

if all_jobs:
    print(f"\nTotal countries with jobs: {len(all_jobs)}. Starting AI processing...")
    for df in all_jobs:
        for _, row in df.iterrows():
            title = str(row.get('title', 'N/A'))
            company = str(row.get('company', 'N/A'))
            location = str(row.get('location', 'N/A'))
            description = str(row.get('description', ''))[:2000]
            job_url = str(row.get('job_url', ''))

            prompt = f"""
            Analyze this job listing:
            Job Title: {title}
            Company: {company}
            Location: {location}
            Description: {description}

            Candidate Skillset:
            - Industrial wiring, electrical maintenance, control panels, AC/HVAC electrical controls.
            - Hands-on PLC/VFD troubleshooting (Siemens, Delta, Mitsubishi, Omron, LS).
            - Machine operation and maintenance.

            Task:
            1. Check if the listing is legitimate (reject if it requires upfront training/recruitment fees or looks like an obvious scam).
               If scam, reply ONLY: REJECT
            2. If legitimate, provide:
               - 1 short line: Validity reason.
               - 2 sentences: A concise cold application pitch highlighting matching electrical/automation skills.
            """

            time.sleep(1)
            ai_eval = evaluate_with_ai(prompt)

            if ai_eval and "REJECT" not in ai_eval:
                card = (
                    f"🏢 {title} at {company}\n"
                    f"📍 Location: {location}\n"
                    f"🔗 Link: {job_url}\n\n"
                    f"📝 AI Review & Pitch:\n{ai_eval}\n"
                    f"----------------------------------------"
                )
                verified_jobs.append(card)
                print(f" Verified Job: {title} ({company})")
            else:
                card = (
                    f"🏢 {title} at {company}\n"
                    f"📍 Location: {location}\n"
                    f"🔗 Link: {job_url}\n\n"
                    f"⚠️ (Direct Apply Link)\n"
                    f"----------------------------------------"
                )
                verified_jobs.append(card)
                print(f" Added Job: {title} ({company})")

            if len(verified_jobs) >= 8:
                break
        if len(verified_jobs) >= 8:
            break
else:
    print("\n⚠️ No jobs were found across all locations.")

# ৪. টেলিগ্রামে মেসেজ পাঠানো
def notify_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            print(f"Telegram Error ({response.status_code}): {response.text}")
    except Exception as err:
        print(f"Telegram Connection Error: {err}")

# ৫. ফাইনাল ডেলিভারি
if verified_jobs:
    notify_telegram(f"⚡ আজকের বাছাইকৃত টেকনিক্যাল জব ({len(verified_jobs)}টি পাওয়া গেছে):")
    for msg in verified_jobs:
        notify_telegram(msg)
    print(f"\n✅ Successfully sent {len(verified_jobs)} jobs to Telegram.")
else:
    notify_telegram("আজকের স্ক্যানে কোনো উপযুক্ত সার্কুলার পাওয়া যায়নি।")
    print("\n Sent empty notification to Telegram.")
