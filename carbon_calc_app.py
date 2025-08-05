import streamlit as st
import pandas as pd
import json
import os

# ------------------ CONFIG ------------------ #
ICE_DB_PATH = "Carbon Calc.xlsx"  # Local file in the repo
SAVE_FOLDER = "saved_calculations"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ------------------ LOAD DATA ------------------ #
@st.cache_data
def load_ice_db(path):
    df = pd.read_excel(path)
    df['Material'] = df['Material'].fillna("").astype(str).str.strip()
    df['Sub-material'] = df['Sub-material'].fillna("").astype(str).str.strip()
    df['ICE DB Name'] = df['ICE DB Name'].fillna("").astype(str).str.strip()
    df['Units of declared unit'] = df['Units of declared unit'].fillna("").astype(str).str.strip()
    return df

ice_db = load_ice_db(ICE_DB_PATH)

# ------------------ SESSION STATE ------------------ #
if "adds" not in st.session_state:
    st.session_state.adds = []
if "omits" not in st.session_state:
    st.session_state.omits = []

# ------------------ FUNCTIONS ------------------ #
def update_totals():
    total_add = sum(item["Total_EC"] for item in st.session_state.adds)
    total_omit = sum(item["Total_EC"] for item in st.session_state.omits)
    net_change = total_add - total_omit
    return total_add, total_omit, net_change

def save_calculation(name, description):
    data = {
        "name": name,
        "description": description,
        "adds": st.session_state.adds,
        "omits": st.session_state.omits
    }
    file_path = os.path.join(SAVE_FOLDER, f"{name}.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    st.success(f"Saved to {file_path}")

def load_calculation(file):
    with open(file, "r") as f:
        data = json.load(f)
    st.session_state.adds = data.get("adds", [])
    st.session_state.omits = data.get("omits", [])
    return data.get("name", ""), data.get("description", "")

def add_item(list_type, ice_name, qty):
    match = ice_db[ice_db['ICE DB Name'] == ice_name]
    if match.empty:
        st.warning(f"{ice_name} not found in ICE DB")
        return
    row = match.iloc[0]
    ec_per_unit = row['Embodied Carbon (kg CO2e per declared unit)']
    total_ec = ec_per_unit * qty
    entry = {"ICE DB Name": ice_name, "Qty": qty, "EC_per_unit": ec_per_unit, "Total_EC": total_ec}
    if list_type == "Add":
        st.session_state.adds.append(entry)
    else:
        st.session_state.omits.append(entry)

def delete_item(list_type, index):
    if list_type == "Add":
        st.session_state.adds.pop(index)
    else:
        st.session_state.omits.pop(index)

# ------------------ UI ------------------ #
st.title("🌍 Embodied Carbon Calculator")

# Calculation name & description
col1, col2 = st.columns([2, 3])
calc_name = col1.text_input("Calculation Name")
calc_desc = col2.text_input("Description")

# Save / Load
col1, col2 = st.columns(2)
if col1.button("💾 Save Calculation"):
    if calc_name.strip():
        save_calculation(calc_name, calc_desc)
    else:
        st.warning("Enter a calculation name before saving.")
if col2.button("📂 Load Calculation"):
    files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith(".json")]
    if files:
        file_to_load = st.selectbox("Select saved JSON", files)
        if st.button("Load Now"):
            name, desc = load_calculation(os.path.join(SAVE_FOLDER, file_to_load))
            st.success(f"Loaded {file_to_load}")
            st.experimental_rerun()
    else:
        st.info("No saved calculations found.")

st.divider()

# Material filters
material = st.selectbox("Material", sorted(ice_db['Material'].unique()))
sub_materials = sorted(ice_db[ice_db['Material'] == material]['Sub-material'].unique())
sub_material = st.selectbox("Sub-Material", sub_materials)
ice_names = sorted(ice_db[(ice_db['Material'] == material) & (ice_db['Sub-material'] == sub_material)]['ICE DB Name'].unique())
ice_name = st.selectbox("ICE DB Name", ice_names)

# Show unit
if ice_name:
    unit = ice_db[ice_db['ICE DB Name'] == ice_name]['Units of declared unit'].iloc[0]
    st.info(f"Unit of measure: {unit}")

# Quantity calculator
st.subheader("Quantity")
qty = st.number_input("Quantity", min_value=0.0, value=0.0, format="%.4f")

with st.expander("📐 Calculate Quantity from Dimensions"):
    nr = st.number_input("Nr", min_value=0.0, value=1.0)
    length = st.number_input("Length", min_value=0.0, value=1.0)
    width = st.number_input("Width", min_value=0.0, value=1.0)
    depth = st.number_input("Depth", min_value=0.0, value=1.0)
    factor = st.number_input("Factor", min_value=0.0, value=1.0)
    calc_qty = nr * length * width * depth * factor
    st.write(f"Calculated Quantity: **{calc_qty:.4f}**")
    if st.button("Use Calculated Quantity"):
        qty = calc_qty

# Add / Omit
col1, col2 = st.columns(2)
if col1.button("➕ Add"):
    if qty > 0 and ice_name:
        add_item("Add", ice_name, qty)
if col2.button("➖ Omit"):
    if qty > 0 and ice_name:
        add_item("Omit", ice_name, qty)

st.divider()

# Adds table
st.subheader("Adds")
for i, item in enumerate(st.session_state.adds):
    st.write(f"{i+1}. {item['ICE DB Name']} - Qty: {item['Qty']:.2f} - EC/unit: {item['EC_per_unit']:.2f} - Total: {item['Total_EC']:.2f}")
    if st.button(f"Delete Add {i+1}", key=f"del_add_{i}"):
        delete_item("Add", i)
        st.experimental_rerun()

# Omits table
st.subheader("Omits")
for i, item in enumerate(st.session_state.omits):
    st.write(f"{i+1}. {item['ICE DB Name']} - Qty: {item['Qty']:.2f} - EC/unit: {item['EC_per_unit']:.2f} - Total: {item['Total_EC']:.2f}")
    if st.button(f"Delete Omit {i+1}", key=f"del_omit_{i}"):
        delete_item("Omit", i)
        st.experimental_rerun()

# Totals
total_add, total_omit, net_change = update_totals()
st.metric("Total Adds (kgCO₂e)", f"{total_add:,.2f}")
st.metric("Total Omits (kgCO₂e)", f"{total_omit:,.2f}")
st.metric("Net Change (kgCO₂e)", f"{net_change:,.2f}", delta=net_change)
