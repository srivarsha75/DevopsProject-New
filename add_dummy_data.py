import sqlite3
import random
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('Finance-Tracker-main/finance_tracker.db')
cursor = conn.cursor()

# First, check if there's a user to associate transactions with
cursor.execute("SELECT id FROM users LIMIT 1")
user = cursor.fetchone()

# If no user exists, create one
if not user:
    cursor.execute("INSERT INTO users (username, email, phone, password) VALUES (?, ?, ?, ?)",
                  ("testuser", "test@example.com", "1234567890", "password"))
    conn.commit()
    user_id = cursor.lastrowid
    print(f"Created test user with ID: {user_id}")
else:
    user_id = user[0]
    print(f"Using existing user with ID: {user_id}")

# Categories for transactions
categories = ["Food", "Transportation", "Entertainment", "Utilities", "Shopping", "Health", "Education"]

# Payment methods
payment_methods = ["Cash", "UPI", "Credit Card", "Debit Card"]

# Generate 10 random transactions
current_date = datetime.now()
for i in range(10):
    # Random amount between 100 and 5000
    amount = round(random.uniform(100, 5000), 2)
    
    # Random category
    category = random.choice(categories)
    
    # Random date in the last 30 days
    days_ago = random.randint(0, 30)
    transaction_date = (current_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    
    # Random payment method
    payment_method = random.choice(payment_methods)
    
    # Description
    description = f"Dummy transaction #{i+1} for {category}"
    
    # Insert transaction
    cursor.execute(
        "INSERT INTO transactions (user_id, amount, category, date, description, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount, category, transaction_date, description, payment_method)
    )
    
    print(f"Added transaction: {amount} for {category} on {transaction_date} via {payment_method}")

# Commit changes and close connection
conn.commit()
conn.close()

print("\nSuccessfully added 10 dummy transactions to the database.") 