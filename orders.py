from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from db import get_db

import mysql.connector

bp = Blueprint('orders', __name__, url_prefix='/orders')

@bp.route('/', methods=['GET'])
def get_orders():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT orderID, orderDate, orderNotes, stat, supervisor, client
        FROM Ordered
    """)
    orders = cursor.fetchall()
    logged_in_user = session.get('username')  # Replace with the session key for the username
    print("logged_in_user", logged_in_user)
    return render_template('orders/orders.html', orders=orders, logged_in_user=logged_in_user)

@bp.route('/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    new_status = request.form.get('status')

    if new_status == 'Delivering':
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE Ordered
            SET stat = %s
            WHERE orderID = %s AND stat = 'prepared'
        """, (new_status, order_id))
        db.commit()

        flash("Order status updated to Delivering!")
        return redirect("/orders")
    
    flash("Invalid status change.")
    return redirect('/orders')

@bp.route('/user_related_orders', methods=['GET', 'POST'])
def user_tasks():
    
    # Combine orders from Ordered and DonatedBy tables
    query = """
    SELECT 
        o.orderID, o.orderDate, o.orderNotes, 'Supervisor' AS Role
    FROM Ordered o
    WHERE o.supervisor = %s
    
    UNION
    
    SELECT 
        o.orderID, o.orderDate, o.orderNotes, 'Client' AS Role
    FROM Ordered o
    WHERE o.client = %s
    
    UNION
    
    SELECT 
        d.ItemID, d.donateDate AS orderDate, 'Donated an item' AS orderNotes, 'Donor' AS Role
    FROM DonatedBy d
    WHERE d.userName = %s
    """
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        username = current_user.username

        cursor.execute(query, (username, username, username))
        tasks = cursor.fetchall()
        print(tasks)
    except Exception as e:
        print(f"Database error: {e}")
        tasks = []


    return render_template('orders/user_tasks.html', tasks=tasks, username=username)

def is_staff(user_name):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT A.roleID FROM Act A JOIN Role R ON A.roleID = R.roleID WHERE A.userName = %s", (user_name,))
    roles = cursor.fetchall()
    return any(r['roleID'] in ['staff', 'supervisor'] for r in roles)


@bp.route('/start_order', methods=['GET', 'POST'])
@login_required
def start_order():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Check staff privilege
    if not is_staff(current_user.id):
        flash("You must be a staff member to start an order.")
        return redirect(url_for('auth.index'))

    # Fetch all client usernames
    cursor.execute("SELECT userName FROM Person WHERE userName != %s", (current_user.id,))
    clients = cursor.fetchall()

    if request.method == 'POST':
        client_user = request.form.get('client_user', '').strip()
        order_notes = request.form.get('order_notes', '').strip()

        # Validate client
        cursor.execute("SELECT userName FROM Person WHERE userName = %s", (client_user,))
        person = cursor.fetchone()
        if not person:
            flash("Client does not exist.")
            return render_template('orders/start_order.html', clients=clients)

        # 2. Client cannot be the same as the staff user
        if client_user == current_user.id:
            flash("You cannot start an order for yourself.")
            return render_template('orders/start_order.html', clients=clients)

        # If validation passes, create a new order
        try:
            cursor.execute(""" 
                INSERT INTO Ordered (orderDate, orderNotes, supervisor, client)
                VALUES (CURDATE(), %s, %s, %s)
            """, (order_notes, current_user.id, client_user))
            db.commit()
            order_id = cursor.lastrowid
        except mysql.connector.Error as e:
            db.rollback()
            flash(f"Database error occurred: {e}")
            return render_template('orders/start_order.html', clients=clients)

        # Store order_id in session
        session['current_order_id'] = order_id
        print(f"[DEBUG] current_order_id set to {session.get('current_order_id')} for user {current_user.id}")
        
        flash("Order started successfully!")
        return redirect(url_for('auth.index'))  # Redirect to main page or next step in process

    # GET request
    return render_template('orders/start_order.html', clients=clients)




