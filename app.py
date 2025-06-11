import streamlit as st
import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import List, Dict, Optional, Union # For type hinting

# --- Configuration and Setup ---
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
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Data File Paths ---
SCENARIO_DATA_FILE = "financial_scenarios.json"
GOALS_DATA_FILE = "financial_goals.json"
EXPENSES_DATA_FILE = "monthly_expenses.json"
NET_WORTH_HISTORY_FILE = "net_worth_history.json"

# --- Data Management Classes/Functions ---

class DataManager:
    """Handles loading and saving of various data files."""
    def __init__(self, file_path, default_content_key="items"):
        self.file_path = file_path
        self.default_content_key = default_content_key

    def load(self) -> Dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {self.default_content_key: []}
        return {self.default_content_key: []}

    def save(self, data: Dict):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)

# Instantiate data managers
scenario_manager = DataManager(SCENARIO_DATA_FILE, "scenarios")
goals_manager = DataManager(GOALS_DATA_FILE, "goals")
expenses_manager = DataManager(EXPENSES_DATA_FILE, "expenses")
net_worth_manager = DataManager(NET_WORTH_HISTORY_FILE, "history")

# --- Financial Simulator Core Logic (similar to before, but now calls DataManager) ---

class FinancialSimulator:
    def __init__(self):
        self.data = scenario_manager.load()
    
    def save_data(self):
        scenario_manager.save(self.data)
    
    def add_scenario(self, scenario_data: Dict):
        # Assign a unique ID if not already present (for editing)
        if "id" not in scenario_data:
             # Find max ID and add +1, or start from 1 if no scenarios
            latest_id = max([s.get("id", 0) for s in self.data["scenarios"]]) if self.data["scenarios"] else 0
            scenario_data["id"] = latest_id + 1
        
        scenario_data["created_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If editing, replace existing scenario; otherwise, append
        if any(s.get("id") == scenario_data["id"] for s in self.data["scenarios"]):
            self.data["scenarios"] = [s if s.get("id") != scenario_data["id"] else scenario_data for s in self.data["scenarios"]]
        else:
            self.data["scenarios"].append(scenario_data)

        self.save_data()
    
    def get_scenarios(self) -> List[Dict]:
        return self.data["scenarios"]
    
    def get_scenario_by_id(self, scenario_id: int) -> Optional[Dict]:
        for scenario in self.data["scenarios"]:
            if scenario.get("id") == scenario_id:
                return scenario
        return None
    
    def delete_scenario(self, scenario_id: int):
        self.data["scenarios"] = [s for s in self.data["scenarios"] if s.get("id") != scenario_id]
        self.save_data()
    
    def simulate_scenario(self, scenario: Dict, years: int = 30, inflation_rate: float = 0.03, tax_rate: float = 0.25) -> Dict:
        # Initialize tracking variables
        age = scenario["starting_age"]
        current_salary = scenario["starting_salary"]
        current_growth_rate = scenario["salary_growth_rate"]
        net_worth = 0
        liquid_savings = 0
        investment_portfolio = 0
        total_earned = 0
        total_saved = 0
        total_spent = 0
        total_taxes = 0
        debt_balance = scenario.get("student_debt", 0)
        
        yearly_data = [] # Stores detailed data for each year
        monthly_expenses_base = scenario["monthly_expenses"]
        
        for year in range(years):
            year_data_entry = {
                "year_idx": year, # 0-indexed year for calculations
                "year_display": year + 1, # 1-indexed for display
                "age": age + year,
                "events": [] # Store significant events happening this year
            }
            
            # Apply career changes
            for change in scenario.get("career_changes", []):
                if change["year"] == year: # change["year"] is 0-indexed in stored data
                    current_salary = change["new_salary"]
                    current_growth_rate = change["new_growth_rate"]
                    year_data_entry["events"].append(f"Career change to ${current_salary:,.0f} (Growth: {current_growth_rate*100:.1f}%)")
            
            # Calculate inflation-adjusted expenses
            inflation_multiplier = (1 + inflation_rate) ** year
            monthly_expenses_adjusted = monthly_expenses_base * inflation_multiplier
            annual_living_expenses = monthly_expenses_adjusted * 12
            
            # Calculate annual income with current growth rate
            # Note: current_salary updates with career changes, then that new salary grows
            annual_income = current_salary * (1 + current_growth_rate) ** year
            
            # Calculate taxes
            annual_taxes = annual_income * tax_rate # Simplified flat tax rate
            after_tax_income = annual_income - annual_taxes
            
            year_data_entry.update({
                "gross_salary": annual_income,
                "taxes": annual_taxes,
                "after_tax_income": after_tax_income,
                "living_expenses_inflation_adj": annual_living_expenses,
                "inflation_multiplier": inflation_multiplier
            })
            
            total_earned += annual_income
            total_taxes += annual_taxes
            total_spent += annual_living_expenses
            
            # Handle major expenses
            major_expense_this_year = 0
            for expense in scenario.get("major_expenses", []):
                if expense["year"] == year: # expense["year"] is 0-indexed
                    # Adjust for inflation
                    adjusted_expense_amount = expense["amount"] * inflation_multiplier
                    major_expense_this_year += adjusted_expense_amount
                    year_data_entry["events"].append(f"{expense['name']}: -${adjusted_expense_amount:,.0f}")
            
            total_spent += major_expense_this_year
            
            # Handle debt payments (e.g., student loans)
            debt_payment_this_year = 0
            if debt_balance > 0 and scenario.get("student_debt",0) > 0:
                # Simple amortization: assume debt is repaid over 10 fixed years (or until paid off)
                fixed_annual_debt_payment = scenario["student_debt"] / 10 # This is a simplification
                debt_payment_this_year = min(fixed_annual_debt_payment, debt_balance)
                debt_balance -= debt_payment_this_year
                debt_balance = max(0, debt_balance) # Ensure debt doesn't go negative
                year_data_entry["events"].append(f"Debt Payment: -${debt_payment_this_year:,.0f} (Remaining: ${debt_balance:,.0f})")

            # Calculate available funds for savings after all deductions
            available_for_savings = after_tax_income - annual_living_expenses - major_expense_this_year - debt_payment_this_year
            
            # Emergency fund logic: try to build up 6 months of living expenses first
            emergency_fund_target = monthly_expenses_adjusted * 6 
            emergency_fund_contribution = 0
            
            if liquid_savings < emergency_fund_target and available_for_savings > 0:
                # Prioritize building emergency fund with an aggressive portion of available funds
                emergency_fund_contribution = min(available_for_savings * 0.5, emergency_fund_target - liquid_savings)
                liquid_savings += emergency_fund_contribution
                available_for_savings -= emergency_fund_contribution
            
            # Investment contributions based on the user's savings rate
            # Only invest after emergency fund contribution (if emergency fund target not met yet)
            investment_contribution = max(0, available_for_savings * scenario["savings_rate"])
            
            # Investment growth (compound annually) from the existing portfolio
            investment_growth_this_year = investment_portfolio * scenario["investment_return_rate"]
            investment_portfolio += investment_contribution + investment_growth_this_year
            
            # Total savings tracked (sum of emergency fund and investment contributions)
            annual_total_savings = emergency_fund_contribution + investment_contribution
            total_saved += annual_total_savings
            net_worth = liquid_savings + investment_portfolio - debt_balance
            
            year_data_entry.update({
                "monthly_expenses_base": monthly_expenses_base,
                "monthly_expenses_display": monthly_expenses_adjusted,
                "major_expenses_this_year": major_expense_this_year,
                "debt_payment_this_year": debt_payment_this_year,
                "emergency_fund_target": emergency_fund_target,
                "emergency_fund_contrib": emergency_fund_contribution,
                "investment_contrib": investment_contribution,
                "investment_growth_this_year": investment_growth_this_year,
                "annual_total_savings": annual_total_savings,
                "liquid_savings_total": liquid_savings,
                "investment_portfolio_total": investment_portfolio,
                "debt_balance_current": debt_balance,
                "net_worth": net_worth
            })
            
            yearly_data.append(year_data_entry)
        
        # Calculate financial independence (FI) metrics
        # Using the 4% rule (safe withdrawal rate)
        current_year_expenses = yearly_data[years-1]['living_expenses_inflation_adj'] # Last year's expenses
        fi_target = current_year_expenses / 0.04 if current_year_expenses > 0 else 0
        
        fi_age = None
        fi_year_achieved = None
        for i, year_data_entry in enumerate(yearly_data):
            if year_data_entry["investment_portfolio_total"] >= fi_target:
                fi_age = year_data_entry["age"]
                fi_year_achieved = year_data_entry["year_display"]
                break
        
        return {
            "yearly_data": yearly_data,
            "summary": {
                "total_earned": total_earned,
                "total_taxes": total_taxes,
                "total_saved": total_saved,
                "total_spent": total_spent,
                "final_net_worth": net_worth,
                "final_age": age + years,
                "liquid_savings_final": liquid_savings,
                "investment_portfolio_final": investment_portfolio,
                "remaining_debt_final": debt_balance,
                "fi_target": fi_target,
                "fi_achieved": fi_age is not None,
                "fi_age": fi_age,
                "fi_year_achieved": fi_year_achieved
            }
        }

# --- Streamlit UI Pages ---

def show_dashboard():
    """Dashboard showing overview of all scenarios and general app info."""
    st.header("📊 Financial Scenarios Dashboard")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.info("👋 Welcome! Create your first financial scenario to get started.")
        st.markdown("""
        ### What is this tool?
        This **Personal Economic Model & Life Decision Simulator** is your secret weapon for understanding your financial future. It helps you:
        - 🎯 **Compare life paths** - See how different career choices, expenses, and savings affect your wealth over decades.
        - 📈 **Visualize compound interest** - Watch your money grow (or shrink!) in interactive charts.
        - 🏆 **Find optimal strategies** - Discover which decisions create the biggest impact on your net worth and financial independence.
        - 🚀 **Plan for financial independence** - Know when you can comfortably retire or achieve financial freedom.
        - 🗂️ **Track your goals, expenses, and net worth** - Get a holistic view of your finances.
        
        ### Quick Start Guide:
        1. Click "➕ **Create Scenario**" to model a potential life path (e.g., "Software Engineer, High Savings").
        2. Go to "📈 **Analyze Scenario**" to see detailed projections for your chosen path.
        3. Use "⚖️ **Compare Scenarios**" to weigh the financial outcomes of different life choices.
        4. Visit "💰 **Goals Tracker**", "💸 **Expenses Tracker**", or "📉 **Net Worth Tracker**" to manage your daily finances.
        """)
        return
    
    # Quick stats for all scenarios
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scenarios", len(scenarios))
    with col2:
        avg_starting_salary = sum(s["starting_salary"] for s in scenarios) / len(scenarios) if scenarios else 0
        st.metric("Avg Starting Salary", f"${avg_starting_salary:,.0f}")
    with col3:
        avg_savings_rate = sum(s["savings_rate"] for s in scenarios) / len(scenarios) * 100 if scenarios else 0
        st.metric("Avg Savings Rate", f"{avg_savings_rate:.1f}%")
    with col4:
        recent_scenario = max(scenarios, key=lambda x: x.get("created_date", "")) if scenarios else {"name": "N/A", "created_date": ""}
        st.metric("Latest Scenario", recent_scenario["name"][:15] + "..." if recent_scenario["name"] else "N/A")
    
    # Scenarios overview table
    st.subheader("📋 Your Scenarios Overview")
    
    # Ensure all required keys exist for the DataFrame construction
    scenario_data_for_df = []
    for s in scenarios:
        row = {
            "ID": s.get("id"),
            "Scenario Name": s.get("name", "N/A"),
            "Start $:": f"${s.get('starting_salary', 0):,}",
            "Monthly Exp $:": f"${s.get('monthly_expenses', 0):,}",
            "Savings Rate %": f"{s.get('savings_rate', 0)*100:.1f}%",
            "Salary Growth %": f"{s.get('salary_growth_rate', 0)*100:.1f}%",
            "Invest Return %": f"{s.get('investment_return_rate', 0)*100:.1f}%",
            "Created": s.get("created_date", "Unknown")[:10]
        }
        scenario_data_for_df.append(row)

    if scenario_data_for_df:
        scenario_df = pd.DataFrame(scenario_data_for_df)
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)
    else:
        st.info("No scenarios to display. Create one using the 'Create Scenario' tab!")

