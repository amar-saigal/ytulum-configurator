import streamlit as st
import json
import math
from fpdf import FPDF
import tempfile
import os
import matplotlib.pyplot as plt
import io

# Load JSON configuration file
with open("Ytulum_Purchase_Config.json") as f:
    config = json.load(f)

st.set_page_config(page_title="Ytulum Property Configurator")
st.title("🏡 Ytulum Property Purchase Configurator")

# Step 1: Unit Type
unit_type = st.selectbox("1. Select Unit Type", list(config["unit_types"].keys()))
unit_info = config["unit_types"][unit_type]

# Step 2: Configuration
configuration = st.selectbox("2. Choose Configuration", unit_info["configurations"])

# Determine base price
base_price = unit_info["base_price_usd"][configuration] if isinstance(unit_info["base_price_usd"], dict) else unit_info["base_price_usd"]

# Step 3: Upgrades
st.markdown("**3. Select Applicable Upgrades**")
selected_upgrades = []
upgrade_total = 0
for upgrade, price in unit_info["upgrades"].items():
    if st.checkbox(f"{upgrade} (+${price:,})"):
        selected_upgrades.append(upgrade)
        upgrade_total += price

# Step 4: Art Tier
st.markdown("**4. Choose Art Tier**")
art_tier = st.selectbox("Art Tier", list(config["art_tiers"].keys()))
art_multiplier = config["art_tiers"][art_tier]
art_cost = base_price * art_multiplier

# Step 5: Financing
st.markdown("**5. Financing Details**")
num_buyers = st.number_input("Number of Buyers", 1, config["financing"]["max_buyers"], 1)
downpayment_percent = st.selectbox("Downpayment %", config["financing"]["downpayment_options_percent"])
duration_years = st.selectbox("Loan Duration (Years)", config["financing"]["loan_durations_years"])
interest_rate = config["financing"]["interest_rate_annual"]

# Step 6: Financial Calculations
final_price = base_price + upgrade_total + art_cost
price_per_buyer = final_price / num_buyers
downpayment = price_per_buyer * (downpayment_percent / 100)
loan_amount = price_per_buyer - downpayment
months = duration_years * 12
monthly_interest = interest_rate / 12
monthly_payment = (
    loan_amount * (monthly_interest * (1 + monthly_interest)**months) / ((1 + monthly_interest)**months - 1)
    if downpayment_percent < 100 else 0
)
total_paid = downpayment + monthly_payment * months

# Step 7: Formatted Summary
st.markdown("""
<style>
    .summary-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-size: 16px;
    }
    .summary-section h4 {
        margin-top: 0;
    }
    .summary-item {
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

summary_html = f"""
<div class='summary-section'>
    <h4>📈 Purchase Summary</h4>
    <div class='summary-item'><strong>Base Price:</strong> ${base_price:,.2f}</div>
    <div class='summary-item'><strong>Upgrades Total:</strong> ${upgrade_total:,.2f}</div>
    <div class='summary-item'><strong>Art Tier ({art_tier}):</strong> ${art_cost:,.2f}</div>
    <div class='summary-item'><strong>Final Price:</strong> ${final_price:,.2f}</div>
    <br>
    <h4>Each Buyer Pays:</h4>
    <div class='summary-item'><strong>Downpayment:</strong> ${downpayment:,.2f}</div>
    <div class='summary-item'><strong>Loan Amount:</strong> ${loan_amount:,.2f}</div>
    <div class='summary-item'><strong>Monthly Payment ({months} mo @ {interest_rate*100:.1f}%):</strong> ${monthly_payment:,.2f}</div>
    <div class='summary-item'><strong>Total Paid Over Term:</strong> ${total_paid:,.2f}</div>
</div>
"""
st.markdown(summary_html, unsafe_allow_html=True)

# Step 8: Payment Timeline Chart
st.markdown("**\n\U0001F4C9 Payment Timeline**")
labels_array = ["Downpayment"] + [f"Month {i+1}" for i in range(months)]
payments_array = [downpayment] + [monthly_payment] * months

# Handle case when months < 12 to prevent slider error
slider_min = 6
slider_max = max(slider_min + 6, months)
months_to_show = st.slider(
    "Months to Display in Chart",
    min_value=slider_min,
    max_value=slider_max,
    value=min(12, months),
    step=6
)

trimmed_labels = labels_array[:months_to_show + 1]  # +1 to include Downpayment
trimmed_values = payments_array[:months_to_show + 1]

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(trimmed_labels, trimmed_values, color=['red'] + ['blue'] * (len(trimmed_labels) - 1))
ax.set_xlabel("Month")
ax.set_ylabel("Amount (USD)")
ax.set_title("Ytulum Payment Schedule (Downpayment + Monthly Breakdown)")
plt.xticks(rotation=45)
plt.tight_layout()
ax.legend(["Downpayment", "Monthly Payments"])
st.pyplot(fig)


# Step 9: PDF Export
if st.button("Generate PDF Summary"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Ytulum Purchase Summary", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Unit Type: {unit_type} ({configuration})", ln=True)
    pdf.cell(200, 10, txt=f"Base Price: ${base_price:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Selected Upgrades: {', '.join(selected_upgrades) if selected_upgrades else 'None'}", ln=True)
    pdf.cell(200, 10, txt=f"Upgrades Total: ${upgrade_total:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Art Tier: {art_tier} (+{art_multiplier*100:.0f}%) = ${art_cost:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Final Price: ${final_price:,.2f}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Number of Buyers: {num_buyers}", ln=True)
    pdf.cell(200, 10, txt=f"Downpayment: ${downpayment:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Loan Amount: ${loan_amount:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Monthly Payment: ${monthly_payment:,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Total Paid Over {months} Months: ${total_paid:,.2f}", ln=True)

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    chart_path = os.path.join(tempfile.gettempdir(), "payment_chart.png")
    with open(chart_path, "wb") as f:
        f.write(img_buffer.read())
    pdf.image(chart_path, x=10, y=pdf.get_y() + 10, w=180)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        tmp_file.close()
        with open(tmp_file.name, "rb") as file:
            st.download_button(
                label="Download PDF",
                data=file,
                file_name="ytulum_purchase_summary.pdf",
                mime="application/pdf"
            )
        os.unlink(tmp_file.name)
        os.unlink(chart_path)
