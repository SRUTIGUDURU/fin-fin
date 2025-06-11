import streamlit as st
import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import date, timedelta
import calendar

# Hardcoded password check function
def check_access():
    """Simple hardcoded password protection"""
    
    def verify_password():
        # YOUR HARDCODED PASSWORD - CHANGE THIS!
        CORRECT_PASSWORD = st.secrets["PASSWORD"]
        
        entered_password = st.session_state.get("app_password", "")
        
        if entered_password == CORRECT_PASSWORD:
            st.session_state["access_granted"] = True
            st.session_state["show_password_input"] = False
        else:
            st.session_state["access_granted"] = False
            if entered_password:  # Only show error if something was entered
                st.error("❌ Incorrect password!")

    # Check if access is already granted
    if st.session_state.get("access_granted", False):
        return True
    
    # Show password input
    st.markdown("""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        height: 50vh;
        flex-direction: column;
    ">
        <h1 style="color: #1f77b4; margin-bottom: 2rem;">🔐 Personal Finance App</h1>
        <p style="color: #666; font-size: 1.2rem; margin-bottom: 2rem;">Enter your access code to continue</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Center the password input
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password_input = st.text_input(
            "🔑 Password:",
            type="password",
            key="app_password",
            placeholder="Enter your password here..."
        )
        
        col_a, col_b, col_c = st.columns([1, 1, 1])
        with col_b:
            if st.button("🚀 Access App", type="primary", use_container_width=True):
                verify_password()
    
    return False

# Data file constants
DATA_FILE = "financial_scenarios.json"
GOALS_FILE = "financial_goals.json"
EXPENSES_FILE = "monthly_expenses.json"
INSIGHTS_FILE = "financial_insights.json"

class FinancialSimulator:
    def __init__(self):
        self.scenario_data = self.load_json(DATA_FILE, {"scenarios": []})
        self.goals_data = self.load_json(GOALS_FILE, {"goals": []})
        self.expenses_data = self.load_json(EXPENSES_FILE, {"expenses": [], "monthly_budgets": []})
        self.insights_data = self.load_json(INSIGHTS_FILE, {"insights": []})
    
    def load_json(self, filename, default):
        """Generic JSON loader."""
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return default
        return default
    
    def save_json(self, filename, data):
        """Generic JSON saver."""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    
    # Scenario methods
    def add_scenario(self, scenario_data):
        """Adds a new scenario to the data."""
        scenario_data["created_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scenario_data["id"] = len(self.scenario_data["scenarios"]) + 1
        self.scenario_data["scenarios"].append(scenario_data)
        self.save_json(DATA_FILE, self.scenario_data)
    
    def get_scenarios(self):
        """Returns all scenarios."""
        return self.scenario_data["scenarios"]
    
    def delete_scenario(self, scenario_id):
        """Deletes a scenario by ID."""
        self.scenario_data["scenarios"] = [s for s in self.scenario_data["scenarios"] if s.get("id") != scenario_id]
        self.save_json(DATA_FILE, self.scenario_data)
    
    # Goals methods
    def add_goal(self, goal_data):
        """Adds a new financial goal."""
        goal_data["id"] = len(self.goals_data["goals"]) + 1
        goal_data["created_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        goal_data["status"] = "active"
        goal_data["progress_history"] = []
        self.goals_data["goals"].append(goal_data)
        self.save_json(GOALS_FILE, self.goals_data)
    
    def update_goal_progress(self, goal_id, amount_saved):
        """Updates progress towards a goal."""
        for goal in self.goals_data["goals"]:
            if goal["id"] == goal_id:
                goal["current_amount"] = amount_saved
                goal["progress_history"].append({
                    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "amount": amount_saved
                })
                if amount_saved >= goal["target_amount"]:
                    goal["status"] = "completed"
                    goal["completion_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
                break
        self.save_json(GOALS_FILE, self.goals_data)
    
    def get_goals(self):
        """Returns all goals."""
        return self.goals_data["goals"]
    
    def delete_goal(self, goal_id):
        """Deletes a goal."""
        self.goals_data["goals"] = [g for g in self.goals_data["goals"] if g["id"] != goal_id]
        self.save_json(GOALS_FILE, self.goals_data)
    
    # Expense methods
    def add_expense(self, expense_data):
        """Adds a new expense."""
        expense_data["id"] = len(self.expenses_data["expenses"]) + 1
        expense_data["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        expense_data["month"] = datetime.datetime.now().strftime("%Y-%m")
        self.expenses_data["expenses"].append(expense_data)
        self.save_json(EXPENSES_FILE, self.expenses_data)
    
    def get_expenses(self, month=None):
        """Returns expenses, optionally filtered by month."""
        if month:
            return [e for e in self.expenses_data["expenses"] if e.get("month") == month]
        return self.expenses_data["expenses"]
    
    def add_monthly_budget(self, budget_data):
        """Adds or updates monthly budget."""
        # Check if budget exists for this month
        existing_budget = None
        for budget in self.expenses_data["monthly_budgets"]:
            if budget["month"] == budget_data["month"]:
                existing_budget = budget
                break
        
        if existing_budget:
            existing_budget.update(budget_data)
        else:
            self.expenses_data["monthly_budgets"].append(budget_data)
        
        self.save_json(EXPENSES_FILE, self.expenses_data)
    
    def get_monthly_budget(self, month):
        """Gets budget for a specific month."""
        for budget in self.expenses_data["monthly_budgets"]:
            if budget["month"] == month:
                return budget
        return None
    
    # Financial insights
    def generate_insights(self, scenarios, goals, expenses):
        """Generates AI-like insights based on financial data."""
        insights = []
        
        # Expense insights
        if expenses:
            total_monthly = sum(e["amount"] for e in expenses[-30:])  # Last 30 expenses
            avg_expense = total_monthly / len(expenses[-30:]) if expenses else 0
            
            if avg_expense > 100:
                insights.append({
                    "type": "expense",
                    "priority": "high",
                    "message": f"Your average expense is ₹{avg_expense:.2f}. Consider reviewing your spending habits.",
                    "date": datetime.datetime.now().strftime("%Y-%m-%d")
                })
        
        # Goal insights
        active_goals = [g for g in goals if g.get("status") == "active"]
        for goal in active_goals:
            progress = (goal.get("current_amount", 0) / goal["target_amount"]) * 100
            if progress < 25 and goal.get("target_date"):
                insights.append({
                    "type": "goal",
                    "priority": "medium",
                    "message": f"Your goal '{goal['name']}' is only {progress:.1f}% complete. Consider increasing savings.",
                    "date": datetime.datetime.now().strftime("%Y-%m-%d")
                })
        
        # Save insights
        self.insights_data["insights"] = insights[-10:]  # Keep last 10 insights
        self.save_json(INSIGHTS_FILE, self.insights_data)
        
        return insights
    
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
                    year_data["events"].append(f"Career change: ₹{current_salary:,}")
            
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
                    year_data["events"].append(f"{expense['name']}: ₹{adjusted_expense:,}")
            
            total_spent += major_expense_this_year
            
            # Handle debt payments
            debt_payment = 0
            if debt_balance > 0:
                # Assume 10-year repayment plan
                if scenario.get("student_debt", 0) > 0:
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

def show_dashboard():
    """Enhanced dashboard with insights."""
    st.header("📊 Financial Dashboard")
    
    scenarios = st.session_state.simulator.get_scenarios()
    goals = st.session_state.simulator.get_goals()
    current_month = datetime.datetime.now().strftime("%Y-%m")
    monthly_expenses = st.session_state.simulator.get_expenses(current_month)
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Scenarios", len(scenarios))
    
    with col2:
        active_goals = len([g for g in goals if g.get("status") == "active"])
        st.metric("Active Goals", active_goals)
    
    with col3:
        monthly_total = sum(e["amount"] for e in monthly_expenses)
        st.metric("This Month's Expenses", f"₹{monthly_total:,.0f}")
    
    with col4:
        completed_goals = len([g for g in goals if g.get("status") == "completed"])
        st.metric("Goals Achieved", completed_goals)
    
    # Financial Health Score
    st.subheader("🏆 Financial Health Score")
    
    health_score = calculate_financial_health_score(scenarios, goals, monthly_expenses)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Financial Health"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': get_health_color(health_score)},
                'steps': [
                    {'range': [0, 40], 'color': "lightgray"},
                    {'range': [40, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Quick insights
    st.subheader("💡 Quick Insights")
    insights = st.session_state.simulator.generate_insights(scenarios, goals, monthly_expenses)
    
    if insights:
        for insight in insights[:3]:  # Show top 3 insights
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(insight["priority"], "⚪")
            st.info(f"{priority_emoji} {insight['message']}")
    else:
        st.info("📊 Keep tracking your finances to generate personalized insights!")
    
    # Goals Progress
    if goals:
        st.subheader("🎯 Goals Progress")
        active_goals = [g for g in goals if g.get("status") == "active"][:3]  # Show top 3
        
        for goal in active_goals:
            current = goal.get("current_amount", 0)
            target = goal["target_amount"]
            progress = (current / target) * 100
            
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.write(f"**{goal['name']}**")
            with col2:
                st.progress(min(progress / 100, 1.0))
            with col3:
                st.write(f"{progress:.1f}%")

def show_goals():
    """Financial goals tracking page."""
    st.header("🎯 Financial Goals")
    
    tab1, tab2, tab3 = st.tabs(["Active Goals", "Add New Goal", "Completed Goals"])
    
    with tab1:
        goals = st.session_state.simulator.get_goals()
        active_goals = [g for g in goals if g.get("status") == "active"]
        
        if not active_goals:
            st.info("No active goals. Start by adding a new goal!")
        else:
            for goal in active_goals:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"### {goal['name']}")
                        st.write(f"{goal['description']}")
                        if goal.get('target_date'):
                            days_left = (datetime.datetime.strptime(goal['target_date'], "%Y-%m-%d") - datetime.datetime.now()).days
                            st.caption(f"⏰ {days_left} days remaining")
                    
                    with col2:
                        current = goal.get("current_amount", 0)
                        target = goal["target_amount"]
                        progress = (current / target) * 100
                        
                        st.metric("Progress", f"₹{current:,.0f} / ₹{target:,.0f}")
                        st.progress(min(progress / 100, 1.0))
                    
                    with col3:
                        # Update progress
                        new_amount = st.number_input(
                            "Update amount saved",
                            min_value=0.0,
                            value=float(current),
                            step=100.0,
                            key=f"update_{goal['id']}"
                        )
                        if st.button("Update", key=f"btn_{goal['id']}"):
                            st.session_state.simulator.update_goal_progress(goal['id'], new_amount)
                            st.rerun()
                    
                    with col4:
                        if st.button("🗑️", key=f"del_goal_{goal['id']}"):
                            st.session_state.simulator.delete_goal(goal['id'])
                            st.rerun()
                    
                    # Goal progress chart
                    if goal.get("progress_history"):
                        with st.expander("View Progress History"):
                            df = pd.DataFrame(goal["progress_history"])
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=df['date'],
                                y=df['amount'],
                                mode='lines+markers',
                                name='Saved Amount'
                            ))
                            fig.add_hline(y=target, line_dash="dash", line_color="green", annotation_text="Target")
                            fig.update_layout(title=f"{goal['name']} Progress", xaxis_title="Date", yaxis_title="Amount (₹)")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
    
    with tab2:
        st.subheader("Add New Financial Goal")
        
        with st.form("new_goal_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                goal_name = st.text_input("Goal Name*", placeholder="e.g., Emergency Fund, New Car, Vacation")
                goal_amount = st.number_input("Target Amount (₹)*", min_value=0, value=5000, step=100)
                current_saved = st.number_input("Already Saved (₹)", min_value=0, value=0, step=100)
            
            with col2:
                goal_category = st.selectbox("Category", ["Emergency Fund", "Major Purchase", "Travel", "Education", "Investment", "Other"])
                target_date = st.date_input("Target Date", min_value=date.today(), value=date.today() + timedelta(days=365))
                goal_description = st.text_area("Description", placeholder="Why is this goal important to you?")
            
            # Monthly saving calculation
            if goal_amount > current_saved and target_date > date.today():
                months_to_goal = (target_date.year - date.today().year) * 12 + (target_date.month - date.today().month)
                monthly_needed = (goal_amount - current_saved) / max(months_to_goal, 1)
                st.info(f"💡 You need to save approximately ₹{monthly_needed:.2f} per month to reach this goal")
            
            submitted = st.form_submit_button("🎯 Create Goal", type="primary")
            
            if submitted and goal_name and goal_amount > 0:
                goal_data = {
                    "name": goal_name,
                    "description": goal_description,
                    "target_amount": goal_amount,
                    "current_amount": current_saved,
                    "category": goal_category,
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "monthly_target": monthly_needed if 'monthly_needed' in locals() else 0
                }
                st.session_state.simulator.add_goal(goal_data)
                st.success(f"✅ Goal '{goal_name}' created successfully!")
                st.rerun()
    
    with tab3:
        goals = st.session_state.simulator.get_goals()
        completed_goals = [g for g in goals if g.get("status") == "completed"]
        
        if not completed_goals:
            st.info("No completed goals yet. Keep working towards your goals!")
        else:
            st.success(f"🎉 Congratulations! You've completed {len(completed_goals)} goals!")
            
            for goal in completed_goals:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"✅ **{goal['name']}**")
                    st.caption(f"Completed on: {goal.get('completion_date', 'Unknown')}")
                
                with col2:
                    st.metric("Final Amount", f"₹{goal['target_amount']:,.0f}")
                
                with col3:
                    if st.button("🗑️", key=f"del_completed_{goal['id']}"):
                        st.session_state.simulator.delete_goal(goal['id'])
                        st.rerun()

def show_expenses():
    """Expense tracking page."""
    st.header("💸 Expense Tracker")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add Expense", "Current Month", "Budget Planning", "Analytics"])
    
    with tab1:
        st.subheader("Add New Expense")
        
        with st.form("expense_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                expense_name = st.text_input("Expense Name*", placeholder="e.g., Groceries, Gas, Coffee")
                expense_amount = st.number_input("Amount (₹)*", min_value=0.0, step=0.01)
            
            with col2:
                expense_category = st.selectbox("Category", 
                    ["🍔 Food & Dining", "🚗 Transportation", "🏠 Housing", "🛍️ Shopping", 
                     "💊 Healthcare", "📚 Education", "🎬 Entertainment", "💰 Savings", "Other"])
            
            with col3:
                expense_date = st.date_input("Date", value=date.today())
                expense_note = st.text_input("Note (optional)", placeholder="Any additional details")
            
            submitted = st.form_submit_button("💸 Add Expense", type="primary")
            
            if submitted and expense_name and expense_amount > 0:
                expense_data = {
                    "name": expense_name,
                    "amount": expense_amount,
                    "category": expense_category,
                    "note": expense_note,
                    "date": expense_date.strftime("%Y-%m-%d")
                }
                st.session_state.simulator.add_expense(expense_data)
                st.success("✅ Expense added successfully!")
                st.rerun()
    
    with tab2:
        current_month = datetime.datetime.now().strftime("%Y-%m")
        month_name = calendar.month_name[datetime.datetime.now().month]
        st.subheader(f"📅 {month_name} {datetime.datetime.now().year} Expenses")
        
        monthly_expenses = st.session_state.simulator.get_expenses(current_month)
        monthly_budget = st.session_state.simulator.get_monthly_budget(current_month)
        
        if monthly_expenses:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            total_spent = sum(e["amount"] for e in monthly_expenses)
            budget_amount = monthly_budget["total_budget"] if monthly_budget else 0
            
            with col1:
                st.metric("Total Spent", f"₹{total_spent:,.2f}")
            
            with col2:
                st.metric("Budget", f"₹{budget_amount:,.2f}")
            
            with col3:
                remaining = budget_amount - total_spent
                st.metric("Remaining", f"₹{remaining:,.2f}", delta=f"{(remaining/budget_amount*100):.1f}%" if budget_amount > 0 else "N/A")
            
            with col4:
                avg_daily = total_spent / datetime.datetime.now().day
                st.metric("Daily Average", f"₹{avg_daily:,.2f}")
            
            # Expense breakdown by category
            st.subheader("📊 Category Breakdown")
            
            category_totals = {}
            for expense in monthly_expenses:
                category = expense["category"]
                category_totals[category] = category_totals.get(category, 0) + expense["amount"]
            
            df_categories = pd.DataFrame(list(category_totals.items()), columns=['Category', 'Amount'])
            
            fig = px.pie(df_categories, values='Amount', names='Category', title='Expenses by Category')
            st.plotly_chart(fig, use_container_width=True)
            
            # Expense list
            st.subheader("📋 Expense Details")
            
            df_expenses = pd.DataFrame(monthly_expenses)
            df_expenses = df_expenses.sort_values('date', ascending=False)
            
            # Display expenses in a nice format
            for _, expense in df_expenses.iterrows():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{expense['name']}**")
                    if expense.get('note'):
                        st.caption(expense['note'])
                
                with col2:
                    st.write(expense['category'])
                
                with col3:
                    st.write(f"₹{expense['amount']:.2f}")
                
                with col4:
                    st.caption(expense['date'])
        else:
            st.info("No expenses recorded for this month yet.")
    
    with tab3:
        st.subheader("📊 Monthly Budget Planning")
        
        current_month = datetime.datetime.now().strftime("%Y-%m")
        budget = st.session_state.simulator.get_monthly_budget(current_month)
        
        with st.form("budget_form"):
            st.write(f"### Budget for {calendar.month_name[datetime.datetime.now().month]} {datetime.datetime.now().year}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                total_budget = st.number_input("Total Monthly Budget (₹)", 
                    min_value=0, 
                    value=budget["total_budget"] if budget else 5000, 
                    step=100)
            
            with col2:
                income = st.number_input("Expected Monthly Income (₹)", 
                    min_value=0, 
                    value=budget["income"] if budget else 6000, 
                    step=100)
            
            st.write("### Category Budgets")
            
            categories = ["🍔 Food & Dining", "🚗 Transportation", "🏠 Housing", "🛍️ Shopping", 
                         "💊 Healthcare", "📚 Education", "🎬 Entertainment", "💰 Savings", "Other"]
            
            category_budgets = {}
            cols = st.columns(3)
            
            for i, category in enumerate(categories):
                with cols[i % 3]:
                    default_value = budget["category_budgets"].get(category, 0) if budget else 0
                    category_budgets[category] = st.number_input(
                        category, 
                        min_value=0, 
                        value=default_value, 
                        step=50,
                        key=f"cat_budget_{category}"
                    )
            
            submitted = st.form_submit_button("💾 Save Budget", type="primary")
            
            if submitted:
                budget_data = {
                    "month": current_month,
                    "total_budget": total_budget,
                    "income": income,
                    "category_budgets": category_budgets,
                    "savings_goal": income - total_budget
                }
                st.session_state.simulator.add_monthly_budget(budget_data)
                st.success("✅ Budget saved successfully!")
                st.rerun()
    
    with tab4:
        st.subheader("📈 Expense Analytics")
        
        # Get all expenses
        all_expenses = st.session_state.simulator.get_expenses()
        
        if all_expenses:
            df = pd.DataFrame(all_expenses)
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M').astype(str)
            
            # Monthly trend
            monthly_totals = df.groupby('month')['amount'].sum().reset_index()
            
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=monthly_totals['month'],
                y=monthly_totals['amount'],
                mode='lines+markers',
                name='Monthly Expenses',
                line=dict(color='red', width=3)
            ))
            fig1.update_layout(title='Monthly Expense Trend', xaxis_title='Month', yaxis_title='Total Expenses (₹)')
            st.plotly_chart(fig1, use_container_width=True)
            
            # Top spending categories
            category_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
            
            fig2 = go.Figure(go.Bar(
                x=category_totals.values,
                y=category_totals.index,
                orientation='h',
                marker_color='lightblue'
            ))
            fig2.update_layout(title='Total Spending by Category', xaxis_title='Amount (₹)', yaxis_title='Category')
            st.plotly_chart(fig2, use_container_width=True)
            
            # Spending patterns
            st.subheader("💡 Spending Insights")
            
            avg_monthly = monthly_totals['amount'].mean()
            highest_month = monthly_totals.loc[monthly_totals['amount'].idxmax()]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"📊 Average monthly spending: ₹{avg_monthly:,.2f}")
                st.info(f"📈 Highest spending month: {highest_month['month']} (₹{highest_month['amount']:,.2f})")
            
            with col2:
                top_category = category_totals.index[0]
                top_category_amount = category_totals.values[0]
                st.info(f"🏷️ Top spending category: {top_category}")
                st.info(f"💰 Total spent on {top_category}: ₹{top_category_amount:,.2f}")
        else:
            st.info("Start tracking expenses to see analytics!")

def show_advice():
    """Financial advice and recommendations page."""
    st.header("🧠 Smart Financial Advice")
    
    scenarios = st.session_state.simulator.get_scenarios()
    goals = st.session_state.simulator.get_goals()
    current_month_expenses = st.session_state.simulator.get_expenses(datetime.datetime.now().strftime("%Y-%m"))
    
    tab1, tab2, tab3 = st.tabs(["Personalized Advice", "Financial Education", "Action Plans"])
    
    with tab1:
        st.subheader("💡 Your Personalized Financial Advice")
        
        if scenarios and current_month_expenses:
            # Calculate some metrics
            total_monthly_expenses = sum(e["amount"] for e in current_month_expenses)
            active_goals = [g for g in goals if g.get("status") == "active"]
            
            # Generate personalized advice
            advice_items = []
            
            # Expense advice
            if total_monthly_expenses > 0:
                if any(e["category"] == "🍔 Food & Dining" for e in current_month_expenses):
                    food_expenses = sum(e["amount"] for e in current_month_expenses if e["category"] == "🍔 Food & Dining")
                    if food_expenses > total_monthly_expenses * 0.2:
                        advice_items.append({
                            "category": "Spending",
                            "priority": "High",
                            "advice": f"Your food expenses ({food_expenses/total_monthly_expenses*100:.1f}%) exceed 20% of monthly spending. Consider meal planning and cooking at home more often.",
                            "potential_savings": food_expenses * 0.3
                        })
            
            # Goals advice
            if active_goals:
                for goal in active_goals[:3]:  # Top 3 goals
                    progress = (goal.get("current_amount", 0) / goal["target_amount"]) * 100
                    if progress < 50:
                        monthly_needed = goal.get("monthly_target", 0)
                        advice_items.append({
                            "category": "Goals",
                            "priority": "Medium",
                            "advice": f"Your '{goal['name']}' goal needs ₹{monthly_needed:.2f}/month. Consider automating this transfer right after payday.",
                            "potential_savings": 0
                        })
            
            # Display advice
            for item in advice_items:
                priority_color = {"High": "red", "Medium": "orange", "Low": "green"}.get(item["priority"], "gray")
                
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**{item['category']}** - ::{priority_color}[{item['priority']} Priority]")
                        st.write(item["advice"])
                        if item["potential_savings"] > 0:
                            st.caption(f"💰 Potential monthly savings: ₹{item['potential_savings']:.2f}")
                    
                    with col2:
                        if st.button("✅ Got it!", key=f"advice_{advice_items.index(item)}"):
                            st.success("Great! Keep up the good work!")
                    
                    st.divider()
        else:
            st.info("Add some financial data to get personalized advice!")
    
    with tab2:
        st.subheader("📚 Financial Education Hub")
        
        education_topics = {
            "Budgeting Basics": {
                "icon": "💰",
                "description": "Learn the 50/30/20 rule and other budgeting strategies",
                "tips": [
                    "50% of income for needs (housing, utilities, groceries)",
                    "30% for wants (entertainment, dining out, hobbies)",
                    "20% for savings and debt repayment",
                    "Track every expense for at least one month",
                    "Review and adjust your budget monthly"
                ]
            },
            "Emergency Fund": {
                "icon": "🚨",
                "description": "Why you need one and how to build it",
                "tips": [
                    "Aim for 3-6 months of living expenses",
                    "Start small - even ₹500 can help",
                    "Keep it in a high-yield savings account",
                    "Only use for true emergencies",
                    "Replenish immediately after use"
                ]
            },
            "Investing Basics": {
                "icon": "📈",
                "description": "Start your investment journey",
                "tips": [
                    "Start with low-cost index funds",
                    "Understand risk tolerance",
                    "Diversify your portfolio",
                    "Think long-term (10+ years)",
                    "Consider dollar-cost averaging"
                ]
            },
            "Credit Score": {
                "icon": "📊",
                "description": "Build and maintain good credit",
                "tips": [
                    "Pay all bills on time",
                    "Keep credit utilization below 30%",
                    "Don't close old credit cards",
                    "Check your report annually",
                    "Dispute any errors immediately"
                ]
            }
        }
        
        cols = st.columns(2)
        for i, (topic, content) in enumerate(education_topics.items()):
            with cols[i % 2]:
                with st.expander(f"{content['icon']} {topic}"):
                    st.write(f"**{content['description']}**")
                    for tip in content['tips']:
                        st.write(f"• {tip}")
    
    with tab3:
        st.subheader("🎯 Your Financial Action Plan")
        
        # Generate action items based on user data
        action_items = []
        
        # Check if user has an emergency fund goal
        emergency_fund_goal = next((g for g in goals if "emergency" in g["name"].lower()), None)
        if not emergency_fund_goal:
            action_items.append({
                "task": "Create an Emergency Fund goal",
                "why": "Financial security against unexpected expenses",
                "how": "Go to Goals page and create a goal for 3-6 months of expenses",
                "priority": "High"
            })
        
        # Check spending patterns
        if current_month_expenses:
            total_monthly = sum(e["amount"] for e in current_month_expenses)
            if scenarios:
                avg_income = sum(s["starting_salary"] for s in scenarios) / len(scenarios) / 12
                if total_monthly > avg_income * 0.8:
                    action_items.append({
                        "task": "Reduce monthly expenses",
                        "why": "You're spending over 80% of your income",
                        "how": "Review expenses and identify areas to cut back",
                        "priority": "High"
                    })
        
        # Display action plan
        if action_items:
            for item in action_items:
                with st.container():
                    col1, col2 = st.columns([5, 1])
                    
                    with col1:
                        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(item["priority"], "⚪")
                        st.write(f"{priority_emoji} **{item['task']}**")
                        st.write(f"*Why:* {item['why']}")
                        st.write(f"*How:* {item['how']}")
                    
                    with col2:
                        if st.button("Start", key=f"action_{action_items.index(item)}"):
                            st.success("Great initiative! You've got this! 💪")
                    
                    st.divider()
        else:
            st.success("🎉 You're on track! Keep maintaining your good financial habits!")

def calculate_financial_health_score(scenarios, goals, expenses):
    """Calculate a financial health score from 0-100."""
    score = 50  # Base score
    
    # Scenario factor (having financial plans)
    if scenarios:
        score += min(len(scenarios) * 5, 15)
    
    # Goals factor
    active_goals = [g for g in goals if g.get("status") == "active"]
    if active_goals:
        avg_progress = sum(g.get("current_amount", 0) / g["target_amount"] * 100 for g in active_goals) / len(active_goals)
        score += min(avg_progress * 0.2, 20)
    
    # Expense tracking factor
    if expenses:
        score += 15
    
    return min(score, 100)

def get_health_color(score):
    """Get color based on health score."""
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    elif score >= 40:
        return "orange"
    else:
        return "red"

def show_create_scenario():
    """Interface for creating new financial scenarios."""
    st.header("➕ Create New Financial Scenario")
    
    with st.form("create_scenario_form"):
        st.subheader("🎯 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Scenario Name*", placeholder="e.g., Software Engineer Path")
            starting_age = st.number_input("Current Age*", min_value=18, max_value=65, value=22)
            starting_salary = st.number_input("Starting Salary (₹)*", min_value=0, value=60000, step=1000)
        
        with col2:
            salary_growth_rate = st.slider("Annual Salary Growth (%)*", 0.0, 20.0, 3.0, 0.1) / 100
            monthly_expenses = st.number_input("Monthly Living Expenses (₹)*", min_value=0, value=3000, step=100)
            savings_rate = st.slider("Savings Rate (%)*", 0.0, 100.0, 15.0, 1.0) / 100
        
        st.subheader("📈 Investment & Finance")
        col1, col2 = st.columns(2)
        with col1:
            investment_return_rate = st.slider("Expected Investment Return (%)*", 0.0, 20.0, 7.0, 0.1) / 100
        with col2:
            student_debt = st.number_input("Student Debt (₹)", min_value=0, value=0, step=1000)
        
        st.subheader("💸 Major Expenses (Optional)")
        num_expenses = st.number_input("Number of major expenses", 0, 5, 0)
        major_expenses = []
        
        for i in range(int(num_expenses)):
            col1, col2, col3 = st.columns(3)
            with col1:
                expense_name = st.text_input(f"Expense {i+1} Name", key=f"exp_name_{i}")
            with col2:
                expense_amount = st.number_input(f"Amount (₹)", key=f"exp_amt_{i}", min_value=0, step=1000)
            with col3:
                expense_year = st.number_input(f"Year", key=f"exp_yr_{i}", min_value=1, max_value=50, value=5)
            
            if expense_name and expense_amount > 0:
                major_expenses.append({
                    "name": expense_name,
                    "amount": expense_amount,
                    "year": expense_year - 1
                })
        
        st.subheader("🚀 Career Changes (Optional)")
        num_changes = st.number_input("Number of career changes", 0, 5, 0)
        career_changes = []
        
        for i in range(int(num_changes)):
            col1, col2, col3 = st.columns(3)
            with col1:
                change_year = st.number_input(f"Year", key=f"ch_yr_{i}", min_value=1, max_value=50, value=5)
            with col2:
                new_salary = st.number_input(f"New Salary (₹)", key=f"ch_sal_{i}", min_value=0, step=1000)
            with col3:
                new_growth_rate = st.slider(f"New Growth Rate (%)", 0.0, 20.0, 3.0, 0.1, key=f"ch_gr_{i}") / 100
            
            if new_salary > 0:
                career_changes.append({
                    "year": change_year - 1,
                    "new_salary": new_salary,
                    "new_growth_rate": new_growth_rate
                })
        
        submitted = st.form_submit_button("🎯 Create Scenario", type="primary")
        
        if submitted and name:
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

def show_analyze_scenario():
    """Detailed analysis of a selected scenario."""
    st.header("📈 Scenario Analysis")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.warning("No scenarios available. Create a scenario first!")
        return
    
    scenario_names = [s["name"] for s in scenarios]
    selected_name = st.selectbox("Select scenario to analyze:", scenario_names)
    
    selected_scenario = next(s for s in scenarios if s["name"] == selected_name)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        years = st.slider("Simulation Years", 5, 50, 30, 5)
    with col2:
        inflation_rate = st.slider("Inflation Rate (%)", 0.0, 10.0, 3.0, 0.1) / 100
    with col3:
        tax_rate = st.slider("Tax Rate (%)", 0.0, 50.0, 25.0, 1.0) / 100
    
    if st.button("🚀 Run Analysis", type="primary"):
        with st.spinner("Running financial simulation..."):
            results = st.session_state.simulator.simulate_scenario(
                selected_scenario, years=years, inflation_rate=inflation_rate, tax_rate=tax_rate
            )
        
        # Display results
        summary = results["summary"]
        yearly_data = results["yearly_data"]
        
        # Key metrics
        st.subheader("🎯 Key Financial Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Final Net Worth", f"₹{summary['final_net_worth']:,.0f}")
        with col2:
            if summary['total_saved'] > 0:
                roi = ((summary['final_net_worth'] - summary['total_saved']) / summary['total_saved']) * 100
            else:
                roi = 0
            st.metric("Investment ROI", f"{roi:.1f}%")
        with col3:
            st.metric("Total Saved", f"₹{summary['total_saved']:,.0f}")
        with col4:
            if summary['fi_achieved']:
                st.metric("Financial Independence", f"Age {summary['fi_age']}")
            else:
                st.metric("FI Target", f"₹{summary['fi_target']:,.0f}")
        
        # Charts
        st.subheader("📊 Financial Growth Over Time")
        
        df = pd.DataFrame(yearly_data)
        
        # Net worth chart
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df['year'], y=df['net_worth'], 
                                  mode='lines', name='Net Worth',
                                  line=dict(color='blue', width=3)))
        fig1.update_layout(title='Net Worth Growth', xaxis_title='Year', yaxis_title='Net Worth (₹)')
        st.plotly_chart(fig1, use_container_width=True)
        
        # Income vs Expenses
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df['year'], y=df['after_tax_income'], 
                                  mode='lines', name='After-tax Income',
                                  line=dict(color='green')))
        fig2.add_trace(go.Scatter(x=df['year'], y=df['living_expenses'], 
                                  mode='lines', name='Living Expenses',
                                  line=dict(color='red')))
        fig2.update_layout(title='Income vs Expenses', xaxis_title='Year', yaxis_title='Amount (₹)')
        st.plotly_chart(fig2, use_container_width=True)

def show_compare_scenarios():
    """Compare multiple scenarios side by side."""
    st.header("⚖️ Scenario Comparison")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if len(scenarios) < 2:
        st.warning("You need at least 2 scenarios to compare!")
        return
    
    scenario_names = [s["name"] for s in scenarios]
    
    col1, col2 = st.columns(2)
    with col1:
        scenario1_name = st.selectbox("First scenario:", scenario_names)
    with col2:
        remaining_scenarios = [s for s in scenario_names if s != scenario1_name]
        scenario2_name = st.selectbox("Second scenario:", remaining_scenarios)
    
    years = st.slider("Years to simulate:", 5, 50, 30, 5)
    
    if st.button("🔍 Compare", type="primary"):
        scenario1 = next(s for s in scenarios if s["name"] == scenario1_name)
        scenario2 = next(s for s in scenarios if s["name"] == scenario2_name)
        
        with st.spinner("Comparing scenarios..."):
            results1 = st.session_state.simulator.simulate_scenario(scenario1, years=years)
            results2 = st.session_state.simulator.simulate_scenario(scenario2, years=years)
        
        # Display comparison
        st.subheader("📊 Comparison Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            diff = results2["summary"]["final_net_worth"] - results1["summary"]["final_net_worth"]
            winner = scenario2_name if diff > 0 else scenario1_name
            st.metric("Net Worth Winner", winner, f"₹{abs(diff):,.0f} advantage")
        
        with col2:
            st.metric(scenario1_name, f"₹{results1['summary']['final_net_worth']:,.0f}")
        
        with col3:
            st.metric(scenario2_name, f"₹{results2['summary']['final_net_worth']:,.0f}")
        
        # Comparison chart
        df1 = pd.DataFrame(results1["yearly_data"])
        df2 = pd.DataFrame(results2["yearly_data"])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df1['year'], y=df1['net_worth'], 
                                mode='lines', name=scenario1_name))
        fig.add_trace(go.Scatter(x=df2['year'], y=df2['net_worth'], 
                                mode='lines', name=scenario2_name))
        fig.update_layout(title='Net Worth Comparison', 
                         xaxis_title='Year', 
                         yaxis_title='Net Worth (₹)')
        st.plotly_chart(fig, use_container_width=True)

def show_manage_scenarios():
    """Manage existing scenarios."""
    st.header("📋 Manage Scenarios")
    
    scenarios = st.session_state.simulator.get_scenarios()
    
    if not scenarios:
        st.info("No scenarios to manage yet.")
        return
    
    for scenario in scenarios:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"**{scenario['name']}**")
            st.caption(f"Created: {scenario.get('created_date', 'Unknown')}")
        
        with col2:
            st.write(f"Salary: ₹{scenario['starting_salary']:,}")
        
        with col3:
            if st.button("🗑️ Delete", key=f"del_{scenario['id']}"):
                st.session_state.simulator.delete_scenario(scenario['id'])
                st.rerun()

def main():
    # Set page config first
    st.set_page_config(
        page_title="Personal Economic Model - Life Decision Simulator",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed"  # Start collapsed until logged in
    )
    
    # Apply CSS styles
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
        .goal-progress {
            background-color: #e8f4f8;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            border-left: 4px solid #1f77b4;
        }
        .expense-category {
            background-color: #fff3cd;
            padding: 0.5rem;
            border-radius: 5px;
            margin: 0.25rem 0;
        }
        .insight-box {
            background-color: #d1ecf1;
            border-left: 4px solid #0c5460;
            padding: 1rem;
            border-radius: 5px;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Check password first
    if not check_access():
        return  # Stop here if password not correct
    
    # If we get here, password was correct - show the app
    # Add a logout option in the sidebar
    with st.sidebar:
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            # Clear session state to require password again
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.divider()
    
    # Your existing app code starts here
    st.markdown('<h1 class="main-header">💰 Personal Economic Model</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Your Complete Financial Life Simulator</p>', unsafe_allow_html=True)
    
    # Initialize simulator
    if 'simulator' not in st.session_state:
        st.session_state.simulator = FinancialSimulator()
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["🏠 Dashboard", "📈 Analyze Scenario", "➕ Create Scenario", "⚖️ Compare Scenarios", 
         "🎯 Goals", "💸 Expenses", "🧠 Advice & Education", "📋 Manage Scenarios"]
    )
    
    # Your existing page routing
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "➕ Create Scenario":
        show_create_scenario()
    elif page == "📈 Analyze Scenario":
        show_analyze_scenario()
    elif page == "⚖️ Compare Scenarios":
        show_compare_scenarios()
    elif page == "🎯 Goals":
        show_goals()
    elif page == "💸 Expenses":
        show_expenses()
    elif page == "🧠 Advice & Education":
        show_advice()
    elif page == "📋 Manage Scenarios":
        show_manage_scenarios()

if __name__ == "__main__":
    main()
