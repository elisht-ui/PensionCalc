import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
from datetime import datetime
import streamlit.components.v1 as components

# Basic page configuration
st.set_page_config(page_title="Advanced Pension Calculator", layout="wide")


def calculate_coefficient(current_age: int) -> float:
    current_year = datetime.now().year
    return 201.81 * (1 + 0.149 * (current_year - 2024 + (67 - current_age)) / 100)


# Sidebar for data entry
with st.sidebar:
    st.header("נתוני כניסה")
    current_age = st.number_input("גיל נוכחי", value=46)
    current_fund_total = st.number_input("צבירה קיימת (₪)", value=1800000)
    monthly_deposit = st.number_input("הפקדה חודשית (₪)", value=7800)
    annual_yield = st.slider("תשואה שנתית (%) ", 0.0, 10.0, 4.5, 0.1)
    inflation_rate = st.slider("אינפלציה שנתית (%) ", 0.0, 5.0, 1.9)
    projected_coefficient = st.number_input(
        "מקדם אקטוארי", value=calculate_coefficient(current_age)
    )
    health_tax = st.number_input("דמי בריאות (₪)", value=237)
    national_insurance = st.number_input("קצבת ביטוח לאומי (₪)", value=2300)


def set_rtl_direction():
    """Sets the document direction to Right-to-Left (RTL) natively in the DOM,
    and ensures charts remain LTR to prevent visual layout bugs."""
    components.html(
        """
        <script>
            const parentDoc = window.parent.document;
            parentDoc.documentElement.dir = "rtl";
            
            // Inject CSS to keep Streamlit charts in LTR
            if (!parentDoc.getElementById("fix-charts-ltr")) {
                const style = parentDoc.createElement("style");
                style.id = "fix-charts-ltr";
                style.innerHTML = `
                    [data-testid="stArrowVegaLiteChart"], 
                    [data-testid="stVegaLiteChart"],
                    [data-baseweb="slider"] { 
                        direction: ltr; 
                    }
                `;
                parentDoc.head.appendChild(style);
            }
        </script>
        """,
        width=0,
        height=0,
    )


set_rtl_direction()

st.title("מחשבון פנסיה מתקדם", text_alignment="right")

st.title(f" פרישה בגיל 67, גיל נוכחי {current_age}", text_alignment="right")


