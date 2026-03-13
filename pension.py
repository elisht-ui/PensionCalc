import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import bidi
from datetime import datetime


def calc_coeff(current_age):
    return 201.81 * (
        1 + 0.149 * (datetime.now().year - 2024 + (67 - current_age)) / 100
    )


# פונקציית החישוב המרכזית
def calculate_pension(
    current_age,
    balance,
    monthly_dep,
    annual_return_pct,
    inflation_pct,
    manual_coefficient,
    health_tax_input,
    ni_benefit,
):
    retire_age = 67
    years_to_retire = retire_age - current_age
    if years_to_retire <= 0:
        st.error("הגיל חייב להיות נמוך מגיל הפרישה")
        return

    def get_trajectory(yield_pct):
        m_return = (yield_pct / 100) / 12
        months = years_to_retire * 12
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

    def calculate_pension_tax(gross_pension):
        # נתוני 2026 (משוערים לפי הצמדה למדד)
        exemption_sum = 6318  # 67% מתקרת הקצבה המזכה
        taxable_pension = max(0, gross_pension - exemption_sum)

        # מדרגות מס חודשיות (לפי הערכת 2026)
        tax = 0
        if taxable_pension <= 7010:
            tax = taxable_pension * 0.10
        elif taxable_pension <= 10060:
            tax = (7010 * 0.10) + (taxable_pension - 7010) * 0.14
        elif taxable_pension <= 16150:
            tax = (7010 * 0.10) + (3050 * 0.14) + (taxable_pension - 10060) * 0.20
        else:
            # מדרגות גבוהות יותר...
            tax = (
                (7010 * 0.10)
                + (3050 * 0.14)
                + (6090 * 0.20)
                + (taxable_pension - 16150) * 0.31
            )

        # נקודות זיכוי (2.25 נקודות זיכוי בסיסיות לגבר)
        credit_point_value = 250  # ערך נקודה ב-2026 (משוער)
        total_credits = 2.25 * credit_point_value

        final_tax = max(0, tax - total_credits)
        return final_tax

    def get_net_pension(f_bal, coeff, infl_pct):
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

    # הצגת נתונים ב-Streamlit

    # col1, col2 = st.columns(2)
    # col1.header("תמצית תחזית פרישה", divider=True )
    (col1,) = st.columns(1)
    col1.header("תמצית תחזית פרישה", divider=True)

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
    st.subheader("ניתוח ויזואלי")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    (ax1, ax2), (ax3, ax4) = axes
    years_arr = np.linspace(current_age, retire_age, len(user_balances))

    # גרף 1: צמיחה
    yield_range = np.arange(annual_return_pct - 1.5, annual_return_pct + 1.6, 0.5)
    for y in yield_range:
        bals, _ = get_trajectory(y)
        is_user = np.isclose(y, annual_return_pct)
        (line,) = ax1.plot(
            years_arr,
            bals / 1_000_000,
            label=f"{y:.1f}%",
            linewidth=3 if is_user else 1,
            alpha=0.8 if is_user else 0.4,
            color="teal" if is_user else "gray",
        )
        ax1.text(
            years_arr[-1],
            bals[-1] / 1_000_000,
            f" {y:.1f}%",
            color=line.get_color(),
            va="center",
            fontweight="bold" if is_user else "normal",
        )
        if is_user:
            ax1.fill_between(years_arr, bals / 1_000_000, color="teal", alpha=0.1)
    ax1.fill_between(
        years_arr,
        user_principals / 1_000_000,
        color="#4682B4",
        alpha=0.3,
        label=bidi.get_display("קרן (הפקדות)"),
    )
    ax1.set_title(bidi.get_display("צמיחת צבירה: רגישות לתשואה והרכב קרן"))
    ax1.set_ylabel(bidi.get_display("מליון ₪"))
    ax1.legend(loc="upper left")

    # גרף 2: עוגה
    labels_pie = [
        bidi.get_display("נטו פנסיה"),
        bidi.get_display("ביטוח לאומי"),
        bidi.get_display("מס הכנסה"),
        bidi.get_display("דמי בריאות"),
    ]
    sizes_pie = [gross_pension_fund - tax - health, ni, tax, health]
    ax2.pie(
        sizes_pie,
        labels=labels_pie,
        autopct="%1.1f%%",
        startangle=140,
        colors=["#99ff99", "#87CEEB", "#FFC0CB", "#FFA500"],
    )
    ax2.set_title(bidi.get_display("התפלגות קצבה חודשית ברוטו"))

    # גרף 3: אינפלציה
    inflations = np.linspace(1.5, 3.0, 10)
    for c in [200, 210, 215, 220]:
        nets = [get_net_pension(future_balance, c, i)[5] for i in inflations]
        (line,) = ax3.plot(
            inflations, nets, label=f"{c} - {bidi.get_display('מקדם')}", alpha=0.5
        )
        ax3.text(inflations[-1], nets[-1], f" {c}", color=line.get_color(), va="center")
    user_nets = [
        get_net_pension(future_balance, manual_coefficient, i)[5] for i in inflations
    ]
    ax3.plot(inflations, user_nets, color="red", linewidth=3, linestyle="--")
    ax3.axvline(x=inflation_pct, color="black", linestyle=":")
    ax3.set_title(bidi.get_display("רגישות: קצבה ריאלית מול אינפלציה (רגישות למקדם)"))
    ax3.legend()

    # גרף 4: תשואה
    yield_range_fine = np.linspace(annual_return_pct - 1.5, annual_return_pct + 1.5, 20)
    for inf in [1.5, 2.0, 2.5, 3.0]:
        is_target = np.isclose(inf, inflation_pct, atol=0.25)
        y_real_nets = [
            get_net_pension(get_trajectory(y_pct)[0][-1], manual_coefficient, inf)[5]
            for y_pct in yield_range_fine
        ]
        (line,) = ax4.plot(
            yield_range_fine,
            y_real_nets,
            label=f"{inf}% - {bidi.get_display('אינפלציה שנתית ממוצעת')}",
            linewidth=3 if is_target else 1,
        )
        ax4.text(
            yield_range_fine[-1],
            y_real_nets[-1],
            f" {inf}%",
            color=line.get_color(),
            va="center",
        )
    ax4.axvline(x=annual_return_pct, color="black", linestyle="--")
    ax4.set_title(bidi.get_display("רגישות: קצבה ריאלית מול תשואה (רדישות לאינפלציה)"))
    ax4.legend()

    plt.tight_layout()
    st.pyplot(fig)


def main():
    st.title("מחשבון פנסיה מתקדם")

    # יצירת סרגל צד להזנת נתונים
    with st.sidebar:
        st.header("נתוני כניסה")
        curr_age = st.number_input("גיל נוכחי", value=46)
        curr_fund_total = st.number_input("צבירה קיימת (₪)", value=1800000)
        monthly_deposit = st.number_input("הפקדה חודשית (₪)", value=7800)
        year_yield = st.slider("תשואה שנתית (%) ", 0.0, 10.0, 4.5)
        inflation = st.slider("אינפלציה שנתית (%) ", 0.0, 5.0, 1.9)
        projected_coeff = st.number_input("מקדם אקטוארי", value=calc_coeff(curr_age))
        health_tax = st.number_input("דמי בריאות (₪)", value=237)
        national_security = st.number_input("קצבת ביטוח לאומי (₪)", value=2300)

    st.title(f" פרישה בגיל 67, גיל נוכחי {curr_age}")

    # הפעלה
    calculate_pension(
        curr_age,
        curr_fund_total,
        monthly_deposit,
        year_yield,
        inflation,
        projected_coeff,
        health_tax,
        national_security,
    )


if __name__ == "__main__":
    main()
