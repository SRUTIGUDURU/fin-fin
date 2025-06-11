import streamlit as st
import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import List, Dict, Optional
import math

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
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .success-metric {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .warning-metric {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
    }
    .danger-metric {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
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
                    return json.load(f)
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
        scenario_data["id"] = len(self.data["scenarios"]) + 1
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
    
    def simulate_scenario(self, scenario, years=30, inflation_rate=0.03, tax_rate=0.25):
        """Runs a comprehensive financial simulation."""
        
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
        
        # Enhanced tracking
        yearly_data = []
        monthly_expenses_base = scenario["monthly_expenses"]
        
        for year in range(years):
            year_data = {
                "year": year + 1,
                "age": age + year,
                "events": []
            }
            
            # Apply career changes
            for change in scenario.get("career_changes", []):
                if change["year"] == year:
                    current_salary = change["new_salary"]
                    current_growth_rate = change["new_growth_rate"]
                    year_data["events"].append(f"Career change: ${current_salary:,}")
            
            # Calculate inflation-adjusted expenses
            inflation_multiplier = (1 + inflation_rate) ** year
            monthly_expenses_adjusted = monthly_expenses_base * inflation_multiplier
            annual_living_expenses = monthly_expenses_adjusted * 12
            
            # Calculate annual income with growth
            annual_income = current_salary * (1 + current_growth_rate) ** year
            
            # Calculate taxes
            annual_taxes = annual_income * tax_rate
            after_tax_income = annual_income - annual_taxes
            
            year_data.update({
                "gross_salary": annual_income,
                "taxes": annual_taxes,
                "after_tax_income": after_tax_income,
                "living_expenses": annual_living_expenses,
                "inflation_multiplier": inflation_multiplier
            })
            
            total_earned += annual_income
            total_taxes += annual_taxes
            total_spent += annual_living_expenses
            
            # Handle major expenses
            major_expense_this_year = 0
            for expense in scenario.get("major_expenses", []):
                if expense["year"] == year:
                    # Adjust for inflation
                    adjusted_expense = expense["amount"] * inflation_multiplier
                    major_expense_this_year += adjusted_expense
                    year_data["events"].append(f"{expense['name']}: ${adjusted_expense:,}")
            
            total_spent += major_expense_this_year
            
            # Handle debt payments
            debt_payment = 0
            if debt_balance > 0:
                # Assume 10-year repayment plan
                annual_debt_payment = scenario.get("student_debt", 0) / 10
                debt_payment = min(annual_debt_payment, debt_balance)
                debt_balance = max(0, debt_balance - debt_payment)
                year_data["debt_payment"] = debt_payment
                year_data["remaining_debt"] = debt_balance
            
            # Calculate available for savings
            available_for_savings = after_tax_income - annual_living_expenses - major_expense_this_year - debt_payment
            
            # Emergency fund logic
            emergency_fund_target = annual_living_expenses * 0.5  # 6 months of expenses
            emergency_fund_contribution = 0
            
            if liquid_savings < emergency_fund_target and available_for_savings > 0:
                emergency_fund_contribution = min(available_for_savings * 0.3, emergency_fund_target - liquid_savings)
                liquid_savings += emergency_fund_contribution
                available_for_savings -= emergency_fund_contribution
            
            # Investment contributions
            investment_contribution = max(0, available_for_savings * scenario["savings_rate"])
            
            # Investment growth (compound annually)
            investment_growth = investment_portfolio * scenario["investment_return_rate"]
            investment_portfolio += investment_contribution + investment_growth
            
            # Total savings and net worth
            annual_savings = investment_contribution + emergency_fund_contribution
            total_saved += annual_savings
            net_worth = liquid_savings + investment_portfolio - debt_balance
            
            year_data.update({
                "major_expenses": major_expense_this_year,
                "emergency_fund_contrib": emergency_fund_contribution,
                "investment_contrib": investment_contribution,
                "investment_growth": investment_growth,
                "total_savings": annual_savings,
                "liquid_savings": liquid_savings,
                "investment_portfolio": investment_portfolio,
                "debt_balance": debt_balance,
                "net_worth": net_worth
            })
            
            yearly_data.append(year_data)
        
        # Calculate financial independence metrics
        final_annual_expenses = monthly_expenses_base * (1 + inflation_rate) ** (years - 1) * 12
        withdrawal_rate = 0.04  # 4% rule
        fi_target = final_annual_expenses / withdrawal_rate
        
        # Find when financial independence is reached
        fi_year = None
        for year_data in yearly_data:
            if year_data["investment_portfolio"] >= fi_target:
                fi_year = year_data
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
                "liquid_savings": liquid_savings,
                "investment_portfolio": investment_portfolio,
                "remaining_debt": debt_balance,
                "fi_target": fi_target,
                "fi_achieved": fi_year is not None,
                "fi_age": fi_year["age"] if fi_year else None
            }
        }