def show_create_scenario():
    """Interface for creating or editing new financial scenarios."""
    
    if 'editing_scenario_id' not in st.session_state:
        st.session_state.editing_scenario_id = None

    if st.session_state.editing_scenario_id:
        st.header("📝 Edit Existing Scenario")
        scenario_to_edit = st.session_state.simulator.get_scenario_by_id(st.session_state.editing_scenario_id)
        if not scenario_to_edit:
            st.error("Scenario not found for editing.")
            st.session_state.editing_scenario_id = None # Clear invalid ID
            return
    else:
        st.header("➕ Create New Financial Scenario")
        scenario_to_edit = {} # Empty dict for new scenario

    # Use a unique key for the form reset behavior
    form_key = f"scenario_form_{st.session_state.editing_scenario_id}" if st.session_state.editing_scenario_id else "scenario_form_new"

    with st.form(key=form_key):
        st.subheader("🎯 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Scenario Name*", value=scenario_to_edit.get("name", ""), placeholder="e.g., Software Engineer Path, MBA Route")
            starting_age = st.number_input("Current Age*", min_value=18, max_value=65, value=scenario_to_edit.get("starting_age", 22))
            starting_salary = st.number_input("Starting Salary ($)*", min_value=0, value=scenario_to_edit.get("starting_salary", 60000), step=1000)
        
        with col2:
            salary_growth_rate = st.slider("Annual Salary Growth (%)*", 0.0, 20.0, scenario_to_edit.get("salary_growth_rate", 3.0)*100, 0.1) / 100
            monthly_expenses = st.number_input("Monthly Living Expenses ($)*", min_value=0, value=scenario_to_edit.get("monthly_expenses", 3000), step=100)
            savings_rate = st.slider("Savings Rate (%)*", 0.0, 100.0, scenario_to_edit.get("savings_rate", 15.0)*100, 1.0) / 100
        
        st.subheader("📈 Investment & Finance")
        col1, col2 = st.columns(2)
        with col1:
            investment_return_rate = st.slider("Expected Investment Return (%)*", 0.0, 20.0, scenario_to_edit.get("investment_return_rate", 7.0)*100, 0.1) / 100
        with col2:
            student_debt = st.number_input("Student Debt ($)", min_value=0, value=scenario_to_edit.get("student_debt", 0), step=1000)
        
        st.Divider()
        st.subheader("💸 Major Expenses (Optional)")
        st.markdown("*Add significant future purchases or expenses (e.g., Car, House Down Payment)*")
        
        # Load existing major expenses for editing or make a fresh list
        current_major_expenses = scenario_to_edit.get("major_expenses", [])
        num_expenses_initial = len(current_major_expenses) if current_major_expenses else 0
        num_expenses = st.number_input("Number of major expenses", min_value=0, max_value=10, value=num_expenses_initial, key="num_major_expenses")
        major_expenses = []
        
        for i in range(num_expenses):
            st.markdown(f"**Expense {i+1}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                expense_name = st.text_input(f"Name", key=f"expense_name_{i}", value=current_major_expenses[i].get("name", "") if i < num_expenses_initial else "", placeholder="e.g., Car, House Down Payment")
            with col2:
                expense_amount = st.number_input(f"Amount ($)", key=f"expense_amount_{i}", min_value=0, step=1000, value=current_major_expenses[i].get("amount", 0) if i < num_expenses_initial else 0)
            with col3:
                expense_year = st.number_input(f"Year (from start)", key=f"expense_year_{i}", min_value=1, max_value=50, value=current_major_expenses[i].get("year", 1)+1 if i < num_expenses_initial else 1) # Convert back to 1-indexed for display
            
            if expense_name and expense_amount > 0:
                major_expenses.append({
                    "name": expense_name,
                    "amount": expense_amount,
                    "year": expense_year - 1  # Convert to 0-indexed for internal simulation
                })
        
        st.Divider()
        st.subheader("🚀 Career Changes (Optional)")
        st.markdown("*Model promotions, career switches, or salary jumps*")
        
        # Load existing career changes for editing
        current_career_changes = scenario_to_edit.get("career_changes", [])
        num_changes_initial = len(current_career_changes) if current_career_changes else 0
        num_changes = st.number_input("Number of career changes", min_value=0, max_value=10, value=num_changes_initial, key="num_career_changes")
        career_changes = []
        
        for i in range(num_changes):
            st.markdown(f"**Career Change {i+1}**")
            col1, col2, col3 = st.columns(3)
            with col1:
                change_year = st.number_input(f"Year (from start)", key=f"change_year_{i}", min_value=1, max_value=50, value=current_career_changes[i].get("year", 5)+1 if i < num_changes_initial else 5) # Convert back
            with col2:
                new_salary = st.number_input(f"New Salary ($)", key=f"new_salary_{i}", min_value=0, step=1000, value=current_career_changes[i].get("new_salary", 0) if i < num_changes_initial else 0)
            with col3:
                new_growth_rate = st.slider(f"New Growth Rate (%)", 0.0, 20.0, current_career_changes[i].get("new_growth_rate", 3.0)*100 if i < num_changes_initial else 3.0, 0.1, key=f"new_growth_rate_{i}") / 100
                
            if new_salary > 0:
                career_changes.append({
                    "year": change_year - 1,  # Convert to 0-indexed for internal simulation
                    "new_salary": new_salary,
                    "new_growth_rate": new_growth_rate
                })
        
        # --- Form Submission ---
        submit_button_label = "🎯 Save Scenario" if st.session_state.editing_scenario_id else "🎯 Create Scenario"
        submitted = st.form_submit_button(submit_button_label, type="primary")
        
        if submitted:
            if not name:
                st.error("Please provide a scenario name.")
                return
            
            scenario_data = {
                "id": st.session_state.editing_scenario_id, # Preserve ID for editing
                "name": name,
                "starting_age": starting_age,
                "starting_salary": starting_salary,
                "salary_growth_rate": salary_growth_rate,
                "monthly_expenses": monthly_expenses,
                "savings_rate": savings_rate,
                "investment_return_rate": investment_return_rate,
                "student_debt": student_debt,
                "major_expenses": major_expenses,
                "career_changes": career_changes
            }
            
            st.session_state.simulator.add_scenario(scenario_data)
            success_message = f"✅ Scenario '{name}' updated successfully!" if st.session_state.editing_scenario_id else f"✅ Scenario '{name}' created successfully!"
            st.success(success_message)
            st.balloons()
            st.session_state.editing_scenario_id = None # Clear editing state after submission

def show_analyze_scenario():
    """Detailed analysis of a selected scenario."""
    st.header("📈 Scenario Analysis")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.warning("No scenarios available. Create a scenario first!")
        return
    
    # Scenario selection
    scenario_names = [s["name"] for s in scenarios if "name" in s]
    selected_name = st.selectbox("Select scenario to analyze:", scenario_names)
    
    selected_scenario = next((s for s in scenarios if s["name"] == selected_name), None)
    
    if selected_scenario is None:
        st.error("Selected scenario not found. Please create or refresh scenarios.")
        return

    # Analysis parameters
    col1, col2, col3 = st.columns(3)
    with col1:
        years = st.slider("Simulation Years", min_value=5, max_value=60, value=30, step=5)
    with col2:
        inflation_rate = st.slider("Inflation Rate (%)", min_value=0.0, max_value=10.0, value=3.0, step=0.1) / 100
    with col3:
        tax_rate = st.slider("Tax Rate (%)", min_value=0.0, max_value=50.0, value=25.0, step=1.0) / 100
    
    if st.button("🚀 Run Analysis", type="primary"):
        with st.spinner("Running comprehensive financial simulation..."):
            results = st.session_state.simulator.simulate_scenario(
                selected_scenario, years=years, inflation_rate=inflation_rate, tax_rate=tax_rate
            )
        
        # Display results
        _display_analysis_results(results, selected_scenario)

def _display_analysis_results(results: Dict, scenario: Dict):
    """Helper function to display comprehensive analysis results."""
    summary = results["summary"]
    yearly_data = results["yearly_data"]
    
    st.subheader(f"Results for '{scenario['name']}'")
    
    # Key metrics at the top
    st.subheader("🎯 Key Financial Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Final Net Worth",
            f"${summary['final_net_worth']:,.0f}",
            delta=f"Age {summary['final_age']}"
        )
    
    with col2:
        # Calculate ROI only if total_saved is positive to avoid division by zero
        roi = ((summary['final_net_worth'] - summary['total_saved']) / max(summary['total_saved'], 1)) * 100
        st.metric(
            "Overall Return on Investment",
            f"{roi:.1f}%",
            delta=f"${summary['final_net_worth'] - summary['total_saved']:,.0f} Growth"
        )
    
    with col3:
        # Calculate Lifetime Savings Rate safely
        lifetime_savings_rate = (summary['total_saved'] / summary['total_earned']) * 100 if summary['total_earned'] > 0 else 0
        st.metric(
            "Lifetime Savings Rate",
            f"{lifetime_savings_rate:.1f}%",
            delta=f"Saved: ${summary['total_saved']:,.0f}"
        )
    
    with col4:
        if summary['fi_achieved']:
            st.metric(
                "Financial Independence",
                f"Age {summary['fi_age']}",
                delta=f"🎉 Achieved in year {summary['fi_year_achieved']}!",
                delta_color="normal"
            )
        else:
            st.metric(
                "FI Target (4% Rule)",
                f"${summary['fi_target']:,.0f}",
                delta="Not reached by end of simulation",
                delta_color="off"
            )
    
    # Lifetime Financial Breakdown
    st.subheader("💰 Lifetime Financial Breakdown")
    
    breakdown_data = [
        {"Category": "Total Earned", "Amount": summary['total_earned']},
    ]
    # Add negative categories
    breakdown_data.append({"Category": "Taxes Paid", "Amount": -summary['total_taxes']})
    breakdown_data.append({"Category": "Total Spent", "Amount": -summary['total_spent']})
    # Add positive category (what's left)
    breakdown_data.append({"Category": "Net Worth (End)", "Amount": summary['final_net_worth']})
    
    breakdown_df = pd.DataFrame(breakdown_data)

    # Use waterfall chart for financial flow if amounts are significant
    if summary['total_earned'] > 0:
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Lifetime Flow",
            orientation = "v",
            measure = ["total", "relative", "relative", "total"], # "total" for earnings, "relative" for deductions, "total" for final net worth
            x = breakdown_df["Category"],
            textposition = "outside",
            text = [f"${val:,.0f}" for val in breakdown_df["Amount"]],
            y = breakdown_df["Amount"],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(title_text="Lifetime Money Flow", showlegend = False)
        st.plotly_chart(fig_waterfall, use_container_width=True)
    else:
        st.info("No earnings in this scenario to display breakdown.")

    # Net worth and components over time
    st.subheader("📈 Financial Growth Over Time")
    
    df = pd.DataFrame(yearly_data)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Net Worth Growth', 'After-tax Income vs. Expenses', 'Investment Portfolio vs. Liquid Savings', 'Total Savings Contribution Annually'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Net worth growth (Top Left)
    fig.add_trace(
        go.Scatter(x=df['year_display'], y=df['net_worth'], name='Net Worth', line=dict(color='blue', width=3), hoverinfo='x+y+name'),
        row=1, col=1
    )
    
    # Income vs expenses (Top Right)
    fig.add_trace(
        go.Scatter(x=df['year_display'], y=df['after_tax_income'], name='After-tax Income', line=dict(color='green'), hoverinfo='x+y+name'),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=df['year_display'], y=df['living_expenses_inflation_adj'], name='Living Expenses (Inflation Adj.)', line=dict(color='red'), hoverinfo='x+y+name'),
        row=1, col=2
    )
    
    # Investment portfolio vs Liquid Savings (Bottom Left)
    fig.add_trace(
        go.Scatter(x=df['year_display'], y=df['investment_portfolio_total'], name='Investment Portfolio', line=dict(color='purple'), hoverinfo='x+y+name'),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df['year_display'], y=df['liquid_savings_total'], name='Liquid Savings (Emergency Fund)', line=dict(color='orange', dash='dot'), hoverinfo='x+y+name'),
        row=2, col=1
    )

    # Total Savings Contribution Annually (Bottom Right)
    fig.add_trace(
        go.Bar(x=df['year_display'], y=df['annual_total_savings'], name='Annual Savings', hoverinfo='x+y+name', marker_color='darkcyan'),
        row=2, col=2
    )

    fig.update_layout(height=800, showlegend=True, title_text="Comprehensive Financial Analysis Charts")
    st.plotly_chart(fig, use_container_width=True)
    
    # Milestones & Events
    st.subheader("🏆 Financial Milestones & Annual Events")
    
    progress_miles = [100000, 250000, 500000, 1000000, 2500000, 5000000, 10000000]
    milestone_summary = []
    
    for mil in progress_miles:
        for year_data in yearly_data:
            if year_data.get("net_worth", 0) >= mil:
                milestone_summary.append({
                    "Milestone": f"${mil:,} Net Worth",
                    "Age": year_data["age"],
                    "Year": year_data["year_display"]
                })
                break # Only record the first time this milestone is hit
    
    if milestone_summary:
        st.markdown("**Net Worth Milestones:**")
        st.dataframe(pd.DataFrame(milestone_summary).set_index("Milestone"), use_container_width=True)
    else:
        st.info("No major net worth milestones reached in this simulation.")

    st.markdown("**Annual Key Events & Metrics:**")
    # Filter and display only relevant columns for the detailed table
    detailed_cols = ["year_display", "age", "gross_salary", "after_tax_income", "living_expenses_inflation_adj", "annual_total_savings", "investment_portfolio_total", "net_worth", "events"]
    detailed_df = pd.DataFrame(yearly_data)[detailed_cols]
    detailed_df.columns = ["Year", "Age", "Gross Salary", "After-tax Income", "Expenses (Adj.)", "Total Saved", "Invest. Port.", "Net Worth", "Events"]
    
    st.dataframe(detailed_df.style.format(
        {"Gross Salary": "${:,.0f}", "After-tax Income": "${:,.0f}", "Expenses (Adj.)": "${:,.0f}",
         "Total Saved": "${:,.0f}", "Invest. Port.": "${:,.0f}", "Net Worth": "${:,.0f}"}
    ), use_container_width=True) # Full dataframe for detailed viewing

