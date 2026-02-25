import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="ODPC Kenya Checker",
    layout="wide"
)

# ---------------------------------------------------
# SCRAPER FUNCTION
# ---------------------------------------------------
@st.cache_data(ttl=3600)  # Cache for 1 hour
def scrape_odpc_data():
    url = "https://www.odpc.go.ke/registered-data-handlers/"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")

        if table is None:
            return pd.DataFrame()

        headers = [th.text.strip() for th in table.find_all("th")]
        rows = []

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            if len(cells) != len(headers):
                continue

            row = {headers[i]: cells[i].text.strip() for i in range(len(headers))}
            rows.append(row)

        return pd.DataFrame(rows)

    except Exception as e:
        st.error(f"Scraping error: {e}")
        return pd.DataFrame()


# ---------------------------------------------------
# MAIN APP
# ---------------------------------------------------
def main():
    st.title("📊 ODPC Kenya Data Handler Status Checker")

    case_option = st.radio(
        "Normalize Provider Names To:",
        ["Lowercase", "Uppercase"]
    )

    uploaded_file = st.file_uploader(
        "📁 Upload Excel File (Must contain column: Provider Name)",
        type=["xlsx"]
    )

    if uploaded_file is None:
        st.info("Please upload an Excel file to begin.")
        return

    # -----------------------------
    # READ EXCEL SAFELY
    # -----------------------------
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return

    # Clean column names
    df.columns = df.columns.str.strip()

    if "Provider Name" not in df.columns:
        st.error("❌ Excel must contain a column named exactly: 'Provider Name'")
        st.write("Columns found:", df.columns.tolist())
        return

    # Normalize user data
    if case_option == "Lowercase":
        df["provider_normalized"] = (
            df["Provider Name"].astype(str).str.strip().str.lower()
        )
    else:
        df["provider_normalized"] = (
            df["Provider Name"].astype(str).str.strip().str.upper()
        )

    # -----------------------------
    # SCRAPE ODPC
    # -----------------------------
    with st.spinner("🔍 Fetching ODPC data..."):
        odpc_df = scrape_odpc_data()

    if odpc_df.empty:
        st.error("⚠️ Could not retrieve ODPC data.")
        return

    # Clean ODPC columns
    odpc_df.columns = odpc_df.columns.str.strip()

    if "NAME" not in odpc_df.columns:
        st.error("ODPC website structure changed. 'NAME' column not found.")
        st.write("Available ODPC columns:", odpc_df.columns.tolist())
        return

    # Normalize ODPC data
    if case_option == "Lowercase":
        odpc_df["odpc_normalized"] = (
            odpc_df["NAME"].astype(str).str.strip().str.lower()
        )
    else:
        odpc_df["odpc_normalized"] = (
            odpc_df["NAME"].astype(str).str.strip().str.upper()
        )

    # -----------------------------
    # MERGE
    # -----------------------------
    merged_df = pd.merge(
        df,
        odpc_df,
        left_on="provider_normalized",
        right_on="odpc_normalized",
        how="left"
    )

    # Add matched column safely
    merged_df["Matched Name"] = merged_df.get("NAME", None)

    # Columns to show (safe selection)
    desired_columns = [
        "Provider Name",
        "Matched Name",
        "TYPE",
        "CURRENT STATE",
        "REGISTRATION NUMBER",
        "COUNTY",
        "COUNTRY",
    ]

    available_columns = [
        col for col in desired_columns if col in merged_df.columns
    ]

    result_df = merged_df[available_columns]

    # -----------------------------
    # DISPLAY RESULTS
    # -----------------------------
    st.success("✅ Matching Complete")
    st.dataframe(result_df, use_container_width=True)

    # -----------------------------
    # DOWNLOAD BUTTON
    # -----------------------------
    output = BytesIO()
    result_df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        label="📥 Download Results as Excel",
        data=output,
        file_name="odpc_provider_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.caption(
        "ℹ️ Matching is exact but case-insensitive based on your selection."
    )


# ---------------------------------------------------
if __name__ == "__main__":
    main()
