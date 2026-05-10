import streamlit as st
import requests
import json
import re
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cold Email Writer Pro",
    page_icon="✉️",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
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
    .score-box {
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .history-item {
        background: #f8f8f8;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.85rem;
        cursor: pointer;
    }
    div[data-testid="stHorizontalBlock"] { align-items: flex-start; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "current_email" not in st.session_state:
    st.session_state.current_email = None
if "current_subject" not in st.session_state:
    st.session_state.current_subject = None
if "variation_b" not in st.session_state:
    st.session_state.variation_b = None
if "subject_b" not in st.session_state:
    st.session_state.subject_b = None
if "followup" not in st.session_state:
    st.session_state.followup = None
if "score_data" not in st.session_state:
    st.session_state.score_data = None

# ── Load credentials ──────────────────────────────────────────────────────────
try:
    account_id = st.secrets["CF_ACCOUNT_ID"]
    api_token = st.secrets["CF_API_TOKEN"]
except Exception:
    st.error("⚠️ Server configuration error. Please contact support.")
    st.stop()

# ── AI call helper ────────────────────────────────────────────────────────────
def call_ai(prompt, system="You are a helpful assistant. Respond only with raw JSON."):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2048
        },
        timeout=45
    )
    if r.status_code != 200:
        raise Exception(f"API error {r.status_code}")
    return r.json().get("result", {}).get("response", "")

def extract_json(raw):
    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        raise Exception("No JSON found in response")
    return json.loads(match.group())

def score_email(subject, body):
    prompt = f"""Score this cold email and return ONLY raw JSON:
Subject: {subject}
Body: {body}

Return exactly:
{{"overall": 85, "subject_score": 80, "body_score": 85, "cta_score": 90, "tips": ["tip 1", "tip 2", "tip 3"]}}
Scores are 0-100. Tips are specific improvements."""
    raw = call_ai(prompt)
    return extract_json(raw)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ✉️ Cold Email Writer Pro")
st.markdown("*Generate, refine, score, and perfect your cold emails with AI*")
st.divider()

# ── Layout: left inputs, right output ────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("### ⚙️ Email settings")

    with st.expander("📋 Business details", expanded=True):
        biz_name = st.text_input("Business name", placeholder="e.g. NexBot AI")
        product = st.text_input("Product / service", placeholder="e.g. AI chatbot for restaurants")
        target = st.text_input("Target customer", placeholder="e.g. local pizza shops in Chicago")
        benefit = st.text_input("Key benefit", placeholder="e.g. saves 5 hours/week")
        sender_name = st.text_input("Your name (optional)", placeholder="e.g. Alex")

    with st.expander("🎨 Tone & style", expanded=True):
        tone = st.select_slider("Tone", options=[
            "Very casual", "Casual", "Friendly & professional",
            "Professional", "Formal", "Very formal"
        ], value="Friendly & professional")
        energy = st.select_slider("Energy", options=[
            "Very soft", "Soft", "Balanced", "Direct", "Aggressive"
        ], value="Balanced")
        length = st.select_slider("Length", options=[
            "Very short (50w)", "Short (80w)", "Medium (120w)", "Long (160w)"
        ], value="Short (80w)")
        humor = st.checkbox("Add a touch of humor 😄")
        emoji_mode = st.checkbox("Include emojis")
        ps_line = st.checkbox("Add a P.S. line")

    with st.expander("📣 Call to action"):
        cta = st.selectbox("Primary CTA", [
            "Book a free 15-minute call",
            "Reply to this email to learn more",
            "Try it free for 7 days",
            "Visit our website",
            "Schedule a quick demo",
            "Claim a free audit",
        ])
        urgency = st.checkbox("Add urgency (limited time / spots)")

    with st.expander("🌍 Language & audience"):
        language = st.selectbox("Language", [
            "English", "Spanish", "French", "German",
            "Portuguese", "Italian", "Dutch", "Japanese"
        ])
        industry = st.selectbox("Target industry (optional)", [
            "Any", "Restaurant / Food", "Real estate", "E-commerce",
            "Healthcare", "Legal", "Marketing agency", "SaaS / Tech",
            "Retail", "Fitness / Wellness", "Education", "Finance"
        ])

    with st.expander("🔧 Advanced"):
        ab_test = st.checkbox("Generate A/B variation")
        gen_followup = st.checkbox("Also generate a follow-up email")
        auto_score = st.checkbox("Auto-score the email", value=True)
        subject_variations = st.checkbox("Generate 3 subject line options")

    generate = st.button("✨ Generate email", use_container_width=True, type="primary")

