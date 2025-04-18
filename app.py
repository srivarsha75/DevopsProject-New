from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from datetime import datetime
import sqlite3
from collections import defaultdict
from flask_mail import Mail, Message
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'
# For development, disable actual sending
app.config['MAIL_SUPPRESS_SEND'] = True

mail = Mail(app)

# SQLite database setup
DATABASE = 'finance_tracker.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            payment_method TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            year INTEGER NOT NULL,
            notifications_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, category, month, year)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' in session:
        user_id = session['user_id']
        username = session['username']
        
        # Fetch transactions from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
        transactions = c.fetchall()
        
        # Compute the sum of transaction amounts for each payment method
        total_amount = sum(transaction[2] for transaction in transactions)
        total_upi = sum(transaction[2] for transaction in transactions if transaction[6] == 'UPI')
        total_cash = sum(transaction[2] for transaction in transactions if transaction[6] == 'Cash')
        
        # Get user email
        c.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        email_result = c.fetchone()
        email = email_result[0] if email_result else ""
        
        # Get recent notifications (limited to 5)
        c.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
        notifications = c.fetchall()
        
        # Format notifications for display
        recent_notifications = []
        for n in notifications:
            recent_notifications.append({
                'id': n[0],
                'title': n[2],
                'message': n[3],
                'category': n[4],
                'type': n[5],
                'created_at': n[6],
                'is_read': n[7]
            })
        
        conn.close()

        return render_template('index.html', 
                              username=username,
                              email=email,
                              total_amount=total_amount, 
                              total_upi=total_upi, 
                              total_cash=total_cash,
                              recent_notifications=recent_notifications)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]  # Store user_id in session
            session['username'] = user[1]  # Store username in session
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = c.fetchone()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
        else:
            c.execute("INSERT INTO users (username, email, phone, password) VALUES (?, ?, ?, ?)",
                      (username, email, phone, password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/transactions')
def transactions():
    if 'username' in session:
        user_id = session['user_id']  # Assuming you store user_id in session
        username = session['username']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
        transactions = c.fetchall()
        conn.close()

        return render_template('transaction.html', transactions=transactions, username=username)
    else:
        return redirect(url_for('login'))



@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'username' in session:
        user_id = session['user_id']
        date = request.form['date']
        category = request.form['category']
        amount = float(request.form['amount'])
        payment_method = request.form['payment_method']
        description = request.form['notes']

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, date, category, amount, payment_method, description) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, date, category, amount, payment_method, description))
        conn.commit()
        
        # Check budget threshold after adding transaction
        check_budget_threshold(user_id, category, conn)
        
        conn.close()

        return redirect(url_for('transactions'))
    else:
        return redirect(url_for('login'))
    
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    if 'username' in session:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        conn.close()
        flash('Transaction deleted successfully.', 'success')
    else:
        flash('You must be logged in to delete a transaction.', 'error')
    return redirect(url_for('transactions'))

@app.route('/daily_spending_data')
def daily_spending_data():
    if 'username' in session:
        user_id = session['user_id']
        
        # Fetch daily spending data from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT date, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY date", (user_id,))
        data = c.fetchall()
        conn.close()

        # Format data for Chart.js
        labels = [row[0] for row in data]
        amounts = [row[1] for row in data]

        return jsonify({'labels': labels, 'amounts': amounts})
    else:
        return redirect(url_for('login'))

@app.route('/monthly_spending_data')
def monthly_spending_data():
    if 'username' in session:
        user_id = session['user_id']
        
        # Fetch monthly spending data from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT strftime('%Y-%m', date) AS month, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY month", (user_id,))
        data = c.fetchall()
        conn.close()

        # Format data for Chart.js
        labels = [datetime.strptime(row[0], '%Y-%m').strftime('%b %Y') for row in data]
        amounts = [row[1] for row in data]

        return jsonify({'labels': labels, 'amounts': amounts})
    else:
        return redirect(url_for('login'))
    
    
from flask import session

@app.route('/statistics')
def statistics():
    # Retrieve the user's identifier from the session
    user_id = session.get('user_id')  # Assuming you store user ID in the session
    
    if user_id:
        # Fetch data for statistics page for the logged-in user from the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # Fetch total expenses for the logged-in user
        c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
        total_expenses_result = c.fetchone()
        total_expenses = total_expenses_result[0] if total_expenses_result else 0

        # Fetch expense breakdown by category for the logged-in user
        c.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY category", (user_id,))
        expense_by_category_result = c.fetchall()
        expense_by_category = dict(expense_by_category_result) if expense_by_category_result else {}

        # Fetch top spending categories for the logged-in user
        c.execute("SELECT category, SUM(amount) FROM transactions WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 5", (user_id,))
        top_spending_categories_result = c.fetchall()
        top_spending_categories = dict(top_spending_categories_result) if top_spending_categories_result else {}

        conn.close()

        # Render the statistics page template with the fetched data
        return render_template('statistics.html', total_expenses=total_expenses, expense_by_category=expense_by_category,
                               top_spending_categories=top_spending_categories)
    else:
        # Redirect to login page if user is not logged in
        return redirect(url_for('login'))

