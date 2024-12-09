from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user
from db import get_db

import mysql.connector

bp = Blueprint('items', __name__, url_prefix='/items')

# @bp.route('/find_item', methods=['GET', 'POST'])
# @login_required
# def find_item():
#     db = get_db()
#     cursor = db.cursor(dictionary=True)

#     if request.method == 'POST':
#         item_id_str = request.form.get('item_id', '').strip()

#         # Edge Case A & B: Validate item_id is numeric and positive
#         if not item_id_str.isdigit():
#             flash("Please enter a valid numeric ItemID.")
#             return render_template('items/find_item.html', items=None)
        
#         item_id = int(item_id_str)
#         if item_id <= 0:
#             flash("ItemID must be a positive integer.")
#             return render_template('items/find_item.html', items=None)

#         # Check if item exists first
#         cursor.execute("SELECT ItemID, hasPieces FROM Item WHERE ItemID = %s", (item_id,))
#         item_row = cursor.fetchone()

#         if item_row is None:
#             # Item truly doesn't exist
#             flash("Item not found.")
#             return render_template('items/find_item.html', items=None)
        
#         # If item exists, handle the hasPieces logic
#         if not item_row['hasPieces']:
#             # Item exists but has no pieces
#             flash("This item exists but it has no pieces associated with it.")
#             # Display minimal info if desired. For now, just show message.
#             return render_template('items/find_item.html', items=None)
#         else:
#             # hasPieces = TRUE, attempt to load pieces
#             query = """
#             SELECT i.ItemID, i.iDescription, p.pieceNum, p.pDescription, 
#                    p.length, p.width, p.height, l.roomNum, l.shelfNum, l.shelf, l.shelfDescription
#             FROM Item i
#             JOIN Piece p ON i.ItemID = p.ItemID
#             JOIN Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum
#             WHERE i.ItemID = %s
#             """
#             cursor.execute(query, (item_id,))
#             results = cursor.fetchall()

#             if not results:
#                 # Data inconsistency: item claims to have pieces, but none found
#                 flash("This item is supposed to have pieces, but none are found. Please contact the administrator.")
#                 return render_template('items/find_item.html', items=None)
            
#             # Edge Case E: Check for invalid piece data (e.g., negative dimensions)
#             invalid_data_found = False
#             for r in results:
#                 if r['length'] < 0 or r['width'] < 0 or r['height'] < 0:
#                     invalid_data_found = True
#                     break
            
#             if invalid_data_found:
#                 flash("Warning: One or more pieces have invalid dimension data. Please verify the item data.")

#             # If we reach this point, we have a valid item with pieces
#             return render_template('items/find_item.html', items=results)

#     # GET request - just show the form
#     return render_template('items/find_item.html', items=None)
@bp.route('/find_item', methods=['GET', 'POST'])
@login_required
def find_item():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        item_id_str = request.form.get('item_id', '').strip()

        # Validate item_id
        if not item_id_str.isdigit():
            flash("Please enter a valid numeric ItemID.")
            return render_template('items/find_item.html', items=None)
        
        item_id = int(item_id_str)
        if item_id <= 0:
            flash("ItemID must be a positive integer.")
            return render_template('items/find_item.html', items=None)

        # Check if item exists
        cursor.execute("SELECT ItemID, iDescription, hasPieces, color, material, isNew FROM Item WHERE ItemID = %s", (item_id,))
        item_row = cursor.fetchone()

        if item_row is None:
            # Item doesn't exist
            flash("Item not found.")
            return render_template('items/find_item.html', items=None)
        
        # Always query pieces now, since even single-piece items are recorded in Piece
        query = """
        SELECT i.ItemID, i.iDescription, p.pieceNum, p.pDescription, 
               p.length, p.width, p.height, l.roomNum, l.shelfNum, l.shelf, l.shelfDescription
        FROM Item i
        JOIN Piece p ON i.ItemID = p.ItemID
        JOIN Location l ON p.roomNum = l.roomNum AND p.shelfNum = l.shelfNum
        WHERE i.ItemID = %s
        ORDER BY p.pieceNum
        """
        cursor.execute(query, (item_id,))
        results = cursor.fetchall()

        if not results:
            # No piece found for the item, this is data inconsistency now
            flash("Data inconsistency: No piece record found for this item. Please contact the administrator.")
            return render_template('items/find_item.html', items=None)
        
        # Check for invalid piece data
        invalid_data_found = any((r['length'] is not None and r['length'] < 0) or
                                 (r['width'] is not None and r['width'] < 0) or
                                 (r['height'] is not None and r['height'] < 0) for r in results)
        
        if invalid_data_found:
            flash("Warning: One or more pieces have invalid dimension data. Please verify the item data.")

        # Check consistency with hasPieces
        if not item_row['hasPieces'] and len(results) > 1:
            # Item is marked as no additional pieces, but multiple pieces found
            flash("Data inconsistency: Item is marked as a single-piece item, but multiple pieces found.")

        # If hasPieces=TRUE but only one piece found, it's not necessarily an error since at least one piece is valid.
        # If more needed, the user would have added them at donation time.

        return render_template('items/find_item.html', items=results)

    # GET request - just show the form
    return render_template('items/find_item.html', items=None)