def show_compare_scenarios():
    """Compare multiple scenarios side by side."""
    st.header("⚖️ Scenario Comparison")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if len(scenarios) < 2:
        st.warning("You need at least 2 financial scenarios to compare. Create more scenarios first!")
        return
    
    scenario_names = [s["name"] for s in scenarios if "name" in s]
    
    col1, col2 = st.columns(2)
    with col1:
        scenario1_name = st.selectbox("Select First Scenario:", scenario_names, key="compare_s1")
    with col2:
        # Filter out scenario1_name from the second selectbox options
        remaining_scenarios = [name for name in scenario_names if name != scenario1_name]
        scenario2_name = st.selectbox("Select Second Scenario:", remaining_scenarios, key="compare_s2")
    
    # Comparison parameters
    comparison_years = st.slider("Simulation Years for Comparison", min_value=5, max_value=60, value=30, step=5, key="compare_years")
    
    if st.button("🔍 Run Comparison", type="primary"):
        scenario1 = next(s for s in scenarios if s["name"] == scenario1_name)
        scenario2 = next(s for s in scenarios if s["name"] == scenario2_name)
        
        with st.spinner("Running comparison analysis..."):
            results1 = st.session_state.simulator.simulate_scenario(scenario1, years=comparison_years)
            results2 = st.session_state.simulator.simulate_scenario(scenario2, years=comparison_years)
        
        _display_comparison_results(results1, results2, scenario1_name, scenario2_name)

