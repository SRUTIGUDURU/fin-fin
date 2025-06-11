import streamlit as st
import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np # Retained for potential underlying use by pandas or future numerical ops
from typing import List, Dict, Optional
import math # Retained for potential math operations

# Configure Streamlit page
st.set_page_config(
    page_title="Personal Economic Model - Life Decision Simulator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem; /* Adjusted for better fit */
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1.5rem; /* Adjusted */
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        text-align: center; /* Center metric content */
    }
    .stMetric { /* Target Streamlit's metric component */
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        background-color: #ffffff;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    .stDataFrame { /* Style dataframes for better readability */
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "financial_scenarios.json"

class FinancialSimulator:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        """Loads existing scenarios from JSON file."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    loaded_data = json.load(f)
                    if "scenarios" not in loaded_data or not isinstance(loaded_data["scenarios"], list):
                        return {"scenarios": []} # Ensure correct structure
                    return loaded_data
            except json.JSONDecodeError:
                return {"scenarios": []}
        return {"scenarios": []}

    def save_data(self):
        """Saves scenario data to JSON file."""
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=4)

    def add_scenario(self, scenario_data):
        """Adds a new scenario to the data."""
        scenario_data["created_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Generate a more robust ID, e.g., timestamp-based or UUID if scaling
        scenario_data["id"] = datetime.datetime.now().timestamp() # Simple unique ID
        self.data["scenarios"].append(scenario_data)
        self.save_data()

    def get_scenarios(self):
        """Returns all scenarios."""
        return self.data["scenarios"]

    def get_scenario_by_id(self, scenario_id):
        """Returns a scenario by ID."""
        for scenario in self.data["scenarios"]:
            if scenario.get("id") == scenario_id:
                return scenario
        return None

    def delete_scenario(self, scenario_id):
        """Deletes a scenario by ID."""
        self.data["scenarios"] = [s for s in self.data["scenarios"] if s.get("id") != scenario_id]
        self.save_data()
        return True # Indicate success

    def simulate_scenario(self, scenario, years=30, inflation_rate=0.03, tax_rate=0.25):
        """Runs a comprehensive financial simulation."""

        # Initialize tracking variables
        age = scenario["starting_age"]
        current_salary = scenario["starting_salary"]
        current_growth_rate = scenario["salary_growth_rate"]
        net_worth = 0
        liquid_savings = 0 # For emergency fund
        investment_portfolio = 0
        total_earned_gross = 0
        total_saved = 0
        total_spent_living = 0
        total_spent_major = 0
        total_taxes_paid = 0
        debt_balance = scenario.get("student_debt", 0)

        yearly_data = []
        monthly_expenses_base = scenario["monthly_expenses"]

        for year_idx in range(years): # Use year_idx to avoid conflict with 'year' key
            year_data = {
                "year": year_idx + 1,
                "age": age + year_idx,
                "events": []
            }

            # Apply career changes
            for change in scenario.get("career_changes", []):
                if change["year"] == year_idx: # 0-indexed year for changes
                    current_salary = change["new_salary"]
                    current_growth_rate = change["new_growth_rate"]
                    year_data["events"].append(f"Career change to ${current_salary:,.0f} with {current_growth_rate*100:.1f}% growth.")

            # Calculate inflation-adjusted expenses
            inflation_multiplier = (1 + inflation_rate) ** year_idx
            monthly_expenses_adjusted = monthly_expenses_base * inflation_multiplier
            annual_living_expenses = monthly_expenses_adjusted * 12

            # Calculate annual income with growth
            # Salary growth is applied from the base salary over the years
            annual_gross_income = scenario["starting_salary"] * ((1 + scenario["salary_growth_rate"]) ** year_idx)
            # If a career change happened, use the new salary and growth from that point
            for change in scenario.get("career_changes", []):
                if change["year"] <= year_idx:
                    years_since_change = year_idx - change["year"]
                    annual_gross_income = change["new_salary"] * ((1 + change["new_growth_rate"]) ** years_since_change)


            # Calculate taxes
            annual_taxes = annual_gross_income * tax_rate
            after_tax_income = annual_gross_income - annual_taxes

            year_data.update({
                "gross_salary": annual_gross_income,
                "taxes": annual_taxes,
                "after_tax_income": after_tax_income,
                "living_expenses": annual_living_expenses,
                "inflation_multiplier": inflation_multiplier
            })

            total_earned_gross += annual_gross_income
            total_taxes_paid += annual_taxes
            total_spent_living += annual_living_expenses

            # Handle major expenses
            major_expense_this_year = 0
            for expense in scenario.get("major_expenses", []):
                if expense["year"] == year_idx: # 0-indexed year for expenses
                    adjusted_expense_amount = expense["amount"] * inflation_multiplier
                    major_expense_this_year += adjusted_expense_amount
                    year_data["events"].append(f"Major Expense: {expense['name']} for ${adjusted_expense_amount:,.0f}")

            total_spent_major += major_expense_this_year

            # Handle debt payments
            debt_payment_this_year = 0
            if debt_balance > 0:
                # Simple model: fixed annual payment (e.g., 10% of original debt, or a min payment)
                # More complex would involve interest rates on debt.
                # For simplicity, let's assume a fixed portion of student debt is paid annually if affordable
                annual_debt_payment_target = scenario.get("student_debt", 0) * 0.10 # Pay 10% of original debt per year
                debt_payment_this_year = min(annual_debt_payment_target, debt_balance, after_tax_income - annual_living_expenses - major_expense_this_year)
                debt_payment_this_year = max(0, debt_payment_this_year) # Ensure non-negative
                debt_balance -= debt_payment_this_year
                year_data["debt_payment"] = debt_payment_this_year
                year_data["remaining_debt"] = debt_balance
                if debt_payment_this_year > 0:
                    year_data["events"].append(f"Debt payment: ${debt_payment_this_year:,.0f}")


            # Calculate available for savings
            disposable_income_after_essentials = after_tax_income - annual_living_expenses - major_expense_this_year - debt_payment_this_year

            # Emergency fund logic
            emergency_fund_target = annual_living_expenses * 0.5  # 6 months of living expenses
            emergency_fund_contribution = 0

            if liquid_savings < emergency_fund_target and disposable_income_after_essentials > 0:
                # Prioritize emergency fund. Let's say up to 20% of disposable income until target met
                to_contribute = min(disposable_income_after_essentials * 0.20, emergency_fund_target - liquid_savings)
                emergency_fund_contribution = max(0, to_contribute)
                liquid_savings += emergency_fund_contribution

            # Investment contributions from the remaining disposable income based on savings rate
            remaining_disposable = disposable_income_after_essentials - emergency_fund_contribution
            investment_contribution = max(0, remaining_disposable * scenario["savings_rate"])

            # Investment growth (compound annually on the *previous* year's portfolio + new contributions)
            investment_portfolio += investment_contribution # Add contributions first
            investment_growth = investment_portfolio * scenario["investment_return_rate"] # Then calculate growth
            investment_portfolio += investment_growth


            annual_total_savings = emergency_fund_contribution + investment_contribution
            total_saved += annual_total_savings
            net_worth = liquid_savings + investment_portfolio - debt_balance

            year_data.update({
                "major_expenses_paid": major_expense_this_year,
                "emergency_fund_contribution": emergency_fund_contribution,
                "investment_contribution": investment_contribution,
                "investment_growth": investment_growth,
                "total_annual_savings": annual_total_savings,
                "liquid_savings_eoy": liquid_savings,
                "investment_portfolio_eoy": investment_portfolio,
                "debt_balance_eoy": debt_balance,
                "net_worth_eoy": net_worth
            })
            yearly_data.append(year_data)

        fi_target = 0
        fi_year_data = None
        if yearly_data: # Check if simulation ran
            final_year_annual_expenses = yearly_data[-1]["living_expenses"] # Use last year's expenses
            withdrawal_rate = 0.04  # 4% rule
            fi_target = final_year_annual_expenses / withdrawal_rate

            for y_data in yearly_data:
                if y_data["investment_portfolio_eoy"] >= fi_target:
                    fi_year_data = y_data
                    break

        return {
            "yearly_data": yearly_data,
            "summary": {
                "total_earned_gross": total_earned_gross,
                "total_taxes_paid": total_taxes_paid,
                "total_saved": total_saved,
                "total_spent_living": total_spent_living,
                "total_spent_major": total_spent_major,
                "final_net_worth": net_worth,
                "final_age": age + years -1 if years > 0 else age,
                "final_liquid_savings": liquid_savings,
                "final_investment_portfolio": investment_portfolio,
                "final_remaining_debt": debt_balance,
                "fi_target": fi_target,
                "fi_achieved": fi_year_data is not None,
                "fi_age": fi_year_data["age"] if fi_year_data else None,
                "fi_year": fi_year_data["year"] if fi_year_data else None
            }
        }


def main():
    st.markdown('<h1 class="main-header">💰 Personal Economic Model</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #555;">Life Decision Simulator - Make Informed Financial Choices</p>', unsafe_allow_html=True)

    if 'simulator' not in st.session_state:
        st.session_state.simulator = FinancialSimulator()

    st.sidebar.title("📊 Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["🏠 Dashboard", "➕ Create Scenario", "📈 Analyze Scenario", "⚖️ Compare Scenarios", "📋 Manage Scenarios"]
    )

    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "➕ Create Scenario":
        show_create_scenario()
    elif page == "📈 Analyze Scenario":
        show_analyze_scenario()
    elif page == "⚖️ Compare Scenarios":
        show_compare_scenarios()
    elif page == "📋 Manage Scenarios":
        show_manage_scenarios()

def show_dashboard():
    st.header("📊 Financial Scenarios Dashboard")
    scenarios = st.session_state.simulator.get_scenarios()

    if not scenarios:
        st.info("👋 Welcome! Create your first financial scenario to get started.")
        st.markdown("""
        ### What is this tool?
        This Personal Economic Model helps you:
        - 🎯 **Compare life paths** - See how different career choices affect your wealth.
        - 📈 **Visualize compound interest** - Watch your money grow over decades.
        - 🏆 **Find optimal strategies** - Discover which decisions create the biggest impact.
        - 🚀 **Plan for financial independence** - Know when you can retire comfortably.
        
        ### Quick Start Guide:
        1. Click "➕ Create Scenario" in the sidebar to model your first life path.
        2. Add details like salary, expenses, and major purchases.
        3. Go to "📈 Analyze Scenario" to run simulations and see your financial future.
        4. Compare different scenarios in "⚖️ Compare Scenarios" to make informed decisions.
        5. Manage your saved scenarios in "📋 Manage Scenarios".
        """)
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Scenarios", len(scenarios))
    if scenarios: # Check if scenarios list is not empty before calculating averages
        with col2:
            avg_starting_salary = sum(s["starting_salary"] for s in scenarios) / len(scenarios)
            st.metric("Avg. Starting Salary", f"${avg_starting_salary:,.0f}")
        with col3:
            avg_savings_rate = sum(s["savings_rate"] for s in scenarios) / len(scenarios) * 100
            st.metric("Avg. Savings Rate", f"{avg_savings_rate:.1f}%")

    st.subheader("📋 Your Scenarios Overview")
    scenario_df_data = []
    for s in scenarios:
        scenario_df_data.append({
            "ID": s.get("id", "N/A"), # Display ID
            "Scenario Name": s["name"],
            "Starting Salary": f"${s['starting_salary']:,.0f}",
            "Savings Rate": f"{s['savings_rate']*100:.1f}%",
            "Created": s.get("created_date", "Unknown")[:10] # Show only date part
        })
    if scenario_df_data:
        scenario_df = pd.DataFrame(scenario_df_data)
        st.dataframe(scenario_df, use_container_width=True, hide_index=True) # Hide pandas index
    else:
        st.write("No scenarios to display yet.")


def show_create_scenario():
    st.header("➕ Create New Financial Scenario")
    with st.form("create_scenario_form"):
        st.subheader("🎯 Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Scenario Name*", placeholder="e.g., Software Engineer Path")
            starting_age = st.number_input("Current Age*", min_value=18, max_value=70, value=22, step=1)
            starting_salary = st.number_input("Starting Annual Gross Salary ($)*", min_value=0, value=60000, step=1000)
        with col2:
            salary_growth_rate = st.number_input("Annual Salary Growth Rate (%)*", min_value=0.0, max_value=25.0, value=3.0, step=0.1) / 100
            monthly_expenses = st.number_input("Current Monthly Living Expenses ($)*", min_value=0, value=2500, step=100)
            savings_rate = st.number_input("Target Savings Rate (of after-tax, after-essentials income) (%)*", min_value=0.0, max_value=100.0, value=20.0, step=1.0) / 100

        st.subheader("📈 Investment & Finance")
        col1, col2 = st.columns(2)
        with col1:
            investment_return_rate = st.number_input("Expected Annual Investment Return Rate (%)*", min_value=0.0, max_value=20.0, value=7.0, step=0.1) / 100
        with col2:
            student_debt = st.number_input("Current Student Debt Balance ($)", min_value=0, value=0, step=1000)

        st.subheader("💸 Major Future Expenses (Optional)")
        st.markdown("*Add significant one-time purchases like a car, house down payment, wedding, etc.*")
        if 'num_major_expenses' not in st.session_state:
            st.session_state.num_major_expenses = 0

        def add_major_expense():
            st.session_state.num_major_expenses += 1
        def remove_major_expense():
            if st.session_state.num_major_expenses > 0:
                st.session_state.num_major_expenses -= 1
        
        col_add_exp, col_rem_exp = st.columns(2)
        with col_add_exp:
            st.button("Add Major Expense Item", on_click=add_major_expense, key="add_major_exp_btn")
        with col_rem_exp:
            st.button("Remove Last Major Expense", on_click=remove_major_expense, key="rem_major_exp_btn", disabled=st.session_state.num_major_expenses == 0)

        major_expenses_list = []
        for i in range(st.session_state.num_major_expenses):
            st.markdown(f"--- **Major Expense {i+1}** ---")
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            name_exp = exp_col1.text_input(f"Expense Name", key=f"maj_exp_name_{i}")
            amount_exp = exp_col2.number_input(f"Amount ($)", key=f"maj_exp_amount_{i}", min_value=0, step=1000)
            year_exp = exp_col3.number_input(f"Year from Start (1 = first year)", key=f"maj_exp_year_{i}", min_value=1, step=1)
            if name_exp and amount_exp > 0:
                major_expenses_list.append({"name": name_exp, "amount": amount_exp, "year": year_exp -1}) # 0-indexed

        st.subheader("🚀 Future Career Changes (Optional)")
        st.markdown("*Model promotions, career switches, or significant salary jumps.*")
        if 'num_career_changes' not in st.session_state:
            st.session_state.num_career_changes = 0

        def add_career_change():
            st.session_state.num_career_changes += 1
        def remove_career_change():
            if st.session_state.num_career_changes > 0:
                st.session_state.num_career_changes -=1

        col_add_career, col_rem_career = st.columns(2)
        with col_add_career:
            st.button("Add Career Change Item", on_click=add_career_change, key="add_career_btn")
        with col_rem_career:
            st.button("Remove Last Career Change", on_click=remove_career_change, key="rem_career_btn", disabled=st.session_state.num_career_changes == 0)
        
        career_changes_list = []
        for i in range(st.session_state.num_career_changes):
            st.markdown(f"--- **Career Change {i+1}** ---")
            car_col1, car_col2, car_col3 = st.columns(3)
            year_chg = car_col1.number_input(f"Year of Change (1 = first year)", key=f"car_chg_year_{i}", min_value=1, step=1)
            new_salary_chg = car_col2.number_input(f"New Annual Gross Salary ($)", key=f"car_chg_salary_{i}", min_value=0, step=1000)
            new_growth_chg = car_col3.number_input(f"New Salary Growth Rate (%)", key=f"car_chg_growth_{i}", min_value=0.0, max_value=25.0, step=0.1) / 100
            if new_salary_chg > 0:
                career_changes_list.append({"year": year_chg -1, "new_salary": new_salary_chg, "new_growth_rate": new_growth_chg}) # 0-indexed

        submitted = st.form_submit_button("💾 Create Scenario", type="primary")
        if submitted:
            if not name.strip():
                st.error("Scenario Name is required.")
            else:
                scenario_data = {
                    "name": name, "starting_age": starting_age, "starting_salary": starting_salary,
                    "salary_growth_rate": salary_growth_rate, "monthly_expenses": monthly_expenses,
                    "savings_rate": savings_rate, "investment_return_rate": investment_return_rate,
                    "student_debt": student_debt, "major_expenses": major_expenses_list,
                    "career_changes": career_changes_list
                }
                st.session_state.simulator.add_scenario(scenario_data)
                st.success(f"✅ Scenario '{name}' created successfully!")
                st.balloons()
                # Reset item counts for next form
                st.session_state.num_major_expenses = 0
                st.session_state.num_career_changes = 0
                st.rerun() # To clear the dynamic fields properly

def show_analyze_scenario():
    st.header("📈 Scenario Analysis")
    scenarios = st.session_state.simulator.get_scenarios()
    if not scenarios:
        st.warning("No scenarios available. Please create one first in '➕ Create Scenario'.")
        return

    scenario_options = {s["name"]: s["id"] for s in scenarios}
    selected_name = st.selectbox("Select scenario to analyze:", list(scenario_options.keys()))

    if selected_name:
        selected_id = scenario_options[selected_name]
        selected_scenario = st.session_state.simulator.get_scenario_by_id(selected_id)

        st.subheader(f"🔬 Analyzing: {selected_scenario['name']}")
        
        with st.expander("🔧 Simulation Parameters", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                years = st.slider("Simulation Years", min_value=5, max_value=60, value=30, step=1, key=f"sim_years_{selected_id}")
            with col2:
                inflation_rate = st.slider("Assumed Annual Inflation Rate (%)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key=f"sim_inf_{selected_id}") / 100
            with col3:
                tax_rate = st.slider("Assumed Average Tax Rate (%)", min_value=0.0, max_value=50.0, value=20.0, step=0.5, key=f"sim_tax_{selected_id}") / 100

        if st.button("🚀 Run Analysis", type="primary", key=f"run_analysis_{selected_id}"):
            with st.spinner("🧙‍♂️ Crunching the numbers for your future..."):
                results = st.session_state.simulator.simulate_scenario(
                    selected_scenario, years=years, inflation_rate=inflation_rate, tax_rate=tax_rate
                )
            show_analysis_results(results, selected_scenario, years)

def show_analysis_results(results, scenario_data, years_simulated):
    summary = results["summary"]
    yearly_df = pd.DataFrame(results["yearly_data"])

    st.markdown("---")
    st.subheader(f"🎯 Financial Snapshot after {years_simulated} years (Age {summary['final_age']})")

    cols = st.columns(4)
    cols[0].metric("Final Net Worth", f"${summary['final_net_worth']:,.0f}", help="Total assets minus liabilities.")
    cols[1].metric("Total Gross Earned", f"${summary['total_earned_gross']:,.0f}")
    cols[2].metric("Total Saved (Invested)", f"${summary['total_saved']:,.0f}")
    
    if summary['fi_achieved']:
        cols[3].metric("Financial Independence", f"Age {summary['fi_age']}", delta="Achieved!", help=f"Target: ${summary['fi_target']:,.0f}")
    else:
        cols[3].metric("Financial Independence", "Not Reached", delta_color="inverse", help=f"Target: ${summary['fi_target']:,.0f}")

    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Charts", "💰 Financial Summary", "📅 Milestones", "🗓️ Yearly Data"])

    with tab1:
        st.subheader("📈 Visual Projections")
        # Net Worth and Components Over Time
        fig_nw = go.Figure()
        fig_nw.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['net_worth_eoy'], mode='lines', name='Net Worth', line=dict(color='#1f77b4', width=3)))
        fig_nw.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['investment_portfolio_eoy'], mode='lines', name='Investment Portfolio', line=dict(color='#2ca02c')))
        fig_nw.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['liquid_savings_eoy'], mode='lines', name='Liquid Savings (Emergency)', line=dict(color='#ff7f0e')))
        if scenario_data.get("student_debt", 0) > 0:
             fig_nw.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['debt_balance_eoy'], mode='lines', name='Remaining Debt', line=dict(color='#d62728', dash='dot')))
        fig_nw.update_layout(title='Net Worth and Components Over Time', xaxis_title='Age', yaxis_title='Amount ($)')
        st.plotly_chart(fig_nw, use_container_width=True)

        # Income vs Expenses
        fig_inc_exp = go.Figure()
        fig_inc_exp.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['after_tax_income'], mode='lines', name='After-Tax Income', line=dict(color='green')))
        fig_inc_exp.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['living_expenses'], mode='lines', name='Living Expenses (Infl. Adj.)', line=dict(color='red')))
        fig_inc_exp.add_trace(go.Scatter(x=yearly_df['age'], y=yearly_df['total_annual_savings'], mode='lines', name='Total Annual Savings', line=dict(color='purple')))
        fig_inc_exp.update_layout(title='Annual Income, Expenses, and Savings', xaxis_title='Age', yaxis_title='Amount ($)')
        st.plotly_chart(fig_inc_exp, use_container_width=True)
        
    with tab2:
        st.subheader("💰 Financial Summary Details")
        st.markdown(f"""
        - **Total Gross Income Earned:** ${summary['total_earned_gross']:,.0f}
        - **Total Taxes Paid (Estimate):** ${summary['total_taxes_paid']:,.0f}
        - **Total Spent on Living Expenses:** ${summary['total_spent_living']:,.0f}
        - **Total Spent on Major Purchases:** ${summary['total_spent_major']:,.0f}
        - **Total Amount Saved & Invested:** ${summary['total_saved']:,.0f}
        - **Final Liquid Savings (Emergency Fund):** ${summary['final_liquid_savings']:,.0f}
        - **Final Investment Portfolio Value:** ${summary['final_investment_portfolio']:,.0f}
        - **Final Remaining Debt:** ${summary['final_remaining_debt']:,.0f}
        """)
        st.markdown(f"""
        #### Financial Independence (FI)
        - **FI Target (Investments needed for 4% withdrawal):** ${summary['fi_target']:,.0f}
        - **FI Achieved:** {'Yes' if summary['fi_achieved'] else 'No'}
        - **Age at FI:** {summary['fi_age'] if summary['fi_achieved'] else 'N/A'}
        - **Year of FI:** {summary['fi_year'] if summary['fi_achieved'] else 'N/A'}
        """)

    with tab3:
        st.subheader("📅 Financial Milestones Reached")
        milestones = [10000, 50000, 100000, 250000, 500000, 750000, 1000000, 1500000, 2000000, 5000000]
        milestone_data = []
        achieved_milestones = set()

        for m_val in milestones:
            for _, row in yearly_df.iterrows():
                if row["net_worth_eoy"] >= m_val and m_val not in achieved_milestones:
                    milestone_data.append({
                        "Net Worth Milestone": f"${m_val:,.0f}",
                        "Achieved at Age": row["age"],
                        "Year of Simulation": row["year"]
                    })
                    achieved_milestones.add(m_val)
                    break
        if milestone_data:
            st.dataframe(pd.DataFrame(milestone_data), hide_index=True, use_container_width=True)
        else:
            st.write("No major milestones reached in this simulation timeframe or for these amounts.")

    with tab4:
        st.subheader("🗓️ Detailed Year-by-Year Data")
        display_df = yearly_df[[
            "year", "age", "gross_salary", "after_tax_income", "living_expenses",
            "major_expenses_paid", "debt_payment", "total_annual_savings",
            "investment_portfolio_eoy", "net_worth_eoy", "events"
        ]].copy() # Create a copy to avoid SettingWithCopyWarning

        # Format monetary columns
        money_cols = ["gross_salary", "after_tax_income", "living_expenses", "major_expenses_paid", "debt_payment", "total_annual_savings", "investment_portfolio_eoy", "net_worth_eoy"]
        for col in money_cols:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
        
        # Convert events list to string
        display_df["events"] = display_df["events"].apply(lambda x: ", ".join(x) if x else "-")

        st.dataframe(display_df, height=400, use_container_width=True, hide_index=True)

def show_compare_scenarios():
    st.header("⚖️ Scenario Comparison")
    scenarios = st.session_state.simulator.get_scenarios()
    if len(scenarios) < 2:
        st.warning("You need at least 2 scenarios to compare. Please create more first.")
        return

    scenario_options = {s["name"]: s["id"] for s in scenarios}
    
    col1, col2 = st.columns(2)
    with col1:
        name1 = st.selectbox("Select First Scenario:", list(scenario_options.keys()), key="compare_s1_name")
        id1 = scenario_options[name1]
    with col2:
        available_s2 = {name: id_val for name, id_val in scenario_options.items() if id_val != id1}
        if not available_s2:
            st.warning("Only one scenario available. Cannot compare.")
            return
        name2 = st.selectbox("Select Second Scenario:", list(available_s2.keys()), key="compare_s2_name")
        id2 = available_s2[name2]

    st.markdown("---")
    st.subheader("🔧 Comparison Parameters")
    comp_years = st.slider("Simulation Years for Comparison", min_value=5, max_value=60, value=30, step=1, key="comp_years")
    comp_inflation = st.slider("Assumed Annual Inflation Rate (%)", min_value=0.0, max_value=10.0, value=2.5, step=0.1, key="comp_inf") / 100
    comp_tax = st.slider("Assumed Average Tax Rate (%)", min_value=0.0, max_value=50.0, value=20.0, step=0.5, key="comp_tax") / 100

    if st.button("🔍 Compare Scenarios Now", type="primary", key="run_comparison_btn"):
        scenario1_data = st.session_state.simulator.get_scenario_by_id(id1)
        scenario2_data = st.session_state.simulator.get_scenario_by_id(id2)

        with st.spinner(f"Comparing '{name1}' vs '{name2}'..."):
            res1 = st.session_state.simulator.simulate_scenario(scenario1_data, years=comp_years, inflation_rate=comp_inflation, tax_rate=comp_tax)
            res2 = st.session_state.simulator.simulate_scenario(scenario2_data, years=comp_years, inflation_rate=comp_inflation, tax_rate=comp_tax)
        
        show_comparison_results(res1, res2, name1, name2, comp_years)

def show_comparison_results(res1, res2, name1, name2, years):
    sum1, sum2 = res1["summary"], res2["summary"]
    yearly1_df, yearly2_df = pd.DataFrame(res1["yearly_data"]), pd.DataFrame(res2["yearly_data"])

    st.markdown("---")
    st.subheader(f"🏆 Comparison: {name1} vs {name2} (after {years} years)")

    cols_comp = st.columns(3)
    with cols_comp[0]:
        st.markdown(f"**{name1}**")
        st.metric("Final Net Worth", f"${sum1['final_net_worth']:,.0f}")
        st.metric("FI Age", f"{sum1['fi_age'] if sum1['fi_achieved'] else 'N/A'}")
    with cols_comp[1]:
        st.markdown(f"**{name2}**")
        st.metric("Final Net Worth", f"${sum2['final_net_worth']:,.0f}")
        st.metric("FI Age", f"{sum2['fi_age'] if sum2['fi_achieved'] else 'N/A'}")
    with cols_comp[2]:
        st.markdown("**Difference**")
        nw_diff = sum1['final_net_worth'] - sum2['final_net_worth']
        st.metric("Net Worth Diff.", f"${nw_diff:,.0f}", delta=f"{name1} vs {name2}")
        
        fi_age1_val = sum1['fi_age'] if sum1['fi_achieved'] else float('inf')
        fi_age2_val = sum2['fi_age'] if sum2['fi_achieved'] else float('inf')
        fi_age_diff_val = fi_age1_val - fi_age2_val
        if fi_age1_val == float('inf') and fi_age2_val == float('inf'):
             st.metric("FI Age Diff.", "N/A")
        elif fi_age1_val == float('inf'):
            st.metric("FI Age Diff.", f"{name2} by >{years - (sum2.get('final_age',0)-sum2.get('fi_age',0))} yrs", delta_color="inverse")
        elif fi_age2_val == float('inf'):
            st.metric("FI Age Diff.", f"{name1} by >{years - (sum1.get('final_age',0)-sum1.get('fi_age',0))} yrs")
        else:
            st.metric("FI Age Diff.", f"{fi_age_diff_val:.0f} years", delta=f"{name1} vs {name2}")


    fig_comp_nw = go.Figure()
    fig_comp_nw.add_trace(go.Scatter(x=yearly1_df['age'], y=yearly1_df['net_worth_eoy'], name=name1, line=dict(width=3)))
    fig_comp_nw.add_trace(go.Scatter(x=yearly2_df['age'], y=yearly2_df['net_worth_eoy'], name=name2, line=dict(width=3, dash='dash')))
    fig_comp_nw.update_layout(title='Net Worth Growth Comparison', xaxis_title='Age', yaxis_title='Net Worth ($)')
    st.plotly_chart(fig_comp_nw, use_container_width=True)

    st.subheader("📊 Detailed Metrics Comparison")
    comp_data = {
        "Metric": ["Final Net Worth", "Total Gross Earned", "Total Saved", "FI Age (if achieved)", "FI Target"],
        name1: [f"${sum1['final_net_worth']:,.0f}", f"${sum1['total_earned_gross']:,.0f}", f"${sum1['total_saved']:,.0f}", sum1['fi_age'] if sum1['fi_achieved'] else "N/A", f"${sum1['fi_target']:,.0f}"],
        name2: [f"${sum2['final_net_worth']:,.0f}", f"${sum2['total_earned_gross']:,.0f}", f"${sum2['total_saved']:,.0f}", sum2['fi_age'] if sum2['fi_achieved'] else "N/A", f"${sum2['fi_target']:,.0f}"]
    }
    st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)

def show_manage_scenarios():
    st.header("📋 Manage Financial Scenarios")
    scenarios = st.session_state.simulator.get_scenarios()

    if not scenarios:
        st.info("No scenarios to manage yet. Create some first!")
        return

    st.write(f"You have **{len(scenarios)}** saved scenario(s).")
    
    for scenario in scenarios:
        with st.expander(f"{scenario['name']} (ID: {scenario.get('id', 'N/A')[:8]}...) - Created: {scenario.get('created_date', 'Unknown')[:10]}"):
            st.write(f"**Starting Salary:** ${scenario['starting_salary']:,}")
            st.write(f"**Monthly Expenses:** ${scenario['monthly_expenses']:,}")
            st.write(f"**Savings Rate:** {scenario['savings_rate']*100:.1f}%")
            st.write(f"**Investment Return:** {scenario['investment_return_rate']*100:.1f}%")
            if scenario.get("student_debt", 0) > 0:
                st.write(f"**Student Debt:** ${scenario['student_debt']:,}")
            
            if st.button("❌ Delete Scenario", key=f"delete_{scenario.get('id')}", type="secondary"):
                confirm_delete = st.checkbox(f"Confirm deletion of '{scenario['name']}'", key=f"confirm_delete_{scenario.get('id')}")
                if confirm_delete:
                    st.session_state.simulator.delete_scenario(scenario.get("id"))
                    st.success(f"Scenario '{scenario['name']}' deleted successfully.")
                    st.rerun() # To refresh the list
                elif st.session_state.get(f"delete_{scenario.get('id')}_clicked", False) and not confirm_delete: # If button clicked but not confirmed
                     st.warning("Deletion not confirmed.")
                st.session_state[f"delete_{scenario.get('id')}_clicked"] = True # Track button click

if __name__ == "__main__":
    main()