@app.route('/budgets')
def budgets():
    if 'username' in session:
        user_id = session['user_id']
        username = session['username']
        
        # Get current month and year
        current_date = datetime.now()
        current_month = current_date.strftime('%B')
        current_year = current_date.year
        
        # Fetch budgets for the current month
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT category, amount, notifications_enabled FROM budgets WHERE user_id = ? AND month = ? AND year = ?", 
                 (user_id, current_month, current_year))
        budgets_data = c.fetchall()
        
        # Get spending by category for current month
        c.execute("""
            SELECT category, SUM(amount) 
            FROM transactions 
            WHERE user_id = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            GROUP BY category
        """, (user_id, current_date.strftime('%m'), current_date.strftime('%Y')))
        spending = dict(c.fetchall())
        
        # Get all categories from transactions for budget setting
        c.execute("SELECT DISTINCT category FROM transactions WHERE user_id = ?", (user_id,))
        categories = [row[0] for row in c.fetchall()]
        
        # Add common categories if not already in list
        common_categories = ["Food", "Transportation", "Entertainment", "Utilities", "Shopping", "Health", "Education"]
        for category in common_categories:
            if category not in categories:
                categories.append(category)
        
        # Convert budgets to dict for easy comparison
        budget_dict = {}
        notifications_dict = {}
        for budget in budgets_data:
            budget_dict[budget[0]] = budget[1]
            notifications_dict[budget[0]] = budget[2]
        
        # Create budget data for display
        budget_data = []
        for category in categories:
            budget_amount = budget_dict.get(category, 0)
            notifications_enabled = notifications_dict.get(category, 1)
            spent_amount = spending.get(category, 0)
            remaining = budget_amount - spent_amount if budget_amount > 0 else 0
            percentage = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
            
            budget_data.append({
                'category': category,
                'budget': budget_amount,
                'spent': spent_amount,
                'remaining': remaining,
                'percentage': min(percentage, 100),  # Cap at 100%
                'notifications_enabled': notifications_enabled
            })
        
        conn.close()
        
        return render_template('budgets.html', 
                              username=username, 
                              budget_data=budget_data, 
                              categories=categories,
                              current_month=current_month,
                              current_year=current_year)
    else:
        return redirect(url_for('login'))