def _display_comparison_results(results1: Dict, results2: Dict, name1: str, name2: str):
    """Helper function to display scenario comparison results."""
    s1, s2 = results1["summary"], results2["summary"]
    
    st.subheader("🏆 Head-to-Head Comparison Summary")
    
    col_results1, col_results2, col_diff = st.columns(3)
    
    # Net Worth Comparison
    net_worth_diff = s2["final_net_worth"] - s1["final_net_worth"]
    with col_results1: st.metric(f"{name1} Final Net Worth", f"${s1['final_net_worth']:,.0f}")
    with col_results2: st.metric(f"{name2} Final Net Worth", f"${s2['final_net_worth']:,.0f}")
    with col_diff: st.metric("Net Worth Difference", f"${net_worth_diff:,.0f}", delta_color=("normal" if net_worth_diff > 0 else "inverse"))

    # Total Earned Comparison
    earned_diff = s2["total_earned"] - s1["total_earned"]
    with col_results1: st.metric(f"{name1} Total Earned", f"${s1['total_earned']:,.0f}")
    with col_results2: st.metric(f"{name2} Total Earned", f"${s2['total_earned']:,.0f}")
    with col_diff: st.metric("Total Earned Difference", f"${earned_diff:,.0f}", delta_color=("normal" if earned_diff > 0 else "inverse"))
    
    # Financial Independence Age Comparison
    fi1_status = f"Age {s1['fi_age']}" if s1['fi_achieved'] else "Not Achieved"
    fi2_status = f"Age {s2['fi_age']}" if s2['fi_achieved'] else "Not Achieved"
    
    col_fi1_disp, col_fi2_disp, col_fi_diff = st.columns(3)
    with col_fi1_disp: st.metric(f"{name1} FI Age", fi1_status)
    with col_fi2_disp: st.metric(f"{name2} FI Age", fi2_status)
    
    with col_fi_diff:
        if s1['fi_achieved'] and s2['fi_achieved']:
            fi_age_diff = s1['fi_age'] - s2['fi_age'] # Positive if s2 achieved earlier
            st.metric("FI Age Difference", f"{abs(fi_age_diff)} years", delta=f"{name2 if fi_age_diff > 0 else name1} earlier", delta_color=("inverse" if fi_age_diff > 0 else "normal"))
        elif s1['fi_achieved']:
            st.metric("FI Age Difference", "Only "+name1+" achieved FI", delta_color="normal")
        elif s2['fi_achieved']:
            st.metric("FI Age Difference", "Only "+name2+" achieved FI", delta_color="normal")
        else:
            st.metric("FI Age Difference", "Neither achieved FI")

    # Net worth growth comparison chart
    st.subheader("📈 Net Worth Growth Over Time")
    
    df1 = pd.DataFrame(results1["yearly_data"])
    df2 = pd.DataFrame(results2["yearly_data"])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df1["year_display"], y=df1["net_worth"], name=name1, line=dict(color='blue', width=3), hoverinfo='x+y+name'))
    fig.add_trace(go.Scatter(x=df2["year_display"], y=df2["net_worth"], name=name2, line=dict(color='green', width=3, dash='dash'), hoverinfo='x+y+name'))
    
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Net Worth ($)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        title_text="Net Worth Comparison Chart"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed comparison table
    st.subheader("📊 Detailed Comparison Table")
    
    summary_data = {
        "Metric": ["Final Net Worth", "Total Earned", "Total Saved", "Total Spent", "Final Investment Portfolio", "Final Remaining Debt", "Financial Independence Age"],
        name1: [s1["final_net_worth"], s1["total_earned"], s1["total_saved"], s1["total_spent"], s1["investment_portfolio_final"], s1["remaining_debt_final"], (f"Age {s1['fi_age']}" if s1['fi_achieved'] else "Not Achieved")],
        name2: [s2["final_net_worth"], s2["total_earned"], s2["total_saved"], s2["total_spent"], s2["investment_portfolio_final"], s2["remaining_debt_final"], (f"Age {s2['fi_age']}" if s2['fi_achieved'] else "Not Achieved")]
    }
    
    comparison_df = pd.DataFrame(summary_data)
    st.dataframe(comparison_df.style.format(
        subset=[name1, name2], 
        formatter=lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else str(x)
    ), use_container_width=True, hide_index=True)

