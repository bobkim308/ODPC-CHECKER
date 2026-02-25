import streamlit as st
import pandas as pd
from io import BytesIO
import requests
from bs4 import BeautifulSoup

# 🔍 Scraper function with error handling
def scrape_odpc_data():
    url = "https://www.odpc.go.ke/registered-data-handlers/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table")

        if table is None:
            raise ValueError("Could not find data table on the page.")

        headers = [th.text.strip() for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header
            cells = tr.find_all("td")
            if len(cells) != len(headers):
                continue  # skip malformed rows
            row = {headers[i]: cells[i].text.strip() for i in range(len(headers))}
            rows.append(row)

        if not rows:
            raise ValueError("No data found in the table.")

        return rows

    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return []
    except Exception as e:
        st.error(f"Scraper error: {e}")
        return []

# 🚀 Main Streamlit App
def main():
    st.set_page_config(page_title="ODPC Kenya Checker", layout="wide")
    st.title("📊 ODPC Kenya Data Handler Status Checker")

    # Let user pick case normalization style
    case_option = st.radio("Change uploaded provider names to:", ("Lowercase", "Uppercase"))

    uploaded_file = st.file_uploader("📁 Upload Excel with 'Provider Name' column", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)

        if 'Provider Name' not in df.columns:
            st.error("❌ Excel must contain a 'Provider Name' column.")
            return

        # Normalize based on user selection
        if case_option == "Lowercase":
            df['Provider Name Normalized'] = df['Provider Name'].astype(str).str.strip().str.lower()
        else:
            df['Provider Name Normalized'] = df['Provider Name'].astype(str).str.strip().str.upper()

        with st.spinner("🔍 Scraping ODPC website..."):
            odpc_data = scrape_odpc_data()

        if not odpc_data:
            st.error("⚠️ Could not retrieve ODPC data.")
            return

        odpc_df = pd.DataFrame(odpc_data)

        # Normalize ODPC names to match user selection
        if case_option == "Lowercase":
            odpc_df['NAME Normalized'] = odpc_df['NAME'].astype(str).str.strip().str.lower()
        else:
            odpc_df['NAME Normalized'] = odpc_df['NAME'].astype(str).str.strip().str.upper()

        # Perform merge
        merged_df = pd.merge(
            df,
            odpc_df,
            left_on='Provider Name Normalized',
            right_on='NAME Normalized',
            how='left'
        )

        # Add "Matched Name" column
        merged_df['Matched Name'] = merged_df['NAME']

        # Clean up columns for display
        columns_to_show = ['Provider Name', 'Matched Name', 'TYPE', 'CURRENT STATE', 'REGISTRATION NUMBER', 'COUNTY', 'COUNTRY']
        result_df = merged_df[columns_to_show]

        st.success("✅ Matching complete!")
        st.dataframe(result_df)

        # 💾 Download button
        towrite = BytesIO()
        result_df.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)

        st.download_button(
            label="📥 Download Results as Excel",
            data=towrite,
            file_name="odpc_provider_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.caption("ℹ️ The tool checks names exactly, but ignores case depending on your selection above.")

if __name__ == "__main__":
    main()
pip install streamlit
streamlit run odpc_checker.py

