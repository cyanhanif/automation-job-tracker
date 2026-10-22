import os
import requests
import google.generativeai as genai
from jobspy import scrape_jobs

# ১. ক্রেডেনশিয়াল লোড
GEMINI_API_KEY = os.getenv("AQ.Ab8RN6Ilg_Yxyu6-3eWGV1zfzxMdFkEgjrLKwLLYBZa0S7cRPw")
TELEGRAM_BOT_TOKEN = os.getenv("8952845466:AAEuLss6QYjPyFVo69mi3XVKPzWf8mey25E")
TELEGRAM_CHAT_ID = os.getenv("5810650897")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ২. টার্গেট পজিশন ও দেশ নির্বাচন
TARGET_ROLES = "Automation Technician OR PLC Programmer OR Industrial Electrician OR Maintenance Electrician OR Machine Operator"
LOCATIONS = [
    "Bangladesh",
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Poland",
    "Czechia",
    "Serbia"
]

all_jobs = []

for loc in LOCATIONS:
    try:
        # গত ৮ ঘণ্টার জবগুলো খোঁজা হবে
        jobs = scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=TARGET_ROLES,
            location=loc,
            results_wanted=4,
            hours_old=8
        )
        if not jobs.empty:
            all_jobs.append(jobs)
    except Exception as e:
        print(f"Fetch failed for {loc}: {e}")

# ৩. জবের সত্যতা যাচাই ও মেসেজ তৈরি
verified_jobs = []

for df in all_jobs:
    for _, row in df.iterrows():
        title = str(row.get('title', 'N/A'))
        company = str(row.get('company', 'N/A'))
        location = str(row.get('location', 'N/A'))
        description = str(row.get('description', ''))[:2500]
        job_url = str(row.get('job_url', ''))

        # ফেক জব ফিল্টারিং এবং কভার মেসেজ প্রম্পট
        prompt = f"""
        Act as an Industrial Automation Technical Recruiter and Job Fraud Detection Expert.
        
        Analyze this job listing:
        - Title: {title}
        - Company: {company}
        - Location: {location}
        - Description: {description}
        
        Evaluation Guidelines:
        1. Fraud / Scam Check:
           - Red flags: Demanding registration fees/training money upfront, free visa guarantees without interview, generic Gmail/WhatsApp contacts for multinational jobs, unrealistic promises.
           - Give a legitimacy score from 1 to 10 (1 = Obvious scam/fake, 10 = Verified direct employer/factory).
        
        2. Candidate Match:
           - Candidate knows Siemens (TIA Portal), Delta, Mitsubishi, Omron, LS PLCs, VFDs, and Industrial wiring.
        
        Instructions:
        - If Legitimacy Score is BELOW 7, output ONLY the word "REJECTED_SCAM".
        - If Legitimacy Score is 7 or above:
          Provide a concise response in Bengali/English:
          [Legitimacy Score: X/10 - Short Reason]
          [Cold Message / Cover Pitch (under 80 words)] tailored to this specific job.
        """

        try:
            ai_eval = model.generate_content(prompt).text.strip()
            if "REJECTED_SCAM" not in ai_eval:
                card = (
                    f"🏢 *{title}* | {company}\n"
                    f"📍 {location}\n"
                    f"🔗 [Apply Here]({job_url})\n\n"
                    f"🔍 *AI Analysis & Pitch:*\n{ai_eval}\n"
                    f"────────────────────"
                )
                verified_jobs.append(card)
        except Exception as e:
            continue

        if len(verified_jobs) >= 8:
            break
    if len(verified_jobs) >= 8:
        break

# ৪. টেলিগ্রামে নোটিফিকেশন পাঠানো
def notify_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if verified_jobs:
    notify_telegram(f"⚡ *প্রতি ৮ ঘণ্টার অটোমেশন জব আপডেট ({len(verified_jobs)}টি ভেরিফাইড জব):*")
    for msg in verified_jobs:
        notify_telegram(msg)
else:
    notify_telegram("গত ৮ ঘণ্টায় কোনো নতুন ভেরিফাইড বা রিয়েল সার্কুলার পাওয়া যায়নি।")
