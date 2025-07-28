import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64 
import gspread
from gspread_dataframe import get_as_dataframe
import json
from google.oauth2 import service_account



# Read credentials from Streamlit secrets
creds_dict = st.secrets["gcp_service_account"]
creds = service_account.Credentials.from_service_account_info(creds_dict)
gc = gspread.authorize(creds)
sheet_id = "1YgTNeWitn8D1SjvF-wOUa-EJSR9fDQgxGn8O445WVHU"
sh = gc.open_by_key(sheet_id)
worksheet = sh.get_worksheet(0)
df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")


# --- Drop sensitive info ---
# --- Clean and Drop Sensitive Info ---
df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")

# Drop all columns that match sensitive labels (case-insensitive, space-tolerant)
sensitive_cols = ['timestamp', 'pin code', 'taluka', 'village', 'area']
df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
df_clean = df.drop(columns=[col for col in df.columns if col.strip().lower() in sensitive_cols])


# Remove 'village' column if it exists
if "village" in df_clean.columns:
    df_clean = df_clean.drop(columns=["village"])

# Then display in Streamlit



# --- Page Setup ---
st.set_page_config(page_title="Individual Health Report", layout="centered")
st.title("\U0001F3E5 Individual Health & Hygiene Analysis")

# --- Email Input ---
email = st.text_input("Enter your email used in the form")
submit = st.button("Submit") or email  # allows Enter key to submit

if submit:
    df_clean["Email address"] = df_clean["Email address"].astype(str)
    person_row = df[df["Email address"].astype(str).str.lower() == email.lower()]


    if person_row.empty:
        st.warning("No response found for this email.")
    else:
        person_data = person_row.copy()
        person_data.columns = person_data.columns.str.strip()  # Normalize
        person_data = person_data.drop(columns=[col for col in person_data.columns if col.strip().lower() in sensitive_cols]).iloc[-1]



        # --- Hygiene Score Calculation ---
        def calculate_health_score(data):
            score = 100

            def check_answer(question, deduction_map):
                ans = str(data.get(question, '')).lower()
                for key, val in deduction_map.items():
                    if key in ans:
                        return val
                return 0

            deductions = [
                check_answer("What kind of waste disposal is used?", {"open": 15, "no disposal": 20}),
                20 if 'yes' in str(data.get("Is the water contaminated?", "")).lower() else 0,
                check_answer("Do you see rats, flies, or other pests nearby?", {"often": 15, "sometimes": 10, "rarely": 5}),
                check_answer("How is the air quality in your area?", {
                    "severely polluted": 25, "moderately polluted": 15, "mildly polluted": 5
                }),
                check_answer("Are public toilets clean?", {
                    "sometimes dirty": 10, "mostly unclean": 15, "no toilets": 20
                }),
                check_answer("Drinking water source", {
                    "tap": 20, "well": 15, "river": 25, "tank": 20
                }),
            ]

            chronic = str(data.get("Do you have any chronic illness?", "") or "").strip().lower()
            if chronic and chronic not in ["none", "none of the above", "no", "nan"]:
                deductions.append(10)

            symptoms = str(data.get("Have you had any of these symptoms in the last month?", "")).lower()
            if symptoms and "none" not in symptoms:
                deductions.append(10)

            toilet = str(data.get("What kind of toilet facility do you use?", "")).lower()
            if "open" in toilet:
                deductions.append(20)
            elif "shared" in toilet:
                deductions.append(10)

            final_score = score - sum(deductions)
            return max(final_score, 0)

        # --- Disease Prediction & Suggestions ---
        def predict_disease(data):
            diseases = []
            suggestions = []

            water_source = str(data.get("Drinking water source", "")).lower()
            if any(x in water_source for x in ['tap']):
                diseases.append("Cholera / Typhoid")
                suggestions.append("Use clean, filtered, or boiled water.")

            toilet = str(data.get("What kind of toilet facility do you use?", "")).lower()
            if "open" in toilet:
                diseases.append("Diarrhea / Dysentery")
                suggestions.append("Avoid open defecation and improve sanitation.")
            elif "shared" in toilet:
                diseases.append("Shared toilet hygiene risk")
                suggestions.append("Clean shared toilets frequently and maintain personal hygiene.")

            if 'yes' in str(data.get("Is there open sewage near your home?", "")).lower():
                diseases.append("Vector-borne Diseases (Dengue/Malaria)")
                suggestions.append("Eliminate stagnant water and clean surroundings.")

            if 'no' in str(data.get("Are public toilets clean?", "")).lower():
                diseases.append("Respiratory / Bacterial Infections")
                suggestions.append("Avoid using dirty toilets and wear masks.")

            chronic = str(data.get("Do you have any chronic illness?", "") or "").strip().lower()
            if chronic and chronic not in ["none", "none of the above", "no", "nan"]:
                diseases.append("Complications due to Chronic Illness")
                suggestions.append("Consult doctor regularly.")

            if not diseases:
                diseases.append("No major risks detected")
                suggestions.append("Maintain your good hygiene habits.")

            return diseases, suggestions

        # --- PDF Generator ---
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 16)
                self.set_fill_color(200, 220, 255)
                self.cell(0, 10, 'Aarogya Darpan - Health Report', ln=True, align='C')
                self.ln(5)

            def footer(self):
                self.set_y(-12)
                self.set_font('Arial', 'I', 10)
                self.set_text_color(100, 100, 100)
                self.cell(0, 10, 'Generated by Aarogya Darpan', align='C')

            def section(self, title, content):
                self.set_font('Arial', 'B', 13)
                self.set_fill_color(230, 230, 230)
                self.cell(0, 10, title, ln=True, fill=True)
                self.set_font('Arial', '', 12)
                self.multi_cell(0, 10, content)
                self.ln(3)

        # --- Output Display ---
        score = calculate_health_score(person_data)
        diseases, suggestions = predict_disease(person_data)

        st.subheader("Hygiene Score")
        st.progress(score / 100)
        st.markdown(f"<h2 style='color:green;'>{score} / 100</h2>", unsafe_allow_html=True)

        st.subheader("Predicted Disease(s)")
        for dis in diseases:
            st.write(f"- {dis}")

        st.subheader("Suggestions")
        for tip in suggestions:
            st.write(f"- {tip}")

        # --- Table View ---
        st.subheader("Your Responses")
        person_dict = person_data.to_dict()
        response_df = pd.DataFrame(list(person_dict.items()), columns=["Question", "Your Answer"])

        st.markdown("""
        <style>
        .scroll-table-wrapper {
            overflow-x: auto;
            width: 100%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="scroll-table-wrapper">' + response_df.to_html(index=False) + '</div>', unsafe_allow_html=True)

        # --- PDF Button ---
        pdf = PDF()
        pdf.add_page()
        pdf.section("Email", email)
        if "Name" in person_data:
            pdf.section("Name", person_data["Name"])
        if "Gender" in person_data:
            pdf.section("Gender", person_data["Gender"])
        pdf.section("Hygiene Score", f"{score}/100")
        pdf.section("Disease Predictions", "\n".join(diseases))
        pdf.section("Suggestions", "\n".join(suggestions))

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="Health_Report.pdf">Download PDF Report</a>'
        st.markdown(href, unsafe_allow_html=True)