# ── Right column: output ──────────────────────────────────────────────────────
with right:
    st.markdown("### 📨 Your email")

    if generate:
        if not biz_name or not product or not target:
            st.error("Please fill in: business name, product, and target customer.")
        else:
            length_map = {
                "Very short (50w)": "50 words max",
                "Short (80w)": "80 words max",
                "Medium (120w)": "120 words max",
                "Long (160w)": "160 words max",
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

Return ONLY raw JSON, no markdown:
{{"subject":"subject here","body":"body here with \\n for line breaks"}}

Rules:
- Subject: under 50 chars, no spam words
- No 'I hope this finds you well'
- Sound human, not robotic
- Respect the word limit strictly"""

            with st.spinner("Generating your email..."):
                try:
                    raw = call_ai(base_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                    data = extract_json(raw)
                    st.session_state.current_subject = data.get("subject", "")
                    st.session_state.current_email = data.get("body", "")
                    st.session_state.variation_b = None
                    st.session_state.subject_b = None
                    st.session_state.followup = None
                    st.session_state.score_data = None
                except Exception as e:
                    st.error(f"Generation failed: {e}")

            # A/B variation
            if ab_test and st.session_state.current_email:
                with st.spinner("Generating A/B variation..."):
                    try:
                        ab_prompt = base_prompt.replace(
                            "Return ONLY raw JSON",
                            "Write a DIFFERENT version with a different angle and opening. Return ONLY raw JSON"
                        )
                        raw_b = call_ai(ab_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                        data_b = extract_json(raw_b)
                        st.session_state.variation_b = data_b.get("body", "")
                        st.session_state.subject_b = data_b.get("subject", "")
                    except:
                        pass

            # Follow-up
            if gen_followup and st.session_state.current_email:
                with st.spinner("Generating follow-up email..."):
                    try:
                        fu_prompt = f"""Write a short follow-up email for someone who didn't reply to this cold email:
Original email: {st.session_state.current_email}
Business: {biz_name}, Product: {product}, Target: {target}
Keep it under 60 words, friendly, reference the original email briefly.
Return ONLY raw JSON: {{"subject":"Re: subject here","body":"followup body here"}}"""
                        raw_fu = call_ai(fu_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                        fu_data = extract_json(raw_fu)
                        st.session_state.followup = fu_data.get("body", "")
                    except:
                        pass

            # Subject variations
            if subject_variations and st.session_state.current_email:
                with st.spinner("Generating subject line variations..."):
                    try:
                        sv_prompt = f"""Generate 3 different subject lines for this cold email:
{st.session_state.current_email}
Business: {biz_name}, Product: {product}
Return ONLY raw JSON: {{"subjects": ["subject 1", "subject 2", "subject 3"]}}"""
                        raw_sv = call_ai(sv_prompt, "Return only raw JSON.")
                        sv_data = extract_json(raw_sv)
                        st.session_state.subject_variations = sv_data.get("subjects", [])
                    except:
                        st.session_state.subject_variations = []

            # Auto score
            if auto_score and st.session_state.current_email:
                with st.spinner("Scoring your email..."):
                    try:
                        st.session_state.score_data = score_email(
                            st.session_state.current_subject,
                            st.session_state.current_email
                        )
                    except:
                        pass

            # Save to history
            if st.session_state.current_email:
                st.session_state.history.insert(0, {
                    "time": datetime.now().strftime("%H:%M"),
                    "subject": st.session_state.current_subject,
                    "body": st.session_state.current_email,
                    "biz": biz_name,
                })
                if len(st.session_state.history) > 20:
                    st.session_state.history = st.session_state.history[:20]

    # ── Display email ─────────────────────────────────────────────────────────
    if st.session_state.current_email:
        tabs = ["📧 Version A"]
        if st.session_state.variation_b:
            tabs.append("📧 Version B")
        if st.session_state.followup:
            tabs.append("📨 Follow-up")

        tab_objects = st.tabs(tabs)

        def show_email(tab, subject, body, label="A"):
            with tab:
                st.markdown(f'<div class="subject-box"><strong>Subject:</strong> {subject}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="email-box">{body}</div>', unsafe_allow_html=True)

                words = len(body.split())
                c1, c2 = st.columns(2)
                c1.metric("Words", words)
                c2.metric("Est. reply rate", "4–7%")

                # Tone adjustment buttons
                st.markdown("**Refine this email:**")
                bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
                adjustments = {
                    "😄 Funnier": "more fun and humorous",
                    "😐 Serious": "more serious and formal",
                    "✂️ Shorter": "shorter, cut to 60 words max",
                    "📝 Longer": "longer with more detail",
                    "💪 Bolder": "more bold and aggressive",
                    "🕊️ Softer": "softer and more gentle",
                }
                buttons = [bc1, bc2, bc3, bc4, bc5, bc6]
                for i, (btn_label, instruction) in enumerate(adjustments.items()):
                    if buttons[i].button(btn_label, key=f"adj_{label}_{i}"):
                        with st.spinner(f"Making it {instruction}..."):
                            try:
                                refine_prompt = f"""Rewrite this cold email to be {instruction}. Keep the same core message and CTA.
Subject: {subject}
Body: {body}
Return ONLY raw JSON: {{"subject":"new subject","body":"new body"}}"""
                                raw_r = call_ai(refine_prompt, "You are an expert cold email copywriter. Return only raw JSON.")
                                refined = extract_json(raw_r)
                                if label == "A":
                                    st.session_state.current_subject = refined.get("subject", subject)
                                    st.session_state.current_email = refined.get("body", body)
                                else:
                                    st.session_state.subject_b = refined.get("subject", subject)
                                    st.session_state.variation_b = refined.get("body", body)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Refinement failed: {e}")

                full_email = f"Subject: {subject}\n\n{body}"
                dl1, dl2 = st.columns(2)
                dl1.download_button(
                    "⬇️ Download .txt",
                    data=full_email,
                    file_name=f"cold_email_{label}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"dl_{label}"
                )
                dl2.download_button(
                    "⬇️ Download .md",
                    data=f"# Cold Email\n\n**Subject:** {subject}\n\n---\n\n{body}",
                    file_name=f"cold_email_{label}.md",
                    mime="text/markdown",
                    use_container_width=True,
                    key=f"dlmd_{label}"
                )

        show_email(tab_objects[0], st.session_state.current_subject, st.session_state.current_email, "A")
        if st.session_state.variation_b and len(tab_objects) > 1:
            show_email(tab_objects[1], st.session_state.subject_b, st.session_state.variation_b, "B")
        if st.session_state.followup:
            with tab_objects[-1]:
                st.markdown(f'<div class="email-box">{st.session_state.followup}</div>', unsafe_allow_html=True)
                st.download_button("⬇️ Download follow-up", data=st.session_state.followup, file_name="followup.txt", mime="text/plain")

        # Subject line variations
        if subject_variations and hasattr(st.session_state, "subject_variations") and st.session_state.subject_variations:
            st.divider()
            st.markdown("**📌 Subject line options:**")
            for i, subj in enumerate(st.session_state.subject_variations, 1):
                st.markdown(f"`{i}.` {subj}")

        # Score
        if st.session_state.score_data:
            st.divider()
            st.markdown("**📊 Email score:**")
            sd = st.session_state.score_data
            overall = sd.get("overall", 0)
            color = "#2ecc71" if overall >= 75 else "#f39c12" if overall >= 50 else "#e74c3c"
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Overall", f"{overall}/100")
            sc2.metric("Subject", f"{sd.get('subject_score', 0)}/100")
            sc3.metric("Body", f"{sd.get('body_score', 0)}/100")
            sc4.metric("CTA", f"{sd.get('cta_score', 0)}/100")
            if sd.get("tips"):
                st.markdown("**💡 Tips to improve:**")
                for tip in sd["tips"]:
                    st.markdown(f"- {tip}")

    else:
        st.info("Fill in the settings on the left and click **Generate email** to get started.")

# ── Email history ─────────────────────────────────────────────────────────────
if st.session_state.history:
    st.divider()
    st.markdown("### 🕓 Email history (this session)")
    for i, item in enumerate(st.session_state.history[:10]):
        with st.expander(f"{item['time']} — {item['biz']} — {item['subject']}"):
            st.markdown(f'<div class="email-box">{item["body"]}</div>', unsafe_allow_html=True)
            if st.button("Load this email", key=f"load_{i}"):
                st.session_state.current_subject = item["subject"]
                st.session_state.current_email = item["body"]
                st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p style='text-align:center; color:#aaa; font-size:0.8rem;'>Cold Email Writer Pro · Powered by Llama 3.1 via Cloudflare Workers AI</p>", unsafe_allow_html=True)