def show_manage_scenarios():
    """Manage existing scenarios (view, edit, delete)."""
    st.header("📋 Manage Your Financial Scenarios")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.info("No scenarios to manage yet. Create one using the 'Create Scenario' tab.")
        return
    
    st.subheader("Your Saved Scenarios:")
    
    for scenario in scenarios:
        with st.container(border=True): # Use a container for each scenario for better grouping
            col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
            with col1:
                st.markdown(f"#### {scenario.get('name', 'Unnamed Scenario')}")
                st.caption(f"ID: {scenario.get('id', 'N/A')} | Created: {scenario.get('created_date', 'Unknown')}")
            with col2:
                st.write(f"Start: ${scenario.get('starting_salary', 0):,}")
                st.write(f"Exp: ${scenario.get('monthly_expenses', 0):,}/mo")
            with col3:
                st.write(f"Savings: {scenario.get('savings_rate', 0)*100:.1f}%")
                st.write(f"Debt: ${scenario.get('student_debt', 0):,}")
            with col4:
                # Add unique keys for buttons
                if st.button("✏️ Edit", key=f"edit_s_{scenario.get('id')}"):
                    st.session_state.editing_scenario_id = scenario.get('id')
                    st.session_state.page = "➕ Create Scenario" # Redirect to create/edit page
                    st.rerun()
                if st.button("🗑️ Delete", key=f"del_s_{scenario.get('id')}"):
                    st.session_state.simulator.delete_scenario(scenario["id"])
                    st.success(f"Scenario '{scenario['name']}' deleted.")
                    st.rerun()