@bp.route('/add_to_order', methods=['GET', 'POST'])
@login_required
def add_to_order():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Check if user is staff
    if not is_staff(current_user.id):
        flash("You must be a staff member to add items to an order.")
        return redirect(url_for('auth.index'))

    # Check if there is a current order in session
    current_order_id = session.get('current_order_id')
    if not current_order_id:
        flash("No active order found. Please start an order first.")
        return redirect(url_for('orders.start_order'))

    # form_step logic:
    # step 1 (GET or initial POST): Show category selection
    # step 2 (POST after category selection): Show available items
    # step 3 (POST after choosing items): Insert items into ItemIn

    form_step = request.form.get('form_step', 'select_category')

    # Fetch categories from the database
    cursor.execute("SELECT DISTINCT mainCategory FROM Item")
    main_categories = cursor.fetchall()

    cursor.execute("SELECT DISTINCT subCategory FROM Item")
    sub_categories = cursor.fetchall()

    if request.method == 'POST':
        if form_step == 'select_category':
            # User selected a category, now we show items
            main_category = request.form.get('mainCategory', '').strip()
            sub_category = request.form.get('subCategory', '').strip()

            if not main_category or not sub_category:
                flash("Please select both main category and sub category.")
                return render_template('orders/add_to_order_select_category.html', main_categories=main_categories, sub_categories=sub_categories)

            # Query available items not in any order
            # Adjust logic if "available" means something else
            query = """
            SELECT I.ItemID, I.iDescription, I.color, I.isNew, I.hasPieces, I.material
            FROM Item I
            WHERE I.mainCategory=%s AND I.subCategory=%s
            AND I.ItemID NOT IN (SELECT ItemID FROM ItemIn)
            """
            cursor.execute(query, (main_category, sub_category))
            items = cursor.fetchall()

            if not items:
                flash("No available items found in this category.")
                return render_template('orders/add_to_order_select_category.html', main_categories=main_categories, sub_categories=sub_categories)

            # Render a template to show available items
            return render_template('orders/add_to_order_show_items.html', items=items, mainCategory=main_category, subCategory=sub_category)

        elif form_step == 'add_items':
            # User selected items to add
            selected_items = request.form.getlist('selected_items')
            if not selected_items:
                flash("No items selected to add.")
                # Show category selection again or redirect back
                return render_template('orders/add_to_order_select_category.html', main_categories=main_categories, sub_categories=sub_categories)

            # Insert selected items into ItemIn
            try:
                for item_id_str in selected_items:
                    item_id = int(item_id_str)
                    cursor.execute("INSERT INTO ItemIn (ItemID, orderID, found) VALUES (%s, %s, FALSE)", (item_id, current_order_id))
                db.commit()
            except mysql.connector.Error as e:
                db.rollback()
                flash(f"Database error occurred while adding items: {e}")
                return render_template('orders/add_to_order_select_category.html', main_categories=main_categories, sub_categories=sub_categories)

            flash("Items successfully added to the order!")
            return redirect(url_for('auth.index'))

    # GET request or initial step: show category selection form
    # Fetch categories if needed or just rely on user input
    # For simplicity, assume user knows what categories exist. If needed, query Category table and display options.
    return render_template('orders/add_to_order_select_category.html', main_categories=main_categories, sub_categories=sub_categories)


@bp.route('/prepare_order', methods=['GET', 'POST'])
@login_required
def prepare_order():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Check staff privilege
    if not is_staff(current_user.id):
        flash("You must be a staff member to prepare orders.")
        return redirect(url_for('auth.index'))

    # We'll use a 'step' field or logic in the POST to distinguish steps
    # Steps:
    # 1. Get order criteria (orderID or client_user)
    # 2. If multiple orders for client, let user choose one
    # 3. Show items in the selected order with a button to prepare
    # 4. On confirmation, update pieces to holding location

    step = request.form.get('step', 'search')  # default step is search

    if request.method == 'POST':
        if step == 'search':
            order_id_str = request.form.get('order_id', '').strip()
            client_user = request.form.get('client_user', '').strip()

            if not order_id_str and not client_user:
                flash("Please enter either an order ID or a client username.")
                return render_template('orders/prepare_order_search.html')

            # If order_id provided
            if order_id_str:
                if not order_id_str.isdigit():
                    flash("Order ID must be numeric.")
                    return render_template('orders/prepare_order_search.html')

                order_id = int(order_id_str)
                cursor.execute("SELECT * FROM Ordered WHERE orderID=%s", (order_id,))
                order = cursor.fetchone()
                if not order:
                    flash("No order found with that Order ID.")
                    return render_template('orders/prepare_order_search.html')

                # Found one order directly
                # Next step: Show items in this order
                # Store this order in session or hidden fields
                return show_order_items_for_preparation(order)

            # If client_user provided
            else:
                cursor.execute("SELECT * FROM Ordered WHERE client=%s", (client_user,))
                orders = cursor.fetchall()
                if not orders:
                    flash("No orders found for that client.")
                    return render_template('orders/prepare_order_search.html')

                if len(orders) == 1:
                    # Only one order, go directly to item display
                    return show_order_items_for_preparation(orders[0])
                else:
                    # Multiple orders, let user pick one
                    return render_template('orders/prepare_order_select_order.html', orders=orders)

        elif step == 'select_order':
            # User selected an order from multiple choices
            chosen_order_id_str = request.form.get('chosen_order_id', '')
            if not chosen_order_id_str.isdigit():
                flash("Invalid order chosen.")
                return render_template('orders/prepare_order_search.html')
            chosen_order_id = int(chosen_order_id_str)
            cursor.execute("SELECT * FROM Ordered WHERE orderID=%s", (chosen_order_id,))
            order = cursor.fetchone()
            if not order:
                flash("Order not found after selection.")
                return render_template('orders/prepare_order_search.html')

            return show_order_items_for_preparation(order)

        elif step == 'prepare_items':
            # Confirming preparation
            order_id_str = request.form.get('order_id', '')
            if not order_id_str.isdigit():
                flash("Invalid order ID during preparation.")
                return render_template('orders/prepare_order_search.html')

            order_id = int(order_id_str)

            # Update pieces of items in this order to holding location
            try:
                # Move all pieces related to this order to holding area (999, 999)
                cursor.execute("""
                    UPDATE Piece P
                    JOIN ItemIn II ON P.ItemID = II.ItemID
                    SET P.roomNum = 999, P.shelfNum = 999
                    WHERE II.orderID = %s
                """, (order_id,))
                #also in order rables change the stat to prepared
                cursor.execute("""
                    UPDATE Ordered
                    SET stat = 'prepared'
                    WHERE orderID = %s
                """, (order_id,))
                db.commit()
            except mysql.connector.Error as e:
                db.rollback()
                flash(f"Database error while preparing order: {e}")
                return render_template('orders/prepare_order_search.html')

            flash("Order prepared for delivery! Items moved to holding location.")
            return redirect(url_for('auth.index'))

    # GET request: show initial search form
    return render_template('orders/prepare_order_search.html')