def main():
    st.markdown('<h1 class="main-header">💰 Personal Economic Model</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Life Decision Simulator - Make Informed Financial Choices</p>', unsafe_allow_html=True)
    
    # Initialize simulator
    if 'simulator' not in st.session_state:
        st.session_state.simulator = FinancialSimulator()
    
    # Sidebar navigation
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
    """Dashboard showing overview of all scenarios."""
    st.header("📊 Financial Scenarios Dashboard")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.info("👋 Welcome! Create your first financial scenario to get started.")
        st.markdown("""
        ### What is this tool?
        This Personal Economic Model helps you:
        - 🎯 **Compare life paths** - See how different career choices affect your wealth
        - 📈 **Visualize compound interest** - Watch your money grow over decades
        - 🏆 **Find optimal strategies** - Discover which decisions create the biggest impact
        - 🚀 **Plan for financial independence** - Know when you can retire comfortably
        
        ### Quick Start Guide:
        1. Click "➕ Create Scenario" to model your first life path
        2. Add details like salary, expenses, and major purchases
        3. Run simulations to see your financial future
        4. Compare different scenarios to make informed decisions
        """)
        return
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Scenarios", len(scenarios))
    
    with col2:
        avg_starting_salary = sum(s["starting_salary"] for s in scenarios) / len(scenarios)
        st.metric("Avg Starting Salary", f"${avg_starting_salary:,.0f}")
    
    with col3:
        avg_savings_rate = sum(s["savings_rate"] for s in scenarios) / len(scenarios) * 100
        st.metric("Avg Savings Rate", f"{avg_savings_rate:.1f}%")
    
    with col4:
        recent_scenario = max(scenarios, key=lambda x: x.get("created_date", ""))
        st.metric("Latest Scenario", recent_scenario["name"][:15] + "...")
    
    # Scenarios overview table
    st.subheader("📋 Your Scenarios")
    
    scenario_df = pd.DataFrame([
        {
            "Scenario": s["name"],
            "Starting Salary": f"${s['starting_salary']:,}",
            "Monthly Expenses": f"${s['monthly_expenses']:,}",
            "Savings Rate": f"{s['savings_rate']*100:.1f}%",
            "Growth Rate": f"{s['salary_growth_rate']*100:.1f}%",
            "Created": s.get("created_date", "Unknown")[:10]
        }
        for s in scenarios
    ])
    
    st.dataframe(scenario_df, use_container_width=True)
    
    # Quick analysis for all scenarios
    if st.button("🚀 Quick Analysis: All Scenarios (30 years)"):
        st.subheader("📊 30-Year Projection Comparison")
        
        results = []
        for scenario in scenarios:
            result = st.session_state.simulator.simulate_scenario(scenario, years=30)
            results.append({
                "Scenario": scenario["name"],
                "Final Net Worth": result["summary"]["final_net_worth"],
                "Total Earned": result["summary"]["total_earned"],
                "Total Saved": result["summary"]["total_saved"],
                "FI Achieved": "✅" if result["summary"]["fi_achieved"] else "❌",
                "FI Age": result["summary"]["fi_age"] if result["summary"]["fi_achieved"] else "Not Reached"
            })
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values("Final Net Worth", ascending=False)
        
        # Display results with formatting
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Net Worth Rankings:**")
            for i, row in results_df.iterrows():
                rank = list(results_df.index).index(i) + 1
                st.write(f"{rank}. **{row['Scenario']}**: ${row['Final Net Worth']:,.0f}")
        
        with col2:
            st.markdown("**Financial Independence Status:**")
            for _, row in results_df.iterrows():
                fi_status = f"Age {row['FI Age']}" if row['FI Age'] != "Not Reached" else "Not Reached"
                st.write(f"**{row['Scenario']}**: {fi_status}")

