from decimal import Decimal, ROUND_HALF_UP

INSURANCE_CONTRIBUTIONS = {
    2024: 49500,
    2025: 53658,
    2026: 57390,
}

ADDITIONAL_CONTRIBUTION_RATE = 0.01
ADDITIONAL_CONTRIBUTION_THRESHOLD = 300000
VAT_INCOME_THRESHOLD = 20_000_000


def round_rub(value: float) -> int:
    """Округление до целого рубля по правилам ФНС: <0.5 отбрасывается, >=0.5 — вверх."""
    return int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def calculate_tax_by_quarters(q1: float, q2: float, q3: float, q4: float,
                               tax_rate: float, year: int,
                               has_employees: bool = False) -> dict:
    incomes = [q1, q2, q3, q4]
    insurance_total = INSURANCE_CONTRIBUTIONS.get(year, 0)

    cumulative_income = 0
    net_paid_so_far = 0
    quarters = []

    for i, income in enumerate(incomes, start=1):
        cumulative_income += income
        base_tax_cumulative = round_rub(cumulative_income * tax_rate / 100)

        additional_contribution_cumulative = round_rub(max(
            cumulative_income - ADDITIONAL_CONTRIBUTION_THRESHOLD, 0
        ) * ADDITIONAL_CONTRIBUTION_RATE)

        total_deduction_pool = insurance_total + additional_contribution_cumulative

        if has_employees:
            max_deduction = base_tax_cumulative / 2
            deduction_cumulative = round_rub(min(total_deduction_pool, max_deduction))
        else:
            deduction_cumulative = round_rub(min(total_deduction_pool, base_tax_cumulative))

        tax_after_deduction = base_tax_cumulative - deduction_cumulative
        diff = tax_after_deduction - net_paid_so_far

        if diff >= 0:
            tax_to_pay_this_quarter = diff
            tax_to_decrease_this_quarter = 0
        else:
            tax_to_pay_this_quarter = 0
            tax_to_decrease_this_quarter = -diff

        net_paid_so_far += tax_to_pay_this_quarter - tax_to_decrease_this_quarter

        quarters.append({
            "quarter": i,
            "income_quarter": round_rub(income),
            "cumulative_income": round_rub(cumulative_income),
            "base_tax_cumulative": base_tax_cumulative,
            "additional_contribution_cumulative": additional_contribution_cumulative,
            "deduction_cumulative": deduction_cumulative,
            "tax_to_pay_this_quarter": tax_to_pay_this_quarter,
            "tax_to_decrease_this_quarter": tax_to_decrease_this_quarter,
        })

    return {
        "quarters": quarters,
        "total_income": round_rub(cumulative_income),
        "insurance_contribution": insurance_total,
        "additional_contribution_total": quarters[-1]["additional_contribution_cumulative"],
        "total_tax_for_year": net_paid_so_far,
        "has_employees": has_employees,
        "exceeds_vat_threshold": cumulative_income > VAT_INCOME_THRESHOLD,
    }