# Main calculation function
def calculate_pension(
    current_age: int,
    balance: float,
    monthly_dep: float,
    annual_return_pct: float,
    inflation_pct: float,
    manual_coefficient: float,
    health_tax_input: float,
    ni_benefit: float,
):
    retire_age = 67
    years_to_retire = retire_age - current_age
    if years_to_retire <= 0:
        st.error("הגיל חייב להיות נמוך מגיל הפרישה")
        return

    def get_trajectory(yield_pct: float):
        m_return = (yield_pct / 100) / 12
        months = int(years_to_retire * 12)
        bals = [balance]
        prins = [balance]
        curr_bal = balance
        curr_prin = balance
        for _ in range(months):
            curr_bal = curr_bal * (1 + m_return) + monthly_dep
            curr_prin += monthly_dep
            bals.append(curr_bal)
            prins.append(curr_prin)
        return np.array(bals), np.array(prins)

    def calculate_pension_tax(gross_pension: float) -> float:
        # 2026 Data (Estimated by index linkage)
        exemption_sum = 6318  # 67% of the qualifying allowance ceiling
        taxable_pension = max(0, gross_pension - exemption_sum)

        # Monthly tax brackets (2026 estimate)
        tax = 0
        if taxable_pension <= 7010:
            tax = taxable_pension * 0.10
        elif taxable_pension <= 10060:
            tax = (7010 * 0.10) + (taxable_pension - 7010) * 0.14
        elif taxable_pension <= 16150:
            tax = (7010 * 0.10) + (3050 * 0.14) + (taxable_pension - 10060) * 0.20
        else:
            # Higher brackets...
            tax = (
                (7010 * 0.10)
                + (3050 * 0.14)
                + (6090 * 0.20)
                + (taxable_pension - 16150) * 0.31
            )

        # Credit points (2.25 basic credit points for a man)
        credit_point_value = 250  # Point value in 2026 (estimated)
        total_credits = 2.25 * credit_point_value

        final_tax = max(0, tax - total_credits)
        return final_tax

    def get_net_pension(f_bal: float, coeff: float, infl_pct: float):
        gross_pension = f_bal / coeff
        total_g = gross_pension + ni_benefit
        t = calculate_pension_tax(total_g)
        net = total_g - t - health_tax_input
        real_net = net / ((1 + (infl_pct / 100)) ** years_to_retire)
        return net, t, gross_pension, ni_benefit, health_tax_input, real_net

    user_balances, user_principals = get_trajectory(annual_return_pct)
    future_balance = user_balances[-1]
    net_pension, tax, gross_pension_fund, ni, health, real_val = get_net_pension(
        future_balance, manual_coefficient, inflation_pct
    )

    # Display data in Streamlit

    (col1,) = st.columns(1)
    col1.header("תמצית תחזית פרישה", divider=True, text_alignment="right")

    col1, col2, col3 = st.columns(3)
    col1.metric("צבירה בפרישה (נומינלי)", f"{future_balance:,.0f} ₪")
    col2.metric("קצבת פנסיה (ברוטו)", f"{gross_pension_fund:,.0f} ₪")

    (col1,) = st.columns(1)
    col1.header("", divider=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("מס הכנסה משוער", f"{tax:,.0f} ₪")
    col2.metric("קצבת נטו חודשית", f"{net_pension:,.0f} ₪")
    col3.metric("ערך ריאלי (כוח קנייה היום)", f"{real_val:,.0f} ₪", border=True)

    st.markdown("---")
    st.subheader("ניתוח ויזואלי", text_alignment="right")

    # Prepare Layout
    chart_row1_col1, chart_row1_col2 = st.columns(2)
    chart_row2_col1, chart_row2_col2 = st.columns(2)

    years_arr = np.linspace(current_age, retire_age, len(user_balances))

    # Graph 1: Growth
    # Prepare Data
    yield_range = np.arange(annual_return_pct - 1.5, annual_return_pct + 1.6, 0.5)
    growth_data = []

    for y in yield_range:
        bals, _ = get_trajectory(y)
        is_user = np.isclose(y, annual_return_pct)
        label_str = f"{y:.1f}%"
        for i, val in enumerate(bals):
            growth_data.append(
                {
                    "Year": years_arr[i],
                    "Amount": val / 1_000_000,
                    "Yield": label_str,
                    "IsUser": is_user,
                    "Type": "Forecast",
                }
            )

    # Add Principal Data
    for i, val in enumerate(user_principals):
        growth_data.append(
            {
                "Year": years_arr[i],
                "Amount": val / 1_000_000,
                "Yield": "Principal",
                "IsUser": False,
                "Type": "Principal",
            }
        )

    df_growth = pd.DataFrame(growth_data)

    # Build Chart 1
    base_growth = alt.Chart(df_growth).encode(x=alt.X("Year", title="גיל"))

    # Layer 1: Principal Area
    area_principal = (
        base_growth.transform_filter(alt.datum.Type == "Principal")
        .mark_area(color="#4682B4", opacity=0.3)
        .encode(y=alt.Y("Amount", title="מליון ₪"))
    )

    # Layer 2: User Confidence Area (Fill under user line)
    area_user = (
        base_growth.transform_filter(alt.datum.IsUser)
        .mark_area(color="teal", opacity=0.1)
        .encode(y="Amount")
    )

    # Layer 3: Lines
    lines_growth = (
        base_growth.transform_filter(alt.datum.Type == "Forecast")
        .mark_line()
        .encode(
            y="Amount",
            color=alt.condition(alt.datum.IsUser, alt.value("teal"), alt.value("gray")),
            strokeWidth=alt.condition(alt.datum.IsUser, alt.value(3), alt.value(1)),
            opacity=alt.condition(alt.datum.IsUser, alt.value(0.8), alt.value(0.4)),
            detail="Yield",
        )
    )

    # Layer 4: Text Labels at the end
    base_text_layer = base_growth.transform_filter(
        alt.datum.Type == "Forecast"
    ).transform_filter(f"datum.Year >= {years_arr[-1] - 0.01}")

    text_growth_user = (
        base_text_layer.transform_filter(alt.datum.IsUser)
        .mark_text(align="left", dx=5, fontWeight="bold")
        .encode(y="Amount", text="Yield", color=alt.value("teal"))
    )

    text_growth_others = (
        base_text_layer.transform_filter(alt.datum.IsUser == False)
        .mark_text(align="left", dx=5, fontWeight="normal")
        .encode(y="Amount", text="Yield", color=alt.value("gray"))
    )

    chart1 = (
        (
            area_principal
            + area_user
            + lines_growth
            + text_growth_user
            + text_growth_others
        )
        .properties(title="צמיחת צבירה: רגישות לתשואה והרכב קרן", width=600, height=450)
        .interactive()
    )

    with chart_row1_col1:
        st.altair_chart(chart1)

    # Graph 2: Pie Chart
    # Matplotlib used fixed colors and calculated slices
    sizes_pie = [gross_pension_fund - tax - health, ni, tax, health]
    labels_pie = ["נטו פנסיה", "ביטוח לאומי", "מס הכנסה", "דמי בריאות"]
    colors_pie = ["#99ff99", "#87CEEB", "#FFC0CB", "#FFA500"]

    df_pie = pd.DataFrame(
        {"Category": labels_pie, "Value": sizes_pie, "Color": colors_pie}
    )
    # Calculate percentage for labels
    total_pie = sum(sizes_pie)
    df_pie["Percent"] = (df_pie["Value"] / total_pie).map("{:.1%}".format)

    base_pie = alt.Chart(df_pie).encode(theta=alt.Theta("Value", stack=True))

    pie_arc = base_pie.mark_arc(outerRadius=100).encode(
        color=alt.Color(
            "Category",
            scale=alt.Scale(domain=labels_pie, range=colors_pie),
            legend=alt.Legend(title="מרכיבי ההכנסה"),
        ),
        order=alt.Order("Value", sort="descending"),
        tooltip=["Category", "Value", "Percent"],
    )

    pie_text = base_pie.mark_text(radius=120).encode(
        text="Percent",
        order=alt.Order("Value", sort="descending"),
        color=alt.value("white"),
    )

    chart2 = (pie_arc + pie_text).properties(
        title="התפלגות קצבה חודשית ברוטו", width=600, height=450
    )

    with chart_row1_col2:
        st.altair_chart(chart2)

    # Graph 3: Inflation
    inflations = np.linspace(1.5, 3.0, 10)
    infl_data = []
    for c in [200, 210, 215, 220]:
        nets = [get_net_pension(future_balance, c, i)[5] for i in inflations]
        for i, val in enumerate(nets):
            infl_data.append(
                {
                    "Inflation": inflations[i],
                    "Net": val,
                    "Label": f"{c}",
                    "Coeff": str(c),
                    "Type": "Scenario",
                }
            )

    user_nets = [
        get_net_pension(future_balance, manual_coefficient, i)[5] for i in inflations
    ]
    for i, val in enumerate(user_nets):
        infl_data.append(
            {
                "Inflation": inflations[i],
                "Net": val,
                "Label": "User",
                "Coeff": "User",
                "Type": "User",
            }
        )

    df_infl = pd.DataFrame(infl_data)
    infl_min = inflations[0]
    infl_max = inflations[-1]
    infl_domain_max = infl_max + (infl_max - infl_min) * 0.01
    base_infl = alt.Chart(df_infl).encode(
        x=alt.X(
            "Inflation",
            title="אינפלציה (%)",
            scale=alt.Scale(domain=[infl_min, infl_domain_max]),
        )
    )

    lines_infl = (
        base_infl.transform_filter(alt.datum.Type == "Scenario")
        .mark_line(opacity=0.5)
        .encode(
            y=alt.Y("Net", title="קצבה ריאלית", scale=alt.Scale(zero=False)),
            color=alt.Color("Label", legend=alt.Legend(title="מקדמים")),
        )
    )

    text_infl = (
        base_infl.transform_filter(alt.datum.Type == "Scenario")
        .transform_filter(f"datum.Inflation >= {inflations[-1] - 0.01}")
        .mark_text(align="left", dx=5)
        .encode(y="Net", text="Coeff", color="Label")
    )

    user_line_infl = (
        base_infl.transform_filter(alt.datum.Type == "User")
        .mark_line(color="red", strokeDash=[5, 5], strokeWidth=3)
        .encode(y="Net")
    )

    curr_infl_rule = (
        alt.Chart(pd.DataFrame({"x": [inflation_pct]}))
        .mark_rule(strokeDash=[5, 5], color="white")
        .encode(x="x")
    )

    chart3 = (
        (lines_infl + text_infl + user_line_infl + curr_infl_rule)
        .properties(
            title="רגישות: קצבה ריאלית מול אינפלציה (רגישות למקדם)",
            width=600,
            height=450,
        )
        .interactive()
    )

    with chart_row2_col1:
        st.altair_chart(chart3)

    # Graph 4: Yield
    yield_range_fine = np.linspace(annual_return_pct - 1.5, annual_return_pct + 1.5, 20)
    yield_sens_data = []

    for inf in [1.5, 2.0, 2.5, 3.0]:
        is_target = np.isclose(inf, inflation_pct, atol=0.25)
        y_real_nets = [
            get_net_pension(get_trajectory(y_pct)[0][-1], manual_coefficient, inf)[5]
            for y_pct in yield_range_fine
        ]
        label_t = f"{inf}%"
        for i, val in enumerate(y_real_nets):
            yield_sens_data.append(
                {
                    "Yield": yield_range_fine[i],
                    "Net": val,
                    "Inflation": inf,
                    "Label": f"{inf}%",
                    "IsTarget": is_target,
                    "Tag": label_t,
                }
            )

    df_yield_sens = pd.DataFrame(yield_sens_data)

    yield_min = yield_range_fine[0]
    yield_max = yield_range_fine[-1]
    yield_domain_max = yield_max + (yield_max - yield_min) * 0.05
    base_yield = alt.Chart(df_yield_sens).encode(
        x=alt.X(
            "Yield",
            title="תשואה שנתית (%)",
            scale=alt.Scale(domain=[yield_min, yield_domain_max]),
        )
    )

    lines_yield = base_yield.mark_line().encode(
        y=alt.Y("Net", title="קצבה ריאלית", scale=alt.Scale(zero=False)),
        color=alt.Color("Label", legend=alt.Legend(title="אינפלציה")),
        strokeWidth=alt.condition(alt.datum.IsTarget, alt.value(3), alt.value(1)),
    )

    text_yield = (
        base_yield.transform_filter(f"datum.Yield >= {yield_range_fine[-1] - 0.01}")
        .mark_text(align="left", dx=5)
        .encode(y="Net", text="Tag", color="Label")
    )

    curr_yield_rule = (
        alt.Chart(pd.DataFrame({"x": [annual_return_pct]}))
        .mark_rule(strokeDash=[5, 5], color="white")
        .encode(x="x")
    )

    chart4 = (
        (lines_yield + text_yield + curr_yield_rule)
        .properties(
            title="רגישות: קצבה ריאלית מול תשואה (רגישות לאינפלציה)",
            width=600,
            height=450,
        )
        .interactive()
    )

    with chart_row2_col2:
        st.altair_chart(chart4)


# Execution
calculate_pension(
    current_age,
    current_fund_total,
    monthly_deposit,
    annual_yield,
    inflation_rate,
    projected_coefficient,
    health_tax,
    national_insurance,
)