def show_order_items_for_preparation(order):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    order_id = order['orderID']
    # Get all items in this order
    cursor.execute("""
        SELECT I.ItemID, I.iDescription, I.color, I.isNew, I.hasPieces, I.material
        FROM ItemIn II
        JOIN Item I ON II.ItemID = I.ItemID
        WHERE II.orderID = %s
    """, (order_id,))
    items = cursor.fetchall()

    return render_template('orders/prepare_order_show_items.html', order=order, items=items)

@bp.route('/find_order_items', methods=['GET', 'POST'])
@login_required
def find_order_items():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        order_id_str = request.form.get('order_id', '').strip()

        if not order_id_str.isdigit():
            flash("Please enter a valid numeric OrderID.")
            return render_template('orders/find_order_items.html', order_details=None)

        order_id = int(order_id_str)
        if order_id <= 0:
            flash("OrderID must be a positive integer.")
            return render_template('orders/find_order_items.html', order_details=None)

        query = """
        SELECT I.ItemID, I.iDescription, I.color, I.hasPieces, 
               P.pieceNum, P.pDescription, P.length, P.width, P.height,
               L.roomNum, L.shelfNum, L.shelf, L.shelfDescription
        FROM ItemIn AS II
        JOIN Item AS I ON II.ItemID = I.ItemID
        LEFT JOIN Piece AS P ON I.ItemID = P.ItemID
        LEFT JOIN Location AS L ON P.roomNum = L.roomNum AND P.shelfNum = L.shelfNum
        WHERE II.orderID = %s
        ORDER BY I.ItemID, P.pieceNum;
        """
        cursor.execute(query, (order_id,))
        results = cursor.fetchall()

        if not results:
            flash("No data found for this order.")
            return render_template('orders/find_order_items.html', order_details=None)

        items_map = {}
        invalid_data_found = False

        for row in results:
            item_id = row['ItemID']
            if item_id not in items_map:
                items_map[item_id] = {
                    'ItemID': item_id,
                    'iDescription': row['iDescription'],
                    'color': row['color'],
                    'hasPieces': row['hasPieces'],
                    'pieces': []
                }

            # If no pieceNum is found (i.e., P is NULL), that would mean no piece exists at all.
            # But we must have at least one piece per item. Check after processing.
            if row['pieceNum'] is not None:
                # Valid piece
                if (row['length'] is not None and row['length'] < 0) or \
                   (row['width'] is not None and row['width'] < 0) or \
                   (row['height'] is not None and row['height'] < 0):
                    invalid_data_found = True

                piece_data = {
                    'pieceNum': row['pieceNum'],
                    'pDescription': row['pDescription'],
                    'length': row['length'],
                    'width': row['width'],
                    'height': row['height'],
                    'roomNum': row['roomNum'],
                    'shelfNum': row['shelfNum'],
                    'shelf': row['shelf'],
                    'shelfDescription': row['shelfDescription']
                }
                items_map[item_id]['pieces'].append(piece_data)

        # After processing all rows, check consistency:
        for item_id, item_info in items_map.items():
            # If no pieces array is empty, that means no piece was returned.
            if len(item_info['pieces']) == 0:
                flash(f"Data inconsistency: No pieces found for ItemID {item_id}, but every item should have at least one piece.")
                # Not preventing rendering, just warning.

            if not item_info['hasPieces'] and len(item_info['pieces']) > 1:
                flash(f"Data inconsistency: ItemID {item_id} is marked as single-piece but multiple pieces found.")

        if invalid_data_found:
            flash("Warning: One or more pieces have invalid dimension data. Please verify the item data.")

        order_details = list(items_map.values())
        return render_template('orders/find_order_items.html', order_details=order_details)

    return render_template('orders/find_order_items.html', order_details=None)

