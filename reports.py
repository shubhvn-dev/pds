from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from db import get_db

import mysql.connector

bp = Blueprint('reports', __name__, url_prefix='/reports')


@bp.route('/year_end_report', methods=['GET', 'POST'])
@login_required
def year_end_report():
    # Get year from POST, fallback to current year or a default year if invalid
    year = request.form.get('year') if request.method == 'POST' else "2024"
    
    # Ensure year is a valid 4-digit number (e.g., 2024)
    try:
        year = int(year)
        if year < 1000 or year > 9999:
            raise ValueError("Invalid year")
    except ValueError:
        year = 2024  # Fallback to a default year

    print(f"Year Selected: {year}")  # Debugging the year selected

    

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Date format for the queries
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        # Query: Number of clients served
        cursor.execute("""
        SELECT COUNT(DISTINCT client) AS num_clients
        FROM Ordered
        WHERE orderDate BETWEEN %s AND %s
        """, (start_date, end_date))
        clients_served = cursor.fetchone()['num_clients']

        # Query: Number of items donated by category
        cursor.execute("""
        SELECT C.mainCategory, C.subCategory, COUNT(DISTINCT D.ItemID) AS donated_items
        FROM DonatedBy D
        JOIN Item I ON D.ItemID = I.ItemID
        JOIN Category C ON I.mainCategory = C.mainCategory AND I.subCategory = C.subCategory
        WHERE D.donateDate BETWEEN %s AND %s
        GROUP BY C.mainCategory, C.subCategory
        """, (start_date, end_date))
        donated_items = cursor.fetchall()

        # Query: Summary of client assistance
        cursor.execute("""
        SELECT COUNT(*) AS orders_processed
        FROM Ordered
        WHERE orderDate BETWEEN %s AND %s
        """, (start_date, end_date))
        orders_processed = cursor.fetchone()['orders_processed']

        # Query: Most frequent categories ordered by clients
        cursor.execute("""
        SELECT C.mainCategory, C.subCategory, COUNT(*) AS order_count
        FROM Ordered O
        JOIN ItemIn I ON O.orderID = I.orderID
        JOIN Item It ON I.ItemID = It.ItemID
        JOIN Category C ON It.mainCategory = C.mainCategory AND It.subCategory = C.subCategory
        WHERE O.orderDate BETWEEN %s AND %s
        GROUP BY C.mainCategory, C.subCategory
        ORDER BY order_count DESC
        LIMIT 5
        """, (start_date, end_date))
        top_categories = cursor.fetchall()

        # Query: Top 5 clients with the most donations
        cursor.execute("""
        SELECT D.userName, COUNT(DISTINCT D.ItemID) AS donation_count
        FROM DonatedBy D
        JOIN Item I ON D.ItemID = I.ItemID
        WHERE D.donateDate BETWEEN %s AND %s
        GROUP BY D.userName
        ORDER BY donation_count DESC
        LIMIT 5
        """, (start_date, end_date))
        top_clients_donations = cursor.fetchall()

        print(f"Clients Served: {clients_served}, Donated Items: {donated_items}, Orders Processed: {orders_processed}, Top Categories: {top_categories}, Top Clients Donations: {top_clients_donations}")

    except Exception as e:
        print(f"Error: {e}")
        # You might want to handle the error gracefully here, maybe return a 500 error or a friendly message

    return render_template(
        'reports/year_end_report.html',
        clients_served=clients_served,
        donated_items=donated_items,
        orders_processed=orders_processed,
        top_categories=top_categories,
        top_clients_donations=top_clients_donations,  # Add this line to pass top clients data to the template
        year=year
    )

@bp.route('/popular_categories', methods=['GET', 'POST'])
def popular_categories():
    #if its post request, get the start and end date from the form
    start_date = request.args.get('start_date', '2024-01-01')
    end_date = request.args.get('end_date', '2024-12-31')

    print(f"Start date: {start_date}, End date: {end_date}")
    

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        # Fetch popular categories
        query = """
            SELECT 
                i.mainCategory,
                i.subCategory,
                COUNT(DISTINCT o.orderID) AS totalOrders
            FROM 
                Item i
            JOIN 
                ItemIn ii ON i.ItemID = ii.ItemID
            JOIN 
                Ordered o ON ii.orderID = o.orderID
            WHERE 
                o.orderDate BETWEEN %s AND %s
            GROUP BY 
                i.mainCategory, i.subCategory
            ORDER BY 
                totalOrders DESC;
        """
        cursor.execute(query, (start_date, end_date))
        popular_categories = cursor.fetchall()
        print(popular_categories)
        return render_template('reports/popular_categories.html', categories=popular_categories, start_date=start_date, end_date=end_date)

    except mysql.connector.Error as e:
        flash(f"Database error: {e}")
        return redirect(url_for('index'))

