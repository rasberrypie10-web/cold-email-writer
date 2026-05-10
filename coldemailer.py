import streamlit as st
import requests
import json
import re
from datetime import datetime, timezone

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cold Email Writer Pro",
    page_icon="✉️",
    layout="centered",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { max-width: 860px; padding-top: 1.5rem; }
    .email-box {
        background: #f8f8f8;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        font-size: 0.95rem;
        line-height: 1.8;
        white-space: pre-wrap;
    }
    .subject-box {
        background: #f0f0f0;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .flag { color: #e74c3c; font-weight: bold; }
    .ok   { color: #2ecc71; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Load credentials ──────────────────────────────────────────────────────────
try:
    account_id    = st.secrets["CF_ACCOUNT_ID"]
    api_token     = st.secrets["CF_API_TOKEN"]
    sb_url        = st.secrets["SUPABASE_URL"]
    sb_key        = st.secrets["SUPABASE_KEY"]
    admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
    valid_passwords = [p.strip() for p in st.secrets.get("PASSWORDS", "").split(",") if p.strip()]
except Exception as e:
    st.error(f"Server configuration error: {e}")
    st.stop()

# ── Supabase helpers ──────────────────────────────────────────────────────────
SB_HEADERS = {
    "apikey": sb_key,
    "Authorization": f"Bearer {sb_key}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def sb_insert(table, data):
    try:
        requests.post(f"{sb_url}/rest/v1/{table}", headers=SB_HEADERS, json=data, timeout=5)
    except Exception:
        pass

def sb_select(table, filters=""):
    try:
        r = requests.get(f"{sb_url}/rest/v1/{table}?{filters}&order=timestamp.desc",
                         headers={**SB_HEADERS, "Prefer": "return=representation"}, timeout=5)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

def sb_delete(table, column, value):
    try:
        requests.delete(f"{sb_url}/rest/v1/{table}?{column}=eq.{value}",
                        headers=SB_HEADERS, timeout=5)
    except Exception:
        pass

def get_ip_info():
    try:
        r = requests.get("https://ipapi.co/json/", timeout=5)
        if r.status_code == 200:
            d = r.json()
            return d.get("ip", "unknown"), d.get("country_name", "unknown"), d.get("city", "unknown")
    except Exception:
        pass
    return "unknown", "unknown", "unknown"

def log_access(password, ip, country, city, device):
    sb_insert("access_logs", {
        "password": password,
        "ip_address": ip,
        "country": country,
        "city": city,
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

def check_suspicious(password, current_ip):
    logs = sb_select("access_logs", f"password=eq.{password}&limit=100")
    if not logs:
        return False, 0, []
    ips = list(set(l.get("ip_address", "") for l in logs if l.get("ip_address") != "unknown"))
    countries = list(set(l.get("country", "") for l in logs if l.get("country") != "unknown"))
    suspicious = len(ips) >= 5 or len(countries) >= 3
    return suspicious, len(ips), countries

# ── Auth ──────────────────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_password" not in st.session_state:
    st.session_state.current_password = ""

if not st.session_state.authenticated:
    st.markdown("## ✉️ Cold Email Writer Pro")
    st.markdown("Enter your access password to continue.")
    st.divider()
    pwd = st.text_input("Access password", type="password", placeholder="Enter your password")
    if st.button("Login", use_container_width=True, type="primary"):
        if pwd == admin_password:
            st.session_state.authenticated = True
            st.session_state.is_admin = True
            st.session_state.current_password = "admin"
            st.rerun()
        elif pwd in valid_passwords:
            ip, country, city = get_ip_info()
            device = "Browser"
            suspicious, ip_count, countries = check_suspicious(pwd, ip)
            log_access(pwd, ip, country, city, device)
            st.session_state.authenticated = True
            st.session_state.is_admin = False
            st.session_state.current_password = pwd
            if suspicious:
                st.session_state.suspicious_alert = f"⚠️ Password used from {ip_count} IPs across {countries}"
            st.rerun()
        else:
            st.error("Incorrect password. Please check your access code.")
    st.stop()

# ── Admin dashboard ───────────────────────────────────────────────────────────
if st.session_state.is_admin:
    st.markdown("## 🛡️ Admin Dashboard")
    st.divider()

    logs = sb_select("access_logs", "limit=200")

    if logs:
        # Group by password
        from collections import defaultdict
        grouped = defaultdict(list)
        for log in logs:
            grouped[log.get("password", "unknown")].append(log)

        st.markdown(f"### 👥 Active passwords ({len(grouped)} total)")
        for pwd_key, entries in grouped.items():
            ips = list(set(e.get("ip_address", "") for e in entries if e.get("ip_address") != "unknown"))
            countries = list(set(e.get("country", "") for e in entries if e.get("country") != "unknown"))
            last_seen = entries[0].get("timestamp", "")[:16].replace("T", " ") if entries else "never"
            suspicious = len(ips) >= 5 or len(countries) >= 3

            flag = "🚨 FLAGGED" if suspicious else "✅ Normal"
            with st.expander(f"{flag} · `{pwd_key}` · {len(entries)} logins · Last: {last_seen}"):
                st.markdown(f"**Unique IPs:** {len(ips)} — {', '.join(ips[:10])}")
                st.markdown(f"**Countries:** {', '.join(countries) if countries else 'unknown'}")

                st.markdown("**Recent logins:**")
                for e in entries[:5]:
                    ts = e.get("timestamp", "")[:16].replace("T", " ")
                    st.markdown(f"- {ts} · {e.get('country','?')} · {e.get('city','?')} · {e.get('ip_address','?')}")

                if st.button(f"🚫 Revoke access for `{pwd_key}`", key=f"revoke_{pwd_key}"):
                    sb_delete("access_logs", "password", pwd_key)
                    st.success(f"Revoked all logs for `{pwd_key}`. Remove from PASSWORDS in secrets to block login.")
    else:
        st.info("No access logs yet.")

    st.divider()
    if st.button("Sign out"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.rerun()
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
for key in ["history", "current_email", "current_subject",
            "variation_b", "subject_b", "followup", "score_data", "subject_vars"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "history" else None

# ── AI helpers ────────────────────────────────────────────────────────────────
def call_ai(prompt, system="You are a helpful assistant. Return only raw JSON."):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt}
            ],
            "max_tokens": 2048
        },
        timeout=45
    )
    if r.status_code != 200:
        raise Exception(f"API error {r.status_code}: {r.text}")
    return r.json().get("result", {}).get("response", "")

def extract_json(raw):
    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        raise Exception("Could not parse AI response. Try again.")
    return json.loads(match.group())

# ── Header ────────────────────────────────────────────────────────────────────
if hasattr(st.session_state, "suspicious_alert"):
    st.warning(st.session_state.suspicious_alert)
    del st.session_state.suspicious_alert

c1, c2 = st.columns([4, 1])
with c1:
    st.markdown("## ✉️ Cold Email Writer Pro")
    st.markdown("*Generate, refine, score and perfect your cold emails with AI*")
with c2:
    if st.button("Sign out", key="signout"):
        st.session_state.authenticated = False
        st.session_state.current_password = ""
        st.rerun()

st.divider()

# ── INPUTS ────────────────────────────────────────────────────────────────────
st.markdown("### ⚙️ Email settings")

with st.expander("📋 Business details", expanded=True):
    c1, c2, c3 = st.columns(3)
    biz_name    = c1.text_input("Business name", placeholder="e.g. NexBot AI")
    product     = c2.text_input("Product / service", placeholder="e.g. AI chatbot for restaurants")
    sender_name = c3.text_input("Your name (optional)", placeholder="e.g. Alex")
    c4, c5 = st.columns(2)
    target  = c4.text_input("Target customer", placeholder="e.g. local pizza shops in Chicago")
    benefit = c5.text_input("Key benefit", placeholder="e.g. saves 5 hours/week on customer questions")

with st.expander("🎨 Tone & style", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        tone = st.select_slider("Tone", options=[
            "Very casual", "Casual", "Friendly & professional",
            "Professional", "Formal", "Very formal"
        ], value="Friendly & professional")
    with c2:
        energy = st.select_slider("Energy", options=[
            "Very soft", "Soft", "Balanced", "Direct", "Aggressive"
        ], value="Balanced")
    with c3:
        length = st.select_slider("Length", options=[
            "Very short (50w)", "Short (80w)", "Medium (120w)", "Long (160w)"
        ], value="Short (80w)")

    c4, c5, c6 = st.columns(3)
    with c4:
        humor      = st.checkbox("Add humor 😄")
        emoji_mode = st.checkbox("Include emojis")
    with c5:
        ps_line  = st.checkbox("Add a P.S. line")
        urgency  = st.checkbox("Add urgency")
    with c6:
        ab_test      = st.checkbox("Generate A/B variation")
        gen_followup = st.checkbox("Generate follow-up email")

with st.expander("📣 Call to action & targeting"):
    c1, c2, c3 = st.columns(3)
    cta = c1.selectbox("Primary CTA", [
        "Book a free 15-minute call",
        "Reply to this email to learn more",
        "Try it free for 7 days",
        "Visit our website",
        "Schedule a quick demo",
        "Claim a free audit",
    ])
    language = c2.selectbox("Language", [
        "English", "Spanish", "French", "German",
        "Portuguese", "Italian", "Dutch", "Japanese"
    ])
    industry = c3.selectbox("Target industry", [
        "Any", "Restaurant / Food", "Real estate", "E-commerce",
        "Healthcare", "Legal", "Marketing agency", "SaaS / Tech",
        "Retail", "Fitness / Wellness", "Education", "Finance"
    ])

with st.expander("🔧 Advanced options"):
    c1, c2 = st.columns(2)
    with c1:
        auto_score         = st.checkbox("Auto-score email", value=True)
        subject_variations = st.checkbox("Generate 3 subject line options")

generate = st.button("✨ Generate email", use_container_width=True, type="primary")

# ── GENERATION ────────────────────────────────────────────────────────────────
if generate:
    if not biz_name or not product or not target:
        st.error("Please fill in: business name, product, and target customer.")
    else:
        length_map = {
            "Very short (50w)": "50 words max",
            "Short (80w)":      "80 words max",
            "Medium (120w)":    "120 words max",
            "Long (160w)":      "160 words max",
        }
        word_limit = length_map[length]

        base_prompt = f"""Write a cold email with these exact parameters:
Business name: {biz_name}
Product/service: {product}
Target customer: {target}
Key benefit: {benefit if benefit else 'not specified'}
Sender name: {sender_name if sender_name else 'not specified'}
Tone: {tone}
Energy level: {energy}
Length: {word_limit}
Humor: {'yes, add a light touch of humor' if humor else 'no'}
Emojis: {'yes, use relevant emojis' if emoji_mode else 'no'}
P.S. line: {'yes, add a clever P.S. line' if ps_line else 'no'}
Call to action: {cta}
Urgency: {'yes, add urgency' if urgency else 'no'}
Language: {language}
Industry context: {industry if industry != 'Any' else 'general'}

Return ONLY raw JSON, no markdown, no backticks:
{{"subject":"subject here","body":"body here with \\n for line breaks"}}

Rules:
- Subject: under 50 chars, curiosity-driven, no spam words
- No 'I hope this finds you well'
- Sound human, not robotic
- Respect the word limit"""

        with st.spinner("✍️ Writing your email..."):
            try:
                raw  = call_ai(base_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                data = extract_json(raw)
                st.session_state.current_subject = data.get("subject", "")
                st.session_state.current_email   = data.get("body", "")
                st.session_state.variation_b  = None
                st.session_state.subject_b    = None
                st.session_state.followup     = None
                st.session_state.score_data   = None
                st.session_state.subject_vars = None
            except Exception as e:
                st.error(f"Generation failed: {e}")

        if ab_test and st.session_state.current_email:
            with st.spinner("🔀 Generating A/B variation..."):
                try:
                    ab_prompt = base_prompt.replace(
                        "Return ONLY raw JSON",
                        "Write a COMPLETELY DIFFERENT version with a different angle and hook. Return ONLY raw JSON"
                    )
                    raw_b  = call_ai(ab_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                    data_b = extract_json(raw_b)
                    st.session_state.variation_b = data_b.get("body", "")
                    st.session_state.subject_b   = data_b.get("subject", "")
                except Exception:
                    pass

        if gen_followup and st.session_state.current_email:
            with st.spinner("📨 Writing follow-up email..."):
                try:
                    fu_prompt = f"""Write a short follow-up cold email for someone who did not reply to this:
Original: {st.session_state.current_email}
Business: {biz_name}, Product: {product}, Target: {target}
Keep it under 60 words, friendly, briefly reference the first email.
Return ONLY raw JSON: {{"subject":"Re: ...","body":"followup body"}}"""
                    raw_fu  = call_ai(fu_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                    fu_data = extract_json(raw_fu)
                    st.session_state.followup = fu_data.get("body", "")
                except Exception:
                    pass

        if subject_variations and st.session_state.current_email:
            with st.spinner("📌 Generating subject line options..."):
                try:
                    sv_prompt = f"""Generate 3 different subject lines for this cold email:
{st.session_state.current_email}
Business: {biz_name}, Product: {product}
Return ONLY raw JSON: {{"subjects":["subject 1","subject 2","subject 3"]}}"""
                    raw_sv  = call_ai(sv_prompt, "Return only raw JSON.")
                    sv_data = extract_json(raw_sv)
                    st.session_state.subject_vars = sv_data.get("subjects", [])
                except Exception:
                    pass

        if auto_score and st.session_state.current_email:
            with st.spinner("📊 Scoring your email..."):
                try:
                    score_prompt = f"""Score this cold email and return ONLY raw JSON:
Subject: {st.session_state.current_subject}
Body: {st.session_state.current_email}
Return exactly:
{{"overall":85,"subject_score":80,"body_score":85,"cta_score":90,"tips":["tip 1","tip 2","tip 3"]}}
Scores 0-100. Tips are specific and actionable."""
                    raw_sc = call_ai(score_prompt, "You are a cold email expert. Return only raw JSON.")
                    st.session_state.score_data = extract_json(raw_sc)
                except Exception:
                    pass

        if st.session_state.current_email:
            st.session_state.history.insert(0, {
                "time":    datetime.now().strftime("%H:%M"),
                "subject": st.session_state.current_subject,
                "body":    st.session_state.current_email,
                "biz":     biz_name,
            })
            if len(st.session_state.history) > 20:
                st.session_state.history = st.session_state.history[:20]

# ── OUTPUT ────────────────────────────────────────────────────────────────────
if st.session_state.current_email:
    st.divider()
    st.markdown("### 📨 Your email")

    tab_labels = ["📧 Version A"]
    if st.session_state.variation_b:
        tab_labels.append("📧 Version B")
    if st.session_state.followup:
        tab_labels.append("📨 Follow-up")
    tabs = st.tabs(tab_labels)

    def show_email_tab(tab, subject, body, key_suffix):
        with tab:
            st.markdown(f'<div class="subject-box"><strong>Subject:</strong> {subject}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="email-box">{body}</div>', unsafe_allow_html=True)

            words = len(body.split())
            m1, m2, m3 = st.columns(3)
            m1.metric("Words", words)
            m2.metric("Read time", f"~{max(1, words // 200)} min")
            m3.metric("Est. reply rate", "4–7%")

            st.markdown("**🎛️ Refine this email:**")
            adjustments = {
                "😄 Funnier":    "more fun and humorous",
                "😐 Serious":    "more serious and formal",
                "✂️ Shorter":    "shorter, cut to 60 words max",
                "📝 Longer":     "longer with more detail, 150 words",
                "💪 Bolder":     "more bold, direct and aggressive",
                "🕊️ Softer":     "softer, warmer and more gentle",
                "🎯 Punchier":   "punchier with a stronger hook",
                "🤝 Friendlier": "more friendly and personable",
            }
            cols = st.columns(4)
            for i, (btn_label, instruction) in enumerate(adjustments.items()):
                if cols[i % 4].button(btn_label, key=f"refine_{key_suffix}_{i}"):
                    with st.spinner("Rewriting..."):
                        try:
                            refine_prompt = f"""Rewrite this cold email to be {instruction}. Keep the same core message and CTA.
Subject: {subject}
Body: {body}
Return ONLY raw JSON: {{"subject":"new subject","body":"new body with \\n for line breaks"}}"""
                            raw_r   = call_ai(refine_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                            refined = extract_json(raw_r)
                            if key_suffix == "A":
                                st.session_state.current_subject = refined.get("subject", subject)
                                st.session_state.current_email   = refined.get("body", body)
                            else:
                                st.session_state.subject_b   = refined.get("subject", subject)
                                st.session_state.variation_b = refined.get("body", body)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Refinement failed: {e}")

            d1, d2 = st.columns(2)
            d1.download_button("⬇️ Download .txt",
                data=f"Subject: {subject}\n\n{body}",
                file_name=f"cold_email_{key_suffix}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"dl_txt_{key_suffix}")
            d2.download_button("⬇️ Download .md",
                data=f"# Cold Email\n\n**Subject:** {subject}\n\n---\n\n{body}",
                file_name=f"cold_email_{key_suffix}.md",
                mime="text/markdown",
                use_container_width=True,
                key=f"dl_md_{key_suffix}")

    show_email_tab(tabs[0], st.session_state.current_subject, st.session_state.current_email, "A")
    if st.session_state.variation_b and len(tabs) > 1:
        show_email_tab(tabs[1], st.session_state.subject_b, st.session_state.variation_b, "B")
    if st.session_state.followup:
        with tabs[-1]:
            st.markdown(f'<div class="email-box">{st.session_state.followup}</div>', unsafe_allow_html=True)
            st.download_button("⬇️ Download follow-up",
                data=st.session_state.followup,
                file_name="followup.txt",
                mime="text/plain",
                key="dl_fu")

    if st.session_state.subject_vars:
        st.divider()
        st.markdown("**📌 Subject line options:**")
        for i, s in enumerate(st.session_state.subject_vars, 1):
            st.markdown(f"`{i}.` {s}")

    if st.session_state.score_data:
        st.divider()
        st.markdown("**📊 Email quality score:**")
        sd = st.session_state.score_data
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Overall",  f"{sd.get('overall', 0)}/100")
        sc2.metric("Subject",  f"{sd.get('subject_score', 0)}/100")
        sc3.metric("Body",     f"{sd.get('body_score', 0)}/100")
        sc4.metric("CTA",      f"{sd.get('cta_score', 0)}/100")
        if sd.get("tips"):
            st.markdown("**💡 Tips to improve:**")
            for tip in sd["tips"]:
                st.markdown(f"- {tip}")

# ── History ───────────────────────────────────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.markdown("### 🕓 Session history")
    for i, item in enumerate(st.session_state.history[:10]):
        with st.expander(f"{item['time']} · {item['biz']} · \"{item['subject']}\""):
            st.markdown(f'<div class="email-box">{item["body"]}</div>', unsafe_allow_html=True)
            if st.button("↩️ Load this email", key=f"load_{i}"):
                st.session_state.current_subject = item["subject"]
                st.session_state.current_email   = item["body"]
                st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p style='text-align:center;color:#aaa;font-size:0.8rem;'>Cold Email Writer Pro · Powered by Llama 3.1 via Cloudflare Workers AI</p>", unsafe_allow_html=True)