@app.route('/set_budget', methods=['POST'])
def set_budget():
    if 'username' in session:
        user_id = session['user_id']
        category = request.form['category']
        amount = float(request.form['amount'])
        month = request.form['month']
        year = int(request.form['year'])
        notifications_enabled = 1 if 'enable_notifications' in request.form else 0
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Check if budget already exists for this category/month/year
        c.execute("SELECT id FROM budgets WHERE user_id = ? AND category = ? AND month = ? AND year = ?", 
                 (user_id, category, month, year))
        existing = c.fetchone()
        
        if existing:
            # Update existing budget
            c.execute("UPDATE budgets SET amount = ?, notifications_enabled = ? WHERE id = ?", 
                     (amount, notifications_enabled, existing[0]))
        else:
            # Create new budget
            c.execute("INSERT INTO budgets (user_id, category, amount, month, year, notifications_enabled) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, category, amount, month, year, notifications_enabled))
        
        conn.commit()
        conn.close()
        
        flash(f'Budget for {category} set successfully!', 'success')
        return redirect(url_for('budgets'))
    else:
        return redirect(url_for('login'))

def check_budget_threshold(user_id, category, conn):
    """Check if the user has exceeded their budget threshold and send notifications if needed."""
    c = conn.cursor()
    
    # Get current month and year
    current_date = datetime.now()
    current_month = current_date.strftime('%B')
    current_year = current_date.year
    
    # Get budget for the category
    c.execute("SELECT amount, notifications_enabled FROM budgets WHERE user_id = ? AND category = ? AND month = ? AND year = ?", 
              (user_id, category, current_month, current_year))
    budget_result = c.fetchone()
    
    if not budget_result:
        return  # No budget set for this category
    
    budget_amount = budget_result[0]
    notifications_enabled = budget_result[1]
    
    # If notifications are disabled, return
    if not notifications_enabled:
        return
    
    # Get total spent for this category in the current month
    c.execute("""
        SELECT SUM(amount) 
        FROM transactions 
        WHERE user_id = ? AND category = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
    """, (user_id, category, current_date.strftime('%m'), current_date.strftime('%Y')))
    
    spent_result = c.fetchone()
    spent_amount = spent_result[0] if spent_result[0] else 0
    
    # Calculate percentage of budget used
    percentage_used = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
    
    # Check if user has exceeded threshold (80% of budget)
    if percentage_used >= 80:
        # Create notification
        if percentage_used >= 100:
            title = f"Budget Exceeded: {category}"
            message = f"You have exceeded your budget for {category}. Budget: ₹{budget_amount:.2f}, Spent: ₹{spent_amount:.2f}, Percentage: {percentage_used:.1f}%"
            notification_type = "danger"
            
            # Add UI notification
            add_notification(user_id, title, message, category, notification_type)
            
            # Show flash message
            flash(f'Warning: You have exceeded your budget for {category}!', 'danger')
        else:
            title = f"Budget Alert: {category}"
            message = f"You have used {percentage_used:.1f}% of your budget for {category}. Budget: ₹{budget_amount:.2f}, Spent: ₹{spent_amount:.2f}, Remaining: ₹{budget_amount-spent_amount:.2f}"
            notification_type = "warning"
            
            # Add UI notification
            add_notification(user_id, title, message, category, notification_type)
            
            # Show flash message
            flash(f'Notice: You have used {percentage_used:.1f}% of your budget for {category}.', 'warning')
        
        # Still try to send email if not suppressed
        if not app.config.get('MAIL_SUPPRESS_SEND', True):
            try:
                # Get user email
                c.execute("SELECT email FROM users WHERE id = ?", (user_id,))
                email_result = c.fetchone()
                
                if email_result:
                    user_email = email_result[0]
                    send_budget_alert(user_email, category, budget_amount, spent_amount, percentage_used)
            except Exception as e:
                print(f"Failed to send email: {str(e)}")

def send_budget_alert(email, category, budget, spent, percentage):
    """Send an email alert about budget threshold."""
    subject = f"Budget Alert: {category}"
    
    if percentage >= 100:
        subject = f"Budget Exceeded: {category}"
        body = f"""
        <h2>Budget Alert</h2>
        <p>You have <strong>exceeded</strong> your budget for <strong>{category}</strong>.</p>
        <ul>
            <li>Budget: ₹{budget:.2f}</li>
            <li>Spent: ₹{spent:.2f}</li>
            <li>Percentage: {percentage:.1f}%</li>
        </ul>
        <p>Please review your spending in this category.</p>
        """
    else:
        body = f"""
        <h2>Budget Alert</h2>
        <p>You have used <strong>{percentage:.1f}%</strong> of your budget for <strong>{category}</strong>.</p>
        <ul>
            <li>Budget: ₹{budget:.2f}</li>
            <li>Spent: ₹{spent:.2f}</li>
            <li>Remaining: ₹{budget-spent:.2f}</li>
        </ul>
        <p>This is a courtesy notification to help you stay within your budget.</p>
        """
    
    msg = Message(subject=subject, recipients=[email], html=body)
    mail.send(msg)

@app.route('/notifications')
def view_notifications():
    if 'username' in session:
        user_id = session['user_id']
        username = session['username']
        
        # Get notifications for the user
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        notifications = c.fetchall()
        
        # Format notifications for display
        formatted_notifications = []
        for n in notifications:
            formatted_notifications.append({
                'id': n[0],
                'title': n[2],
                'message': n[3],
                'category': n[4],
                'type': n[5],
                'created_at': n[6],
                'is_read': n[7]
            })
        
        # Get unread count
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
        unread_count = c.fetchone()[0]
        
        conn.close()
        
        return render_template('notifications.html', 
                              username=username, 
                              notifications=formatted_notifications,
                              unread_count=unread_count)
    else:
        return redirect(url_for('login'))

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'username' in session:
        user_id = session['user_id']
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", 
                 (notification_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

@app.route('/unread_notification_count')
def unread_notification_count():
    if 'username' in session:
        user_id = session['user_id']
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
        unread_count = c.fetchone()[0]
        conn.close()
        
        return jsonify({'count': unread_count})
    else:
        return jsonify({'count': 0})

def add_notification(user_id, title, message, category, type):
    """Add a notification to the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("""
        INSERT INTO notifications 
        (user_id, title, message, category, type, created_at) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, message, category, type, current_time))
    
    conn.commit()
    conn.close()

