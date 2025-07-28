import streamlit as st
import pandas as pd
import plotly.express as px

# --- Load Data ---
sheet_id = "1YgTNeWitn8D1SjvF-wOUa-EJSR9fDQgxGn8O445WVHU"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
df = pd.read_csv(sheet_url).dropna(how="all")


# Clean column names
df.columns = df.columns.str.strip()

# --- Remove only specific sensitive columns (but keep Age and Area)
exclude_keywords = ['timestamp', 'email', 'name', 'pin code', 'taluka', 'village']
df_clean = df[[col for col in df.columns if all(ex not in col.lower() for ex in exclude_keywords)]]

# --- Page Setup ---
st.set_page_config(page_title="Overall Analysis", layout="centered")
st.title("📊 Overall Hygiene Data Analysis")

col1, col2 = st.columns([6, 5])
with col2:
    with col2:
        st.markdown(f"""
        <div style='background-color:#e8f0fe; padding:10px 16px; border-radius:10px;
                    width: 180px; text-align:center; font-weight:600; color:#1967d2;
                    box-shadow: 1px 1px 6px rgba(0,0,0,0.1); font-size:16px;'>
            Total Responses: {len(df)}
        </div>
    """, unsafe_allow_html=True)



# --- Dropdown with valid questions including 'Age' and 'Area' ---
selected_questions = st.multiselect("Select one or more questions to analyze", df_clean.columns)

if not selected_questions:
    st.info("Please select at least one question.")
else:
    for selected_question in selected_questions:
        st.markdown(f"<h4 style='color:#68d4d0;'>Analysis for: <span style='font-weight:600;'>{selected_question}</span></h4>", unsafe_allow_html=True)

        # Handle checkbox/multi-answer questions
        if df_clean[selected_question].astype(str).str.contains(',').any():
            exploded = df_clean[selected_question].dropna().astype(str).str.split(',').explode().str.strip()
            counts = exploded.value_counts().reset_index()
            counts.columns = [selected_question, "Count"]
        else:
            counts = df_clean[selected_question].value_counts().reset_index()
            counts.columns = [selected_question, "Count"]

        # Pie Chart
        st.subheader("Pie Chart")
        fig_pie = px.pie(counts, names=selected_question, values="Count", hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)

        # Bar Chart
        st.subheader("Bar Chart")
        fig_bar = px.bar(
            counts,
            x=selected_question,
            y="Count",
            text="Count",
            title="Response Distribution"
        )
        fig_bar.update_traces(textposition='outside', textfont_size=14)
        fig_bar.update_layout(
            yaxis=dict(fixedrange=True),
            xaxis=dict(fixedrange=True),
            dragmode=False,
            margin=dict(t=30, b=60),
        )
        st.plotly_chart(fig_bar, use_container_width=True)


