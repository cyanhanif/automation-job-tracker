import os
import requests
import google.generativeai as genai
from jobspy import scrape_jobs

# ১. সিক্রেট কি লোড
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("--- প্রসেস শুরু হচ্ছে ---")
print(f"Checking Secrets: Bot Token={'OK' if TELEGRAM_BOT_TOKEN else 'MISSING'}, Chat ID={'OK' if TELEGRAM_CHAT_ID else 'MISSING'}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

TARGET_ROLES = "Automation Technician OR PLC Programmer OR Industrial Electrician"
LOCATIONS = [
    "Bangladesh",
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Poland"
]

all_jobs = []

# ২. জব স্ক্র্যাপিং ও লাইভ লগ
for loc in LOCATIONS:
    print(f"\n🔍 Searching jobs for: {loc} ...")
    try:
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor", "google"],
            search_term=TARGET_ROLES,
            location=loc,
            results_wanted=3,
            hours_old=72  # টেস্ট রানের জন্য ৭২ ঘণ্টা দেওয়া হয়েছে যাতে নিশ্চিত জব পাওয়া যায়
        )
        if not jobs.empty:
            print(f" Found {len(jobs)} jobs in {loc}")
            all_jobs.append(jobs)
        else:
            print(f"⚪ No new jobs found in {loc}")
    except Exception as e:
        print(f"⚠️ Error fetching for {loc}: {e}")

# ৩. ভেরিফিকেশন ও মেসেজ ড্রাফট
verified_jobs = []

if all_jobs:
    print(f"\nTotal countries with jobs: {len(all_jobs)}. Starting AI evaluation...")
    for df in all_jobs:
        for _, row in df.iterrows():
            title = str(row.get('title', 'N/A'))
            company = str(row.get('company', 'N/A'))
            location = str(row.get('location', 'N/A'))
            description = str(row.get('description', ''))[:2000]
            job_url = str(row.get('job_url', ''))

            prompt = f"""
            Analyze this job for an automation technician (Siemens, Delta, Mitsubishi, Omron, LS):
            Job Title: {title}
            Company: {company}
            Location: {location}
            Description: {description}

            Check if it seems legitimate (not an upfront money scam).
            If scam, reply ONLY 'REJECT'.
            If legitimate, give 1 line validation reason and a 2-sentence cold message.
            """

            try:
                ai_eval = model.generate_content(prompt).text.strip()
                if "REJECT" not in ai_eval:
                    card = (
                        f"🏢 {title} at {company}\n"
                        f"📍 Location: {location}\n"
                        f"🔗 Link: {job_url}\n\n"
                        f"📝 AI Review & Pitch:\n{ai_eval}\n"
                        f"----------------------------------------"
                    )
                    verified_jobs.append(card)
                    print(f" Verified Job: {title} ({company})")
            except Exception as e:
                print(f"AI generation failed for {title}: {e}")

            if len(verified_jobs) >= 5:
                break
        if len(verified_jobs) >= 5:
            break
else:
    print("\n⚠️ No jobs were found across all locations.")

# ৪. টেলিগ্রামে নোটিফিকেশন পাঠানো (নিরাপদ ফরম্যাট)
def notify_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Telegram API Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Telegram API Error Details: {response.text}")
    except Exception as err:
        print(f"Failed to connect to Telegram: {err}")

# ৫. ফাইনাল সেন্ডিং
if verified_jobs:
    notify_telegram(f"⚡ আজকের ভেরিফাইড অটোমেশন জব ({len(verified_jobs)}টি পাওয়া গেছে):")
    for msg in verified_jobs:
        notify_telegram(msg)
    print("\n✅ All messages dispatched to Telegram.")
else:
    notify_telegram("আজকের স্ক্যানে কোনো উপযুক্ত সার্কুলার পাওয়া যায়নি বা স্ক্র্যাপারে জব আসেনি।")
    print("\n Sent empty notification to Telegram.")