def show_create_scenario():
    """Interface for creating new financial scenarios."""
    st.header("➕ Create New Financial Scenario")
    
    with st.form("create_scenario_form"):
        st.subheader("🎯 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Scenario Name*", placeholder="e.g., Software Engineer Path, MBA Route")
            starting_age = st.number_input("Current Age*", min_value=18, max_value=65, value=22)
            starting_salary = st.number_input("Starting Salary ($)*", min_value=0, value=60000, step=1000)
        
        with col2:
            salary_growth_rate = st.number_input("Annual Salary Growth (%)*", min_value=0.0, max_value=20.0, value=3.0, step=0.1) / 100
            monthly_expenses = st.number_input("Monthly Living Expenses ($)*", min_value=0, value=3000, step=100)
            savings_rate = st.number_input("Savings Rate (%)*", min_value=0.0, max_value=100.0, value=15.0, step=1.0) / 100
        
        st.subheader("📈 Investment & Finance")
        col1, col2 = st.columns(2)
        with col1:
            investment_return_rate = st.number_input("Expected Investment Return (%)*", min_value=0.0, max_value=20.0, value=7.0, step=0.1) / 100
        with col2:
            student_debt = st.number_input("Student Debt ($)", min_value=0, value=0, step=1000)
        
        st.subheader("💸 Major Expenses (Optional)")
        st.markdown("*Add significant future purchases or expenses*")
        
        # Dynamic major expenses
        num_expenses = st.number_input("Number of major expenses", min_value=0, max_value=10, value=0)
        major_expenses = []
        
        if num_expenses > 0:
            for i in range(num_expenses):
                st.markdown(f"**Expense {i+1}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    expense_name = st.text_input(f"Name", key=f"expense_name_{i}", placeholder="e.g., Car, House Down Payment")
                with col2:
                    expense_amount = st.number_input(f"Amount ($)", key=f"expense_amount_{i}", min_value=0, step=1000)
                with col3:
                    expense_year = st.number_input(f"Year", key=f"expense_year_{i}", min_value=1, max_value=50, value=1)
                
                if expense_name and expense_amount > 0:
                    major_expenses.append({
                        "name": expense_name,
                        "amount": expense_amount,
                        "year": expense_year - 1  # Convert to 0-indexed
                    })
        
        st.subheader("🚀 Career Changes (Optional)")
        st.markdown("*Model promotions, career switches, or salary jumps*")
        
        num_changes = st.number_input("Number of career changes", min_value=0, max_value=10, value=0)
        career_changes = []
        
        if num_changes > 0:
            for i in range(num_changes):
                st.markdown(f"**Career Change {i+1}**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    change_year = st.number_input(f"Year", key=f"change_year_{i}", min_value=1, max_value=50, value=5)
                with col2:
                    new_salary = st.number_input(f"New Salary ($)", key=f"new_salary_{i}", min_value=0, step=1000)
                with col3:
                    new_growth_rate = st.number_input(f"New Growth Rate (%)", key=f"new_growth_{i}", min_value=0.0, max_value=20.0, value=3.0, step=0.1) / 100
                
                if new_salary > 0:
                    career_changes.append({
                        "year": change_year - 1,  # Convert to 0-indexed
                        "new_salary": new_salary,
                        "new_growth_rate": new_growth_rate
                    })
        
        # Submit button
        submitted = st.form_submit_button("🎯 Create Scenario", type="primary")
        
        if submitted:
            if not name:
                st.error("Please provide a scenario name.")
                return
            
            scenario_data = {
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
            st.success(f"✅ Scenario '{name}' created successfully!")
            st.balloons()
            
            # Show quick preview
            with st.expander("📊 Quick 10-Year Preview"):
                preview_result = st.session_state.simulator.simulate_scenario(scenario_data, years=10)
                st.metric("Projected Net Worth (10 years)", f"${preview_result['summary']['final_net_worth']:,.0f}")

def show_analyze_scenario():
    """Detailed analysis of a selected scenario."""
    st.header("📈 Scenario Analysis")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.warning("No scenarios available. Create a scenario first!")
        return
    
    # Scenario selection
    scenario_names = [s["name"] for s in scenarios]
    selected_name = st.selectbox("Select scenario to analyze:", scenario_names)
    
    selected_scenario = next(s for s in scenarios if s["name"] == selected_name)
    
    # Analysis parameters
    col1, col2, col3 = st.columns(3)
    with col1:
        years = st.slider("Simulation Years", min_value=5, max_value=50, value=30, step=5)
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
        show_analysis_results(results, selected_scenario, years)

def show_analysis_results(results, scenario, years):
    """Display comprehensive analysis results."""
    summary = results["summary"]
    yearly_data = results["yearly_data"]
    
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
        roi = ((summary['final_net_worth'] - summary['total_saved']) / max(summary['total_saved'], 1)) * 100
        st.metric(
            "Investment ROI",
            f"{roi:.1f}%",
            delta=f"${summary['final_net_worth'] - summary['total_saved']:,.0f} growth"
        )
    
    with col3:
        savings_rate = (summary['total_saved'] / summary['total_earned']) * 100
        st.metric(
            "Lifetime Savings Rate",
            f"{savings_rate:.1f}%",
            delta=f"${summary['total_saved']:,.0f} saved"
        )
    
    with col4:
        if summary['fi_achieved']:
            st.metric(
                "Financial Independence",
                f"Age {summary['fi_age']}",
                delta="🎉 Achieved!"
            )
        else:
            st.metric(
                "FI Target",
                f"${summary['fi_target']:,.0f}",
                delta="Not reached"
            )
    
    # Financial breakdown
    st.subheader("💰 Lifetime Financial Breakdown")
    
    breakdown_df = pd.DataFrame([
        {"Category": "Total Earned", "Amount": summary['total_earned'], "Percentage": 100},
        {"Category": "Taxes Paid", "Amount": summary['total_taxes'], "Percentage": (summary['total_taxes']/summary['total_earned'])*100},
        {"Category": "Total Spent", "Amount": summary['total_spent'], "Percentage": (summary['total_spent']/summary['total_earned'])*100},
        {"Category": "Total Saved", "Amount": summary['total_saved'], "Percentage": (summary['total_saved']/summary['total_earned'])*100},
    ])
    
    # Pie chart
    fig_pie = px.pie(
        breakdown_df, 
        values='Amount', 
        names='Category',
        title="Lifetime Money Allocation",
        color_discrete_sequence=['#ff7f0e', '#d62728', '#2ca02c', '#1f77b4']
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Net worth over time
    st.subheader("📈 Net Worth Growth Over Time")
    
    df = pd.DataFrame(yearly_data)
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Net Worth Growth', 'Annual Income vs Expenses', 'Investment Portfolio Growth', 'Savings Rate by Year'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Net worth growth
    fig.add_trace(
        go.Scatter(x=df['year'], y=df['net_worth'], name='Net Worth', line=dict(color='blue', width=3)),
        row=1, col=1
    )
    
    # Income vs expenses
    fig.add_trace(
        go.Scatter(x=df['year'], y=df['after_tax_income'], name='After-tax Income', line=dict(color='green')),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=df['year'], y=df['living_expenses'], name='Living Expenses', line=dict(color='red')),
        row=1, col=2
    )
    
    # Investment portfolio
    fig.add_trace(
        go.Scatter(x=df['year'], y=df['investment_portfolio'], name='Investment Portfolio', line=dict(color='purple')),
        row=2, col=1
    )
    
    # Savings rate
    df['annual_savings_rate'] = (df['total_savings'] / df['after_tax_income']) * 100
    fig.add_trace(
        go.Scatter(x=df['year'], y=df['annual_savings_rate'], name='Savings Rate %', line=dict(color='orange')),
        row=2, col=2
    )
    
    fig.update_layout(height=800, showlegend=True, title_text="Comprehensive Financial Analysis")
    st.plotly_chart(fig, use_container_width=True)
    
    # Milestones
    st.subheader("🏆 Financial Milestones")
    
    milestones = [50000, 100000, 250000, 500000, 1000000, 2500000, 5000000]
    milestone_data = []
    
    for milestone in milestones:
        for year_data in yearly_data:
            if year_data["net_worth"] >= milestone:
                milestone_data.append({
                    "Milestone": f"${milestone:,}",
                    "Age": year_data["age"],
                    "Year": year_data["year"],
                    "Time to Achieve": f"{year_data['year']} years"
                })
                break
    
    if milestone_data:
        milestone_df = pd.DataFrame(milestone_data)
        st.dataframe(milestone_df, use_container_width=True)
    
    # Detailed year-by-year table
    with st.expander("📊 Detailed Year-by-Year Breakdown"):
        detailed_df = pd.DataFrame([
            {
                "Year": d["year"],
                "Age": d["age"],
                "Salary": f"${d['gross_salary']:,.0f}",
                "After-tax": f"${d['after_tax_income']:,.0f}",
                "Expenses": f"${d['living_expenses']:,.0f}",
                "Saved": f"${d['total_savings']:,.0f}",
                "Net Worth": f"${d['net_worth']:,.0f}",
                "Investment": f"${d['investment_portfolio']:,.0f}"
            }
            for d in yearly_data
        ])
        st.dataframe(detailed_df, use_container_width=True)

def show_compare_scenarios():
    """Compare multiple scenarios side by side."""
    st.header("⚖️ Scenario Comparison")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if len(scenarios) < 2:
        st.warning("You need at least 2 scenarios to compare. Create more scenarios first!")
        return
    
    # Scenario selection
    scenario_names = [s["name"] for s in scenarios]
    
    col1, col2 = st.columns(2)
    with col1:
        scenario1_name = st.selectbox("Select first scenario:", scenario_names, key="compare1")
    with col2:
        scenario2_name = st.selectbox("Select second scenario:", [name for name in scenario_names if name != scenario1_name], key="compare2")
    
    # Comparison parameters
    comparison_years = st.slider("Comparison Years", min_value=5, max_value=50, value=30, step=5)
    
    if st.button("🔍 Compare Scenarios", type="primary"):
        scenario1 = next(s for s in scenarios if s["name"] == scenario1_name)
        scenario2 = next(s for s in scenarios if s["name"] == scenario2_name)
        
        with st.spinner("Running comparison analysis..."):
            results1 = st.session_state.simulator.simulate_scenario(scenario1, years=comparison_years)
            results2 = st.session_state.simulator.simulate_scenario(scenario2, years=comparison_years)
        
        show_comparison_results(results1, results2, scenario1_name, scenario2_name, comparison_years)

def show_comparison_results(results1, results2, name1, name2, years):
    """Display scenario comparison results."""
    s1, s2 = results1["summary"], results2["summary"]
    
    # Comparison metrics
    st.subheader("🏆 Head-to-Head Comparison")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Net Worth")
        winner = name1 if s1["final_net_worth"] > s2["final_net_worth"] else name2
        advantage = abs(s1["final_net_worth"] - s2["final_net_worth"])
        st.success(f"🏆 **{winner}**")
        st.write(f"Advantage: ${advantage:,.0f}")
    
    with col2:
        st.markdown("### Total Earnings")
        winner = name1 if s1["total_earned"] > s2["total_earned"] else name2
        advantage = abs(s1["total_earned"] - s2["total_earned"])
        st.info(f"🏆 **{winner}**")
        st.write(f"Advantage: ${advantage:,.0f}")
    
    with col3:
        st.markdown("### Financial Independence")
        fi1 = s1["fi_age"] if s1["fi_achieved"] else "Not Achieved"
        fi2 = s2["fi_age"] if s2["fi_achieved"] else "Not Achieved"
        
        if fi1 == "Not Achieved" and fi2 == "Not Achieved":
            st.write(f"{name1}: {fi1}")
            st.write(f"{name2}: {fi2}")
        
        else:
            if fi1 != "Not Achieved" and fi2 != "Not Achieved":
                if fi1 < fi2:
                    st.success(f"🏆 **{name1}**")
                    st.write(f"Faster by {fi2 - fi1} years")
                else:
                    st.success(f"🏆 **{name2}**")
                    st.write(f"Faster by {fi1 - fi2} years")
            elif fi1 != "Not Achieved":
                st.success(f"🏆 **{name1}**")
                st.write(f"{name2} did not achieve FI")
            else:
                st.success(f"🏆 **{name2}**")
                st.write(f"{name1} did not achieve FI")
    
    # Detailed net worth growth comparison
    st.subheader("📈 Net Worth Growth Over Time")
    
    df1 = pd.DataFrame(results1["yearly_data"])
    df2 = pd.DataFrame(results2["yearly_data"])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df1["year"], y=df1["net_worth"], name=name1, line=dict(color='blue', width=3)))
    fig.add_trace(go.Scatter(x=df2["year"], y=df2["net_worth"], name=name2, line=dict(color='green', width=3, dash='dash')))
    
    fig.update_layout(
        xaxis_title='Years',
        yaxis_title='Net Worth ($)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Full comparison table
    st.subheader("📊 Detailed Comparison")
    
    comparisons = pd.DataFrame({
        "Metric": ["Total Earned", "Total Saved", "Total Spent", "Final Net Worth", "Liquid Savings", "Investment Portfolio", "FI Target"],
        name1: [s1["total_earned"], s1["total_saved"], s1["total_spent"], s1["final_net_worth"], s1["liquid_savings"], s1["investment_portfolio"], s1["fi_target"]],
        name2: [s2["total_earned"], s2["total_saved"], s2["total_spent"], s2["final_net_worth"], s2["liquid_savings"], s2["investment_portfolio"], s2["fi_target"]]
    })
    
    st.write(comparisons.style.format(subset=[name1, name2], formatter="{$,.0f}"))