@app.route('/profile')
def profile():
    if 'username' in session:
        user_id = session['user_id']
        username = session['username']
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Get user email
        c.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        email_result = c.fetchone()
        email = email_result[0] if email_result else ""
        
        # Get recent notifications (limited to 5)
        c.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
        notifications = c.fetchall()
        
        # Format notifications for display
        recent_notifications = []
        for n in notifications:
            recent_notifications.append({
                'id': n[0],
                'title': n[2],
                'message': n[3],
                'category': n[4],
                'type': n[5],
                'created_at': n[6],
                'is_read': n[7]
            })
        
        # Get budget alerts count (unread warning/danger notifications)
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0 AND (type = 'warning' OR type = 'danger')", (user_id,))
        budget_alerts = c.fetchone()[0]
        
        # Get total spent
        c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (user_id,))
        total_spent_result = c.fetchone()
        total_spent = total_spent_result[0] if total_spent_result[0] else 0
        
        # Get current month's spending
        current_date = datetime.now()
        c.execute("""
            SELECT SUM(amount) 
            FROM transactions 
            WHERE user_id = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        """, (user_id, current_date.strftime('%m'), current_date.strftime('%Y')))
        monthly_spent_result = c.fetchone()
        monthly_spent = monthly_spent_result[0] if monthly_spent_result[0] else 0
        
        conn.close()
        
        return render_template('profile.html', 
                              username=username,
                              email=email,
                              recent_notifications=recent_notifications,
                              budget_alerts=budget_alerts,
                              total_spent=total_spent,
                              monthly_spent=monthly_spent)
    else:
        return redirect(url_for('login'))

@app.route('/test-icons')
def test_icons():
    return render_template('test-icons.html')

@app.route('/test-budget-alert/<category>')
def test_budget_alert(category):
    """Route to test budget alert functionality for a given category."""
    if 'username' in session:
        user_id = session['user_id']
        
        conn = sqlite3.connect(DATABASE)
        
        # Manually trigger budget check
        check_budget_threshold(user_id, category, conn)
        
        # Get budget data for information
        c = conn.cursor()
        current_date = datetime.now()
        current_month = current_date.strftime('%B')
        current_year = current_date.year
        
        # Get budget info
        c.execute("SELECT amount, notifications_enabled FROM budgets WHERE user_id = ? AND category = ? AND month = ? AND year = ?", 
                  (user_id, category, current_month, current_year))
        budget_result = c.fetchone()
        
        # Get spending info
        c.execute("""
            SELECT SUM(amount) 
            FROM transactions 
            WHERE user_id = ? AND category = ? AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        """, (user_id, category, current_date.strftime('%m'), current_date.strftime('%Y')))
        spent_result = c.fetchone()
        
        conn.close()
        
        if not budget_result:
            return f"No budget set for {category} in {current_month} {current_year}"
        
        budget_amount = budget_result[0]
        notifications_enabled = "Enabled" if budget_result[1] else "Disabled"
        spent_amount = spent_result[0] if spent_result and spent_result[0] else 0
        percentage = (spent_amount / budget_amount * 100) if budget_amount > 0 else 0
        
        # Display debug info
        debug_info = (
            f"Budget check triggered for {category}<br>"
            f"Budget: ₹{budget_amount:.2f}<br>"
            f"Spent: ₹{spent_amount:.2f}<br>"
            f"Percentage: {percentage:.1f}%<br>"
            f"Notifications: {notifications_enabled}<br>"
            f"Threshold check: {'Triggered' if percentage >= 80 else 'Not triggered'} (needs 80%+)"
        )
        
        return debug_info
    else:
        return redirect(url_for('login'))

@app.route('/add-test-transaction/<category>/<amount>')
def add_test_transaction(category, amount):
    """Add a test transaction for budget alert testing."""
    if 'username' in session:
        user_id = session['user_id']
        date = datetime.now().strftime('%Y-%m-%d')
        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount"
        
        payment_method = "Test"
        description = "Test transaction for budget alert"
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("INSERT INTO transactions (user_id, date, category, amount, payment_method, description) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, date, category, amount, payment_method, description))
        conn.commit()
        
        # Check budget threshold after adding transaction
        check_budget_threshold(user_id, category, conn)
        
        conn.close()
        
        return f"Added test transaction of ₹{amount} to {category}. <a href='/test-budget-alert/{category}'>Check alert status</a>"
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
