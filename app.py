import pandas as pd
import streamlit as st
import requests
from pathlib import Path

# --------------------------
# Paths
# --------------------------
DATA_DIR = Path("data")
SUPPORT_FILE = DATA_DIR / "piggdekk_support.csv"
CONTACTS_FILE = DATA_DIR / "municipality_contacts.csv"


# --------------------------
# Flexible CSV reader
# --------------------------
def read_csv_flexible(path, required_cols=None):
    """
    Try multiple encodings and automatic separator detection.
    """
    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    last_error = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc, sep=None, engine="python")
            if required_cols:
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    raise KeyError(
                        f"Missing columns {missing} in file {path.name}. "
                        f"Current columns are: {list(df.columns)}"
                    )
            return df
        except (UnicodeDecodeError, KeyError) as e:
            last_error = e
            continue

    # If everything fails, show the last error
    raise last_error


# --------------------------
# Data loading functions
# --------------------------
@st.cache_data
def load_support_data():
    df = read_csv_flexible(
        SUPPORT_FILE,
        required_cols=[
            "municipality",
            "county",
            "has_support",
            "payment_per_tire",
            "max_tires",
            "max_total_nok",
            "period_start",
            "period_end",
            "lat",
            "lon",
            "info_url",
        ],
    )
    df["has_support"] = df["has_support"].astype(bool)
    return df


@st.cache_data
def load_contact_data():
    if not CONTACTS_FILE.exists():
        return pd.DataFrame(
            columns=["municipality", "service_name", "phone", "website"]
        )

    df = read_csv_flexible(
        CONTACTS_FILE,
        required_cols=["municipality", "service_name", "phone", "website"],
    )
    return df


@st.cache_data
def fetch_municipalities_from_api():
    url = "https://ws.geonorge.no/kommuneinfo/v1/kommuner"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.json_normalize(data)
        return df
    except Exception:
        return pd.DataFrame()


def build_merged_data():
    support_df = load_support_data()
    contacts_df = load_contact_data()

    # Merge on municipality name
    merged = support_df.merge(
        contacts_df,
        on="municipality",
        how="left",
        suffixes=("", "_contact"),
    )
    return merged


# --------------------------
# Streamlit app
# --------------------------
def main():
    st.set_page_config(
        page_title="Piggdekk Support Dashboard",
        page_icon="🛞",
        layout="wide",
    )

    # Try to load data and show a clear error if something is wrong
    try:
        df = build_merged_data()
    except Exception as e:
        st.error(
            "There was an error loading the CSV files.\n\n"
            f"Details: {e}\n\n"
            "Please check that:\n"
            "- 'piggdekk_support.csv' and 'municipality_contacts.csv' are in the 'data' folder\n"
            "- The first row in each file contains the column names.\n"
            "- The column 'municipality' exists and is spelled exactly like this."
        )
        st.stop()

    # Sidebar filters
    st.sidebar.title("Filters")

    counties = ["All"] + sorted(df["county"].dropna().unique().tolist())
    selected_county = st.sidebar.selectbox("County", counties)

    support_filter = st.sidebar.selectbox(
        "Support filter",
        ["All", "With support", "Without support"],
    )

    # Apply filters
    filtered_df = df.copy()

    if selected_county != "All":
        filtered_df = filtered_df[filtered_df["county"] == selected_county]

    if support_filter == "With support":
        filtered_df = filtered_df[filtered_df["has_support"] == True]
    elif support_filter == "Without support":
        filtered_df = filtered_df[filtered_df["has_support"] == False]

    # Title & intro
    st.title("🛞 Piggdekk Support Dashboard")

    st.markdown(
        """
        This dashboard shows Norwegian municipalities that offer **financial support**
        for switching from studded winter tires (*piggdekk*) to non-studded winter tires
        (*piggfrie vinterdekk*).
        """
    )

    # KPIs
    col1, col2, col3 = st.columns(3)

    col1.metric("Municipalities (view)", len(filtered_df))

    with_support_df = filtered_df[filtered_df["has_support"] == True]
    col2.metric("With support", len(with_support_df))

    valid_payments = with_support_df["payment_per_tire"].dropna()
    if not valid_payments.empty:
        max_support = int(valid_payments.max())
        col3.metric("Max NOK per tire", f"{max_support} NOK")
    else:
        col3.metric("Max NOK per tire", "-")

    st.divider()

    # Map
    st.subheader("📍 Map of municipalities with support")

    map_df = with_support_df[
        with_support_df["lat"].notna() & with_support_df["lon"].notna()
    ][["municipality", "lat", "lon"]]

    if not map_df.empty:
        st.map(map_df.rename(columns={"lat": "latitude", "lon": "longitude"}))
        st.caption("Map shows municipalities in the current filter that have support.")
    else:
        st.info("No supported municipalities in the current filter or missing coordinates.")

    st.divider()

    # Table
    st.subheader("📊 Municipal details")

    display_cols = [
        "municipality",
        "county",
        "has_support",
        "payment_per_tire",
        "max_tires",
        "max_total_nok",
        "period_start",
        "period_end",
        "service_name",
        "phone",
        "website",
        "info_url",
    ]

    for col in display_cols:
        if col not in filtered_df.columns:
            filtered_df[col] = ""

    st.dataframe(filtered_df[display_cols], use_container_width=True)

    st.markdown(
        """
        **Column notes**  
        - `has_support = True` → municipality currently has a piggdekk support scheme (according to your dataset).  
        - `payment_per_tire` → compensation per studded tire when switching to non-studded.  
        - `max_tires` & `max_total_nok` → upper limits per car.  
        - `info_url` → official municipal page for more details.  
        """
    )

    st.divider()

    with st.expander("ℹ About this dashboard"):
        st.markdown(
            """
            Built with **Python + Streamlit** using:

            - `piggdekk_support.csv` – support schemes per municipality  
            - `municipality_contacts.csv` – contact info for citizen services  
            - Optional enrichment from public APIs (Kommuneinfo)  

            You can extend it by adding more municipalities and updating support values.
            """
        )


if __name__ == "__main__":
    main()
