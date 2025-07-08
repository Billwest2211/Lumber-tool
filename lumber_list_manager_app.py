
import streamlit as st
import pandas as pd
import io
import math

st.set_page_config(page_title="Lumber List Manager", layout="wide")

st.title("🪵 Lumber List Manager")

# Upload CSV/Excel files
uploaded_files = st.file_uploader("Upload one or more spreadsheets", type=["csv", "xlsx"], accept_multiple_files=True)

def dimension_rank(val):
    if pd.isna(val): return float('inf')
    if "OSB" in str(val).upper(): return float('inf') + 1
    try:
        parts = str(val).upper().split("X")
        return float(parts[0]) * 100 + float(parts[1])
    except:
        return float('inf')

def parse_length(value):
    try:
        return float(str(value).replace("'", "").strip())
    except:
        return float('inf')

def calculate_board_feet(row):
    try:
        return (row['Thickness'] * row['Width'] * row['Length (ft)'] / 12) * row['Qty']
    except:
        return 0

unit_sizes = {
    "2x4": 294, "2x6": 189, "2x8": 147, "2x10": 105, "2x12": 84,
    "4x4": 91, "4x6": 64, "4x8": 48, "4x10": 40, "4x12": 32,
    "6x6": 32, "6x8": 24, "6x10": 20, "6x12": 16
}

def get_unit_key(row):
    return f"{int(row['Thickness'])}x{int(row['Width'])}"

def compute_units(row):
    size_key = get_unit_key(row)
    unit_size = unit_sizes.get(size_key)
    if unit_size:
        full_units = row["Qty"] // unit_size
        remaining = row["Qty"] % unit_size
        return pd.Series([full_units, remaining])
    else:
        return pd.Series([None, None])

if uploaded_files:
    df_list = []
    for file in uploaded_files:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        df["Source"] = file.name
        df_list.append(df)

    combined_df = pd.concat(df_list, ignore_index=True)

    # Detect key columns
    columns = list(combined_df.columns)
    with st.expander("⚙️ Column Mapping (optional override)"):
        thickness_col = st.selectbox("Select Thickness Column", columns, index=0)
        width_col = st.selectbox("Select Width Column", columns, index=1)
        length_col = st.selectbox("Select Length Column", columns, index=2)
        qty_col = st.selectbox("Select Quantity Column", columns, index=3)
        pet_col = st.selectbox("Select PET Column", columns, index=4)
        dimension_col = st.selectbox("Select Dimension Column", columns, index=5)

    combined_df.rename(columns={
        thickness_col: "Thickness",
        width_col: "Width",
        length_col: "Length (ft)",
        qty_col: "Qty",
        pet_col: "PET",
        dimension_col: "Dimension"
    }, inplace=True)

    # Sort + Process
    has_pet = combined_df[combined_df["PET"].notna()].copy()
    no_pet = combined_df[combined_df["PET"].isna()].copy()

    has_pet["__DimRank__"] = has_pet["Dimension"].apply(dimension_rank)
    has_pet["__PETSort__"] = has_pet["PET"].apply(parse_length)

    no_pet["__DimRank__"] = no_pet["Dimension"].apply(dimension_rank)
    no_pet["__PETSort__"] = float('inf')

    df = pd.concat([has_pet, no_pet], ignore_index=True)
    df["__IsOSB__"] = df["Dimension"].astype(str).str.upper().str.contains("OSB")

    df = df.sort_values(by=["__IsOSB__", "__DimRank__", "__PETSort__"], ascending=[True, True, True])
    df.drop(columns=["__DimRank__", "__PETSort__", "__IsOSB__"], inplace=True)

    # Allow manual editing
    st.subheader("📝 Edit Your Lumber List")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # Recalculate board feet and units
    edited_df["Total_BF"] = edited_df.apply(calculate_board_feet, axis=1)
    edited_df[["Full Units", "Remaining Pieces"]] = edited_df.apply(compute_units, axis=1)

    st.subheader("📦 Final Processed Data")
    st.dataframe(edited_df, use_container_width=True)

    # Export
    to_download = edited_df.dropna(how="all")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        to_download.to_excel(writer, index=False, sheet_name="CleanedData")
    st.download_button("📥 Download Cleaned Excel File", data=output.getvalue(), file_name="cleaned_lumber_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
