import streamlit as st
import requests
import json
import re

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cold Email Writer",
    page_icon="✉️",
    layout="centered",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { max-width: 700px; padding-top: 2rem; }
    .stTextInput > label, .stSelectbox > label { font-size: 0.85rem; color: #888; }
    .email-box {
        background: #f8f8f8;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        font-size: 0.95rem;
        line-height: 1.8;
        white-space: pre-wrap;
        margin-top: 0.5rem;
    }
    .subject-box {
        background: #f0f0f0;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ✉️ Cold Email Writer")
st.markdown("*AI-powered personalized cold emails in seconds*")
st.divider()

# ── Credentials ───────────────────────────────────────────────────────────────
st.markdown("#### Cloudflare Workers AI credentials")
st.markdown("Get these free at [cloudflare.com](https://cloudflare.com) — no credit card needed.")

account_id = st.text_input(
    "Cloudflare Account ID",
    placeholder="Found on your Cloudflare dashboard homepage (right side)",
)
api_token = st.text_input(
    "Cloudflare API Token",
    type="password",
    placeholder="My Profile → API Tokens → Create Token → Workers AI Read",
)

st.divider()

# ── Inputs ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    biz_name = st.text_input("Your business name", placeholder="e.g. NexBot AI")
with col2:
    product = st.text_input("Your product / service", placeholder="e.g. AI chatbot for restaurants")

target = st.text_input("Who are you emailing?", placeholder="e.g. local pizza shops in Chicago")
benefit = st.text_input("Key benefit you offer", placeholder="e.g. saves 5 hours/week on customer questions")

col3, col4 = st.columns(2)
with col3:
    tone = st.selectbox("Tone", [
        "Friendly and professional",
        "Direct and punchy",
        "Formal",
        "Casual and conversational",
    ])
with col4:
    cta = st.selectbox("Call to action", [
        "Book a free 15-minute call",
        "Reply to this email to learn more",
        "Try it free for 7 days",
        "Visit our website",
    ])

# ── Generate ──────────────────────────────────────────────────────────────────
if st.button("✨ Generate cold email", use_container_width=True, type="primary"):
    if not account_id or not api_token:
        st.error("Please enter your Cloudflare Account ID and API Token above.")
    elif not biz_name or not product or not target:
        st.error("Please fill in: business name, product, and target customer.")
    else:
        with st.spinner("Writing your email..."):
            try:
                prompt = f"""You are an expert cold email copywriter. Write a cold email for:

Business name: {biz_name}
Product/service: {product}
Target customer: {target}
Key benefit: {benefit if benefit else 'not specified'}
Tone: {tone}
Call to action: {cta}

Return ONLY raw JSON, no markdown, no backticks, no explanation. Format:
{{"subject":"subject line here","body":"email body here with \\n for line breaks"}}

Rules:
- Subject: under 50 chars, curiosity-driven, no spam words
- Body: 80-120 words, personalized, one value prop, soft CTA
- No 'I hope this finds you well' openers
- Sound human, not robotic"""

                url = f"https://api.cloudflare.com/client/v4/accounts/{account_id.strip()}/ai/run/@cf/meta/llama-3.1-8b-instruct"

                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_token.strip()}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [
                            {"role": "system", "content": "You are an expert cold email copywriter. Always respond with only raw JSON, no markdown, no backticks."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 1024
                    },
                    timeout=30
                )

                if response.status_code == 401:
                    st.error("Invalid API token. Check it at cloudflare.com → My Profile → API Tokens.")
                elif response.status_code == 403:
                    st.error("Token doesn't have Workers AI permission. Create a new token using the 'Workers AI Read' template.")
                elif response.status_code != 200:
                    st.error(f"API error {response.status_code}: {response.text}")
                else:
                    result = response.json()
                    raw = result.get("result", {}).get("response", "")
                    match = re.search(r'\{[\s\S]*\}', raw)
                    if not match:
                        st.error("Couldn't parse the response. Try again.")
                    else:
                        data = json.loads(match.group())
                        subject = data.get("subject", "")
                        body = data.get("body", "")

                        st.divider()
                        st.markdown("#### Generated email")
                        st.markdown(f'<div class="subject-box"><strong>Subject:</strong> {subject}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="email-box">{body}</div>', unsafe_allow_html=True)

                        words = len(body.split())
                        st.divider()
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Word count", words)
                        c2.metric("Reading level", "Grade 6–8" if words < 100 else "Grade 8–10")
                        c3.metric("Est. reply rate", "4–7%")

                        full_email = f"Subject: {subject}\n\n{body}"
                        st.download_button(
                            "⬇️ Download email as .txt",
                            data=full_email,
                            file_name="cold_email.txt",
                            mime="text/plain",
                            use_container_width=True,
                        )

            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p style='text-align:center; color:#aaa; font-size:0.8rem;'>Built with Llama 3.1 via Cloudflare Workers AI · free tier</p>", unsafe_allow_html=True)
