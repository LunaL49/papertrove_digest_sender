
from supabase import create_client
import os
import resend
import datetime
import time

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RESEND_API = os.environ["RESEND_API"]
resend.api_key = RESEND_API

users = supabase.table("users").select("email, frequency, digest_length").execute().data

today = datetime.datetime.today()
today_format = today.strftime("%d %b")

for i in range(0, len(users)):
  # handle days of the week, break if the day is not one where digests need to be sent
  if users[i]["frequency"] == "daily" and today.weekday() in [5, 6]: # no digests on Saturday or Sunday
    print("No digest today.")
    continue
  if users[i]["frequency"] == "biweekly" and today.weekday() in [1,2,4,5,6]: # no digests on any day other than Monday & Thursday
    print("No digest today.")
    continue
  if users[i]["frequency"] == "weekly" and today.weekday() != 0 : # no digests on any day other than Monday
    print("No digest today.")
    continue

  # otherwise send digest
  print("Sending digest...")
  recommendations = supabase.table("recommendations").select("*").eq("user_email",users[i]["email"]).execute().data
  digest_len = users[i]["digest_length"]
  
  sorted_papers = sorted(recommendations, key=lambda x: x['score'], reverse=True)
  if len(sorted_papers) > users[i]["digest_length"]:
    papers = sorted_papers[:users[i]["digest_length"]]
  else:
    papers = sorted_papers

  html_content = f'''
    <div style="margin: 20px auto; max-width: 800px; padding: 20px; background-color: #ffffff; font-family: Arial, sans-serif; border: 1px solid #e0e0e0; border-radius: 8px;">
      <div style="background-color: #0fa3b1; padding: 15px 20px; border-radius: 6px;">
        <div style="background-color: #0fa3b1; padding: 15px 20px; border-radius: 6px;">
          <h2 style="margin: 0; color: #ffffff; font-size: 22px;">
            Research Digest - {today_format}
          </h2>
        </div>
      </div>
    '''

  # Add blocks using a loop
  for j in range(len(papers)):
    author_line = f'<p style="margin: 0 0 10px 0; color: #888888; font-size: 13px;">By {papers[j]["author"]} et al. </p>' if papers[j].get("author") else ""
    block = f'''
    <div style="margin-top: 20px; padding: 15px; border-left: 5px solid #f7a072; background-color: #f9f9f9; border-radius: 6px;">
        <h3 style="margin: 0 0 5px 0; color: #0fa3b1; font-size: 18px;">
            <a href="{papers[j]["link"]}" style="color: #0fa3b1; text-decoration: none;">
                {papers[j]["title"]} <span style="font-size: 14px; color: #aaaaaa;">(link)</span>
            </a>
        </h3>
        {author_line}
        <p style="margin: 0; color: #333333; font-size: 14px; line-height: 1.5;">
            {papers[j]["abstract"]}
        </p>
    </div>
    '''
    html_content += block

  # Add footer
  html_content += '''
    <p style="margin-top: 30px; font-size: 12px; color: #999999; text-align: center;">
        You’re receiving this email because you have subscribed to the research digest from papertrove.ai.<br>
        <a href="https://papertrove.ai/unsubscribe" style="color: #f7a072; text-decoration: none;">Unsubscribe</a>
    </p>
  </div>
  '''

  params: resend.Emails.SendParams = {
  "from": "Papertrove.ai <digest@mail.papertrove.ai>",
  "to": [users[i]["email"]],
  "subject": "Your research digest from Papertrove.ai",
  "html": html_content
  }
  email = resend.Emails.send(params)
  time.sleep(1)

  if email:
    print("One digest sent, now deleting relevant data from database...")
    supabase.table("recommendations").delete().eq('user_email', users[i]["email"]).execute()
