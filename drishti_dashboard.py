import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DRISHTI Supervisor Dashboard",
    page_icon="🔴",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0F172A; }
    .metric-card {
        background: #1E293B;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border-left: 4px solid;
    }
    .red-card   { border-color: #EF4444; }
    .amber-card { border-color: #F59E0B; }
    .green-card { border-color: #10B981; }
    .blue-card  { border-color: #3B82F6; }
</style>
""", unsafe_allow_html=True)

# ── Connect to Google Sheets ──────────────────────────────────────────────────
@st.cache_resource
def connect_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=60)
def load_data():
    client = connect_sheets()
    sheet = client.open_by_key("1Km1v-b_MLlXCnesSldXUO7XxB41Uyi8EHZpkeM4pUNM")
    
    # Load Beneficiary Register
    register = sheet.worksheet("Beneficiary Register")
    reg_data = pd.DataFrame(register.get_all_records())
    
    # Load Alert Log
    alert_log = sheet.worksheet("DRISHTI Alert Log")
    alert_data = pd.DataFrame(alert_log.get_all_records())
    
    return reg_data, alert_data

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    reg_df, alert_df = load_data()
    connected = True
except Exception as e:
    st.error(f"Connection error: {e}")
    connected = False

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3,1])
with col1:
    st.markdown("# 🔴 DRISHTI")
    st.markdown("### Dropout Recognition and Intelligent System for Health Tracking Interventions")
    st.markdown("**Immunisation Surveillance Dashboard — Odisha Pilot**")
with col2:
    st.markdown(f"**Last refreshed:** {datetime.now().strftime('%d %b %Y %H:%M')}")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

st.divider()

if connected and len(alert_df) > 0:

    # ── Clean data ────────────────────────────────────────────────────────────
    alert_df["Days Overdue"] = pd.to_numeric(alert_df["Days Overdue"], errors="coerce").fillna(0)
    
    # ── KPI Cards ─────────────────────────────────────────────────────────────
    total_alerts    = len(alert_df)
    pending         = len(alert_df[alert_df["Alert Status"] == "Pending"])
    resolved        = len(alert_df[alert_df["Alert Status"] == "Resolved"])
    escalated       = len(alert_df[alert_df["Alert Status"] == "Escalated"])
    resolution_rate = round((resolved / total_alerts * 100), 1) if total_alerts > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""<div class="metric-card red-card">
            <h1 style="color:#EF4444;margin:0">{total_alerts}</h1>
            <p style="color:#94A3B8;margin:0">Total Alerts Sent</p>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div class="metric-card amber-card">
            <h1 style="color:#F59E0B;margin:0">{pending}</h1>
            <p style="color:#94A3B8;margin:0">Pending</p>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""<div class="metric-card green-card">
            <h1 style="color:#10B981;margin:0">{resolved}</h1>
            <p style="color:#94A3B8;margin:0">Resolved</p>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""<div class="metric-card red-card">
            <h1 style="color:#EF4444;margin:0">{escalated}</h1>
            <p style="color:#94A3B8;margin:0">Escalated</p>
        </div>""", unsafe_allow_html=True)

    with c5:
        st.markdown(f"""<div class="metric-card blue-card">
            <h1 style="color:#3B82F6;margin:0">{resolution_rate}%</h1>
            <p style="color:#94A3B8;margin:0">Resolution Rate</p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Alerts by Village")
        village_counts = alert_df.groupby("Village").size().reset_index(name="Alerts")
        fig1 = px.bar(
            village_counts, x="Village", y="Alerts",
            color="Alerts",
            color_continuous_scale="Reds",
            template="plotly_dark"
        )
        fig1.update_layout(
            plot_bgcolor="#1E293B",
            paper_bgcolor="#1E293B",
            showlegend=False
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        st.markdown("#### Alert Status Breakdown")
        status_counts = alert_df["Alert Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        colors = {"Pending":"#F59E0B", "Resolved":"#10B981", "Escalated":"#EF4444"}
        fig2 = px.pie(
            status_counts, values="Count", names="Status",
            color="Status",
            color_discrete_map=colors,
            template="plotly_dark",
            hole=0.4
        )
        fig2.update_layout(
            plot_bgcolor="#1E293B",
            paper_bgcolor="#1E293B"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Alerts by ASHA ────────────────────────────────────────────────────────
    st.markdown("#### Workload by ASHA")
    asha_summary = alert_df.groupby("ASHA Name").agg(
        Total_Alerts   = ("Alert Status", "count"),
        Pending        = ("Alert Status", lambda x: (x=="Pending").sum()),
        Resolved       = ("Alert Status", lambda x: (x=="Resolved").sum()),
        Escalated      = ("Alert Status", lambda x: (x=="Escalated").sum()),
        Avg_Days_Overdue = ("Days Overdue", "mean")
    ).reset_index()
    asha_summary["Avg_Days_Overdue"] = asha_summary["Avg_Days_Overdue"].round(1)
    asha_summary.columns = ["ASHA Name","Total Alerts","Pending","Resolved","Escalated","Avg Days Overdue"]

    st.dataframe(
        asha_summary,
        use_container_width=True,
        hide_index=True
    )

    # ── Vaccine breakdown ─────────────────────────────────────────────────────
    st.markdown("#### Most Missed Vaccines")
    vax_counts = alert_df["Vaccine Overdue"].value_counts().reset_index()
    vax_counts.columns = ["Vaccine", "Count"]
    fig3 = px.bar(
        vax_counts, x="Vaccine", y="Count",
        color="Count",
        color_continuous_scale="Oranges",
        template="plotly_dark"
    )
    fig3.update_layout(
        plot_bgcolor="#1E293B",
        paper_bgcolor="#1E293B",
        showlegend=False
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Full Alert Log table ──────────────────────────────────────────────────
    st.markdown("#### Full Alert Log")
    
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Pending", "Resolved", "Escalated"]
    )
    
    if status_filter != "All":
        filtered_df = alert_df[alert_df["Alert Status"] == status_filter]
    else:
        filtered_df = alert_df

    def highlight_status(val):
        if val == "Pending":   return "background-color: #78350F; color: #FDE68A"
        if val == "Resolved":  return "background-color: #064E3B; color: #A7F3D0"
        if val == "Escalated": return "background-color: #7F1D1D; color: #FECACA"
        return ""

    st.dataframe(
        filtered_df.style.map(highlight_status, subset=["Alert Status"]),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No alert data found. Run your n8n workflow first to generate alerts.")
    st.markdown("### Sample view of what the dashboard will show:")
    st.image("https://via.placeholder.com/800x400?text=DRISHTI+Dashboard+Preview")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center;color:#475569'>DRISHTI — PATH India Pilot | Odisha | Powered by n8n + Streamlit</p>",
    unsafe_allow_html=True
)