def show_goals_tracker():
    """Page for tracking financial goals."""
    st.header("💰 Financial Goals Tracker")
    
    # Load goals data
    goals_data = goals_manager.load()
    
    st.subheader("Add a New Goal")
    with st.form("new_goal_form"):
        col1, col2 = st.columns(2)
        with col1:
            goal_name = st.text_input("Goal Name*", placeholder="e.g., House Down Payment, Retirement, New Car")
            target_amount = st.number_input("Target Amount ($)*", min_value=0, step=1000)
        with col2:
            target_date = st.date_input("Target Date (Optional)", min_value=datetime.date.today())
            current_progress = st.number_input("Current Progress ($)", min_value=0, step=100)
        
        submitted = st.form_submit_button("Add Goal", type="primary")
        if submitted:
            if goal_name and target_amount > 0:
                new_goal_id = max([g.get("id",0) for g in goals_data["goals"]]) + 1 if goals_data["goals"] else 1
                goals_data["goals"].append({
                    "id": new_goal_id,
                    "name": goal_name,
                    "target_amount": target_amount,
                    "target_date": target_date.strftime("%Y-%m-%d") if target_date else None,
                    "current_progress": current_progress,
                    "created_date": datetime.datetime.now().strftime("%Y-%m-%d")
                })
                goals_manager.save(goals_data)
                st.success(f"Goal '{goal_name}' added!")
                st.rerun()
            else:
                st.error("Please enter a goal name and a target amount.")
    
    st.subheader("Your Current Goals")
    
    if not goals_data["goals"]:
        st.info("No goals added yet. Start planning your future!")
        return

    # Prepare data for display
    goals_df_data = []
    for g in goals_data["goals"]:
        remaining_amount = g["target_amount"] - g["current_progress"]
        monthly_savings_needed = "N/A"
        date_obj = None
        if g["target_date"]:
            date_obj = datetime.datetime.strptime(g["target_date"], "%Y-%m-%d").date()
            today = datetime.date.today()
            if date_obj > today and remaining_amount > 0:
                months_left = (date_obj.year - today.year) * 12 + date_obj.month - today.month
                if months_left > 0:
                    monthly_savings_needed = f"${(remaining_amount / months_left):,.0f}"
        
        goals_df_data.append({
            "ID": g["id"],
            "Goal Name": g["name"],
            "Target Amount": f"${g['target_amount']:,.0f}",
            "Current Progress": f"${g['current_progress']:,.0f}",
            "Remaining": f"${remaining_amount:,.0f}",
            "Target Date": g["target_date"] if g["target_date"] else "N/A",
            "Monthly Savings Needed": monthly_savings_needed,
            "Created On": g["created_date"]
        })
    
    goals_df = pd.DataFrame(goals_df_data)
    cols_to_hide = ['ID'] # Hide ID column

    col_df, col_buttons = st.columns([0.8, 0.2])
    with col_df:
        st.dataframe(goals_df, use_container_width=True, hide_index=True)
    
    with col_buttons:
        st.write("---")
        st.subheader("Actions")
        goal_to_delete_id = st.number_input("Goal ID to delete:", min_value=0, step=1, key="goal_delete_id")
        if st.button("Delete Selected Goal", type="secondary"):
            if goal_to_delete_id > 0:
                initial_count = len(goals_data["goals"])
                goals_data["goals"] = [g for g in goals_data["goals"] if g["id"] != goal_to_delete_id]
                if len(goals_data["goals"]) < initial_count:
                    goals_manager.save(goals_data)
                    st.success(f"Goal with ID {goal_to_delete_id} deleted.")
                    st.rerun()
                else:
                    st.warning("Could not find goal with that ID.")
            else:
                st.warning("Please enter a valid Goal ID to delete.")

def show_expenses_tracker():
    """Page for tracking monthly expenses."""
    st.header("💸 Monthly Expenses Tracker")
    
    # Load expenses data
    expenses_data = expenses_manager.load()
    
    st.subheader("Add a New Expense")
    with st.form("new_expense_form"):
        col1, col2 = st.columns(2)
        with col1:
            expense_name = st.text_input("Expense Name*", placeholder="e.g., Rent, Groceries, Electricity")
            expense_amount = st.number_input("Monthly Amount ($)*", min_value=0.0, step=10.0)
        with col2:
            expense_category = st.selectbox("Category", ["Housing", "Food", "Transportation", "Utilities", "Entertainment", "Health", "Education", "Debt", "Personal Care", "Miscellaneous"])
        
        submitted = st.form_submit_button("Add Expense", type="primary")
        if submitted:
            if expense_name and expense_amount > 0:
                new_expense_id = max([e.get("id",0) for e in expenses_data["expenses"]]) + 1 if expenses_data["expenses"] else 1
                expenses_data["expenses"].append({
                    "id": new_expense_id,
                    "name": expense_name,
                    "amount": expense_amount,
                    "category": expense_category,
                    "created_date": datetime.datetime.now().strftime("%Y-%m-%d")
                })
                expenses_manager.save(expenses_data)
                st.success(f"Expense '{expense_name}' added!")
                st.rerun()
            else:
                st.error("Please enter an expense name and amount.")
    
    st.subheader("Your Current Monthly Expenses")
    
    if not expenses_data["expenses"]:
        st.info("No expenses added yet. Start tracking your spending!")
        return

    expenses_df = pd.DataFrame(expenses_data["expenses"])
    expenses_df["Amount ($)"] = expenses_df["amount"].apply(lambda x: f"${x:,.2f}") # Format for display
    
    total_monthly_expenses = expenses_df["amount"].sum()
    st.metric("Total Monthly Expenses", f"${total_monthly_expenses:,.2f}")
    
    col_df, col_actions = st.columns([0.7, 0.3])
    with col_df:
        st.dataframe(expenses_df[["name", "Amount ($)", "category", "created_date"]].rename(columns={"name":"Expense", "created_date":"Added On"}), use_container_width=True, hide_index=True)

    with col_actions:
        # Pie chart of expenses by category
        category_summary = expenses_df.groupby("category")["amount"].sum().reset_index()
        fig_pie = px.pie(category_summary, values='amount', names='category', title='Expenses by Category', hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)

        expense_to_delete_id = st.number_input("Expense ID to delete:", min_value=0, step=1, key="expense_delete_id")
        if st.button("Delete Selected Expense", type="secondary"):
            if expense_to_delete_id > 0:
                initial_count = len(expenses_data["expenses"])
                expenses_data["expenses"] = [e for e in expenses_data["expenses"] if e["id"] != expense_to_delete_id]
                if len(expenses_data["expenses"]) < initial_count:
                    expenses_manager.save(expenses_data)
                    st.success(f"Expense with ID {expense_to_delete_id} deleted.")
                    st.rerun()
                else:
                    st.warning("Could not find expense with that ID.")
            else:
                st.warning("Please enter a valid Expense ID to delete.")