# @bp.route('/find_order_items', methods=['GET', 'POST'])
# @login_required
# def find_order_items():
#     db = get_db()
#     cursor = db.cursor(dictionary=True)

#     if request.method == 'POST':
#         order_id_str = request.form.get('order_id', '').strip()

#         # Validate order_id (non-empty, numeric)
#         if not order_id_str.isdigit():
#             flash("Please enter a valid numeric OrderID.")
#             return render_template('orders/find_order_items.html', order_details=None)

#         order_id = int(order_id_str)
#         if order_id <= 0:
#             flash("OrderID must be a positive integer.")
#             return render_template('orders/find_order_items.html', order_details=None)

#         # Query to fetch item and piece info for given order
#         query = """
#         SELECT I.ItemID, I.iDescription, I.color, I.hasPieces, 
#                P.pieceNum, P.pDescription, P.length, P.width, P.height,
#                L.roomNum, L.shelfNum, L.shelf, L.shelfDescription
#         FROM ItemIn AS II
#         JOIN Item AS I ON II.ItemID = I.ItemID
#         LEFT JOIN Piece AS P ON I.ItemID = P.ItemID
#         LEFT JOIN Location AS L ON P.roomNum = L.roomNum AND P.shelfNum = L.shelfNum
#         WHERE II.orderID = %s
#         ORDER BY I.ItemID, P.pieceNum;
#         """
#         cursor.execute(query, (order_id,))
#         results = cursor.fetchall()

#         if not results:
#             # No items associated with this order at all
#             flash("No data found for this order.")
#             return render_template('orders/find_order_items.html', order_details=None)

#         # Group items by ItemID
#         items_map = {}
#         # Track if any invalid piece data found
#         invalid_data_found = False

#         for row in results:
#             item_id = row['ItemID']
#             if item_id not in items_map:
#                 # Initialize structure for a new item
#                 items_map[item_id] = {
#                     'ItemID': item_id,
#                     'iDescription': row['iDescription'],
#                     'color': row['color'],
#                     'hasPieces': row['hasPieces'],
#                     'pieces': []
#                 }

#             # If the item is supposed to have pieces but piece is None (from LEFT JOIN), handle that:
#             if row['hasPieces'] and row['pieceNum'] is None:
#                 # This means hasPieces=TRUE but no actual pieces returned
#                 # We'll set a flag to display a warning
#                 items_map[item_id]['no_pieces_found'] = True
#                 continue

#             if row['pieceNum'] is not None:
#                 # Check dimensions for invalid data
#                 if (row['length'] is not None and row['length'] < 0) or \
#                    (row['width'] is not None and row['width'] < 0) or \
#                    (row['height'] is not None and row['height'] < 0):
#                     invalid_data_found = True

#                 # Add piece to the item's pieces list if it exists
#                 piece_data = {
#                     'pieceNum': row['pieceNum'],
#                     'pDescription': row['pDescription'],
#                     'length': row['length'],
#                     'width': row['width'],
#                     'height': row['height'],
#                     'roomNum': row['roomNum'],
#                     'shelfNum': row['shelfNum'],
#                     'shelf': row['shelf'],
#                     'shelfDescription': row['shelfDescription']
#                 }
#                 items_map[item_id]['pieces'].append(piece_data)

#         # Check for items with hasPieces=TRUE but no pieces returned
#         # This is done after processing all results
#         for item_id, item_info in items_map.items():
#             if item_info['hasPieces'] and ('no_pieces_found' in item_info) and not item_info['pieces']:
#                 flash(f"Data inconsistency detected: ItemID {item_id} is supposed to have pieces, but none found. Please check the data.")

#         if invalid_data_found:
#             flash("Warning: One or more pieces have invalid dimension data. Please verify the item data.")

#         # Convert items_map to a list for easier template iteration
#         order_details = list(items_map.values())
#         return render_template('orders/find_order_items.html', order_details=order_details)

#     # GET request
#     return render_template('orders/find_order_items.html', order_details=None)