def show_net_worth_tracker():
    """Page for manually tracking net worth snapshots."""
    st.header("📉 Net Worth Tracker")
    
    current_net_worth_history = net_worth_manager.load()

    st.subheader("Record Current Net Worth")
    with st.form("net_worth_snapshot_form"):
        st.markdown("Enter your current assets and liabilities to calculate your net worth snapshot.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Assets")
            cash = st.number_input("Cash & Bank Accounts ($)", min_value=0, value=0, step=100)
            investments = st.number_input("Investments (Stocks, Funds, etc.) ($)", min_value=0, value=0, step=100)
            property_value = st.number_input("Property (Home, Car) Value ($)", min_value=0, value=0, step=100)
            other_assets = st.number_input("Other Assets (Valuables, etc.) ($)", min_value=0, value=0, step=100)
        
        with col2:
            st.markdown("#### Liabilities")
            student_loans = st.number_input("Student Loans ($)", min_value=0, value=0, step=100)
            credit_card_debt = st.number_input("Credit Card Debt ($)", min_value=0, value=0, step=100)
            mortgage = st.number_input("Mortgage ($)", min_value=0, value=0, step=100)
            other_liabilities = st.number_input("Other Loans/Debts ($)", min_value=0, value=0, step=100)
        
        snapshot_date = st.date_input("Snapshot Date", value=datetime.date.today())
        
        submitted = st.form_submit_button("Record Net Worth Snapshot", type="primary")
        if submitted:
            total_assets = cash + investments + property_value + other_assets
            total_liabilities = student_loans + credit_card_debt + mortgage + other_liabilities
            calculated_net_worth = total_assets - total_liabilities
            
            # Check if an entry for this date already exists, update it
            existing_entry_index = next((i for i, item in enumerate(current_net_worth_history["history"]) if item["date"] == snapshot_date.strftime("%Y-%m-%d")), -1)

            new_snapshot = {
                "date": snapshot_date.strftime("%Y-%m-%d"),
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "net_worth": calculated_net_worth,
                "components": {
                    "cash": cash, "investments": investments, "property": property_value, "other_assets": other_assets,
                    "student_loans": student_loans, "credit_card_debt": credit_card_debt, "mortgage": mortgage, "other_liabilities": other_liabilities
                }
            }

            if existing_entry_index != -1:
                current_net_worth_history["history"][existing_entry_index] = new_snapshot
                st.success(f"Net Worth for {snapshot_date.strftime('%Y-%m-%d')} updated!")
            else:
                current_net_worth_history["history"].append(new_snapshot)
                st.success(f"Net Worth snapshot for {snapshot_date.strftime('%Y-%m-%d')} recorded!")

            net_worth_manager.save(current_net_worth_history)
            st.rerun()

    st.subheader("Net Worth History")
    
    if not current_net_worth_history["history"]:
        st.info("No net worth snapshots recorded yet. Start tracking your progress!")
        return

    df_history = pd.DataFrame(current_net_worth_history["history"])
    df_history["date"] = pd.to_datetime(df_history["date"])
    df_history = df_history.sort_values("date")
    
    st.metric("Latest Net Worth", f"${df_history['net_worth'].iloc[-1]:,.0f}", delta=f"As of {df_history['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # Plot Net Worth History
    fig = px.line(df_history, x="date", y="net_worth", title="Net Worth Over Time", markers=True)
    fig.update_layout(xaxis_title="Date", yaxis_title="Net Worth ($)")
    st.plotly_chart(fig, use_container_width=True)

    # Display detailed history table
    st.markdown("#### Detailed Net Worth Snapshots")
    st.dataframe(df_history[["date", "total_assets", "total_liabilities", "net_worth"]].style.format(
        {"total_assets": "${:,.0f}", "total_liabilities": "${:,.0f}", "net_worth": "${:,.0f}"}
    ), use_container_width=True, hide_index=True)

    # Option to delete a snapshot
    st.markdown("#### Delete Net Worth Snapshot")
    dates_to_delete = [d.strftime("%Y-%m-%d") for d in df_history["date"]]
    selected_date_to_delete = st.selectbox("Select date to delete snapshot for:", [""] + dates_to_delete, key="nw_delete_date")
    if st.button("Delete Snapshot", type="secondary"):
        if selected_date_to_delete:
            current_net_worth_history["history"] = [
                entry for entry in current_net_worth_history["history"] 
                if entry["date"] != selected_date_to_delete
            ]
            net_worth_manager.save(current_net_worth_history)
            st.success(f"Snapshot for {selected_date_to_delete} deleted.")
            st.rerun()
        else:
            st.warning("Please select a date to delete.")


def show_financial_tips():
    """Page providing general financial tips and insights."""
    st.header("💡 Financial Tips & Insights")
    st.markdown("Here are some general tips and insights to help you on your financial journey. Use your simulation results to apply these principles!")

    tabs = st.tabs(["🚀 Core Principles", "📈 Growing Wealth", "🛡️ Managing Risk", "🧠 Behavioral Finance"])

    with tabs[0]:
        st.subheader("🚀 Core Principles")
        st.markdown("""
        *   **Pay Yourself First:** Automate savings and investments before you spend. Treat it like a non-negotiable bill.
        *   **Live Below Your Means:** Consistently spend less than you earn. This is the foundation of wealth accumulation.
        *   **Understand Compound Interest:** It's the "eighth wonder of the world." The earlier you start investing, the more time your money has to grow exponentially.
        *   **Know Your Net Worth:** Regularly track your assets minus your liabilities. Use the Net Worth Tracker!
        *   **Create a Budget (and stick to it):** Know where your money is going. The Expenses Tracker can help.
        """)
    
    with tabs[1]:
        st.subheader("📈 Growing Wealth")
        st.markdown("""
        *   **Invest Early and Consistently:** Time in the market beats timing the market. Regular, automated investments are key.
        *   **Diversify Your Investments:** Don't put all your eggs in one basket. Invest across different asset classes (stocks, bonds, real estate).
        *   **Minimize Fees:** High fees can significantly erode your investment returns over time. Choose low-cost index funds or ETFs.
        *   **Increase Your Income:** Look for ways to boost your earnings – ask for raises, pursue promotions, start a side hustle.
            *   *Simulator Tip:* Use the "Career Changes" in scenarios to see how salary jumps affect your net worth!
        *   **Optimize Your Debt:** Prioritize paying off high-interest debt (like credit cards) first.
        """)

    with tabs[2]:
        st.subheader("🛡️ Managing Risk")
        st.markdown("""
        *   **Build an Emergency Fund:** Aim for 3-6 months (or more) of living expenses in an easily accessible, separate savings account. This prevents debt when unexpected expenses arise.
            *   *Simulator Tip:* Notice how the simulation prioritizes building an emergency fund if you factor in living expenses!
        *   **Get Adequate Insurance:** Health, auto, renter's/homeowner's, and disability insurance protect you from catastrophic financial losses.
        *   **Manage Debt Wisely:** Avoid unnecessary high-interest debt. Understand the terms, interest rates, and repayment plans for any loans you take.
        """)

    with tabs[3]:
        st.subheader("🧠 Behavioral Finance")
        st.markdown("""
        *   **Avoid Lifestyle Creep:** As your income grows, resist the urge to immediately increase your spending proportionally. Save or invest the difference.
        *   **Stay Invested During Volatility:** Market downturns are normal. Panic selling locks in losses. History shows markets recover.
        *   **Automate Everything:** Automate savings, investments, and bill payments to remove emotion and make financial progress effortless.
        *   **Be Patient:** Building significant wealth takes time and discipline. It's a marathon, not a sprint.
        *   **Educate Yourself Continuously:** The more you learn about personal finance, the better decisions you'll make.
        """)

def show_data_management():
    """Page for downloading and uploading data."""
    st.header("🗃️ Data Management")
    st.markdown("Manage your financial data files. You can download them for backup or upload previous versions.")

    tabs = st.tabs(["Download Data", "Upload Data"])

    # --- Download Data Tab ---
    with tabs[0]:
        st.subheader("Download Your Data")
        st.markdown("Click the buttons below to download your financial data files. These are in JSON format and can be re-uploaded later.")

        col1, col2, col3, col4 = st.columns(4)
        
        # Scenario Data
        with col1:
            scenario_data = scenario_manager.load()
            st.download_button(
                label="Download Scenarios (.json)",
                data=json.dumps(scenario_data, indent=4),
                file_name=SCENARIO_DATA_FILE,
                mime="application/json",
                help="Your saved financial scenarios.",
                key="download_scenarios"
            )
        
        # Goals Data
        with col2:
            goals_data = goals_manager.load()
            st.download_button(
                label="Download Goals (.json)",
                data=json.dumps(goals_data, indent=4),
                file_name=GOALS_DATA_FILE,
                mime="application/json",
                help="Your tracked financial goals.",
                key="download_goals"
            )

        # Expenses Data
        with col3:
            expenses_data = expenses_manager.load()
            st.download_button(
                label="Download Expenses (.json)",
                data=json.dumps(expenses_data, indent=4),
                file_name=EXPENSES_DATA_FILE,
                mime="application/json",
                help="Your monthly expenses records.",
                key="download_expenses"
            )

        # Net Worth History Data
        with col4:
            net_worth_history_data = net_worth_manager.load()
            st.download_button(
                label="Download Net Worth History (.json)",
                data=json.dumps(net_worth_history_data, indent=4),
                file_name=NET_WORTH_HISTORY_FILE,
                mime="application/json",
                help="Your historical net worth snapshots.",
                key="download_net_worth_history"
            )

    # --- Upload Data Tab ---
    with tabs[1]:
        st.subheader("Upload Your Data")
        st.warning("Uploading a file will **overwrite** your current data for that section. Proceed with caution!")

        upload_type = st.radio("Select data type to upload:", ["Scenarios", "Goals", "Expenses", "Net Worth History"])
        uploaded_file = st.file_uploader(f"Upload {upload_type} JSON file", type="json")

        if uploaded_file is not None:
            try:
                uploaded_data = json.load(uploaded_file)
                
                # Validate uploaded data structure (simple check)
                is_valid = True
                if upload_type == "Scenarios" and "scenarios" not in uploaded_data: is_valid = False
                elif upload_type == "Goals" and "goals" not in uploaded_data: is_valid = False
                elif upload_type == "Expenses" and "expenses" not in uploaded_data: is_valid = False
                elif upload_type == "Net Worth History" and "history" not in uploaded_data: is_valid = False

                if not is_valid:
                    st.error(f"Invalid {upload_type} file structure. Expected a JSON with a top-level '{upload_type.lower()}' or 'history' key.")
                    return

                if st.button(f"Confirm Overwrite and Upload {upload_type}", type="primary"):
                    if upload_type == "Scenarios":
                        scenario_manager.save(uploaded_data)
                        st.session_state.simulator = FinancialSimulator() # Reload simulator data
                    elif upload_type == "Goals":
                        goals_manager.save(uploaded_data)
                    elif upload_type == "Expenses":
                        expenses_manager.save(uploaded_data)
                    elif upload_type == "Net Worth History":
                        net_worth_manager.save(uploaded_data)
                    
                    st.success(f"Successfully uploaded and overwritten {upload_type} data!")
                    st.rerun() # Rerun to reflect changes
                else:
                    st.info("Click 'Confirm Upload' to finalize the upload.")

            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid JSON file.")
            except Exception as e:
                st.error(f"An error occurred during upload: {e}")

# --- Main Application Flow ---

def main():
    st.markdown('<h1 class="main-header">💰 Personal Economic Model</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Life Decision Simulator</p>', unsafe_allow_html=True)
    
    # Initialize simulator in session state if not already present
    if 'simulator' not in st.session_state:
        st.session_state.simulator = FinancialSimulator()
    
    # Initialize page state
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Dashboard"
    if 'editing_scenario_id' not in st.session_state: # To handle scenario editing state
        st.session_state.editing_scenario_id = None
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    
    # Use st.sidebar.button to allow dynamic page changes, especially for "Edit" actions
    if st.sidebar.button("🏠 Dashboard", key="nav_dashboard"):
        st.session_state.page = "🏠 Dashboard"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("➕ Create Scenario", key="nav_create_scenario"):
        st.session_state.page = "➕ Create Scenario"
        st.session_state.editing_scenario_id = None # Ensure we start fresh for new creation
    if st.sidebar.button("📈 Analyze Scenario", key="nav_analyze_scenario"):
        st.session_state.page = "📈 Analyze Scenario"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("⚖️ Compare Scenarios", key="nav_compare_scenarios"):
        st.session_state.page = "⚖️ Compare Scenarios"
        st.session_state.editing_scenario_id = None
    st.sidebar.markdown("---") # Separator
    if st.sidebar.button("💰 Goals Tracker", key="nav_goals_tracker"):
        st.session_state.page = "💰 Goals Tracker"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("💸 Expenses Tracker", key="nav_expenses_tracker"):
        st.session_state.page = "💸 Expenses Tracker"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("📉 Net Worth Tracker", key="nav_net_worth_tracker"):
        st.session_state.page = "📉 Net Worth Tracker"
        st.session_state.editing_scenario_id = None
    st.sidebar.markdown("---") # Separator
    if st.sidebar.button("📋 Manage Scenarios", key="nav_manage_scenarios"):
        st.session_state.page = "📋 Manage Scenarios"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("💡 Financial Tips", key="nav_financial_tips"):
        st.session_state.page = "💡 Financial Tips"
        st.session_state.editing_scenario_id = None
    if st.sidebar.button("🗃️ Data Management", key="nav_data_management"):
        st.session_state.page = "🗃️ Data Management"
        st.session_state.editing_scenario_id = None

    # Display the selected page content
    if st.session_state.page == "🏠 Dashboard":
        show_dashboard()
    elif st.session_state.page == "➕ Create Scenario":
        show_create_scenario()
    elif st.session_state.page == "📈 Analyze Scenario":
        show_analyze_scenario()
    elif st.session_state.page == "⚖️ Compare Scenarios":
        show_compare_scenarios()
    elif st.session_state.page == "📋 Manage Scenarios":
        show_manage_scenarios()
    elif st.session_state.page == "💰 Goals Tracker":
        show_goals_tracker()
    elif st.session_state.page == "💸 Expenses Tracker":
        show_expenses_tracker()
    elif st.session_state.page == "📉 Net Worth Tracker":
        show_net_worth_tracker()
    elif st.session_state.page == "💡 Financial Tips":
        show_financial_tips()
    elif st.session_state.page == "🗃️ Data Management":
        show_data_management()

if __name__ == "__main__":
    main()
