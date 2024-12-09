from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from db import get_db
import mysql.connector

bp = Blueprint('donations', __name__, url_prefix='/donations')

def is_staff(user_name):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT A.roleID FROM Act A JOIN Role R ON A.roleID = R.roleID WHERE A.userName = %s", (user_name,))
    roles = cursor.fetchall()
    return any(r['roleID'] in ['staff', 'supervisor'] for r in roles)

def is_donor(user_name):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Person WHERE userName = %s", (user_name,))
    person = cursor.fetchone()
    if not person:
        return False
    cursor.execute("SELECT roleID FROM Act WHERE userName = %s", (user_name,))
    roles = cursor.fetchall()
    return any(r['roleID'] == 'donor' for r in roles)

def get_all_donors():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT P.userName
        FROM Person P
        JOIN Act A ON P.userName = A.userName
        WHERE A.roleID = 'donor'
    """)
    donors = [row['userName'] for row in cursor.fetchall()]
    return donors

def get_all_categories():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT mainCategory, subCategory FROM Category")
    rows = cursor.fetchall()
    main_cats = sorted(set(row['mainCategory'] for row in rows))
    sub_cats = sorted(set(row['subCategory'] for row in rows))
    return main_cats, sub_cats

@bp.route('/accept_donation', methods=['GET', 'POST'])
@login_required
def accept_donation():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if not is_staff(current_user.id):
        flash("You must be a staff member to access this page.")
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        donors = get_all_donors()
        main_categories, sub_categories = get_all_categories()

        donor_user = request.form.get('donor_user', '').strip()
        iDescription = request.form.get('iDescription', '').strip()
        photo = request.form.get('photo', None)
        color = request.form.get('color', '').strip()
        isNew = request.form.get('isNew', 'true') == 'true'
        hasPieces = request.form.get('hasPieces', 'false') == 'true'
        material = request.form.get('material', '').strip()
        mainCategory = request.form.get('mainCategory', '').strip()
        subCategory = request.form.get('subCategory', '').strip()

        user_provided_item_id_str = request.form.get('item_id', '').strip()
        user_provided_item_id = int(user_provided_item_id_str) if user_provided_item_id_str.isdigit() else None

        # Validate donor
        if not is_donor(donor_user):
            flash("Donor does not exist or is not registered as a donor.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

        # Check category existence
        cursor.execute("SELECT 1 FROM Category WHERE mainCategory=%s AND subCategory=%s", (mainCategory, subCategory))
        if cursor.fetchone() is None:
            flash("Specified category does not exist. Please choose an existing category.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

        num_pieces_str = request.form.get('num_pieces', '0').strip()
        if not num_pieces_str.isdigit():
            flash("Invalid number of pieces.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)
        num_pieces = int(num_pieces_str)

        if num_pieces < 1:
            flash("At least one piece is required for every donation.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

        if not hasPieces and num_pieces > 1:
            flash("Item has no additional pieces, only one piece is allowed.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

        piece_data_list = []

        for idx in range(1, num_pieces + 1):
            pieceNum_str = request.form.get(f'pieceNum_{idx}', '').strip()
            pDescription = request.form.get(f'pDescription_{idx}', '').strip()
            length_str = request.form.get(f'length_{idx}', '').strip()
            width_str = request.form.get(f'width_{idx}', '').strip()
            height_str = request.form.get(f'height_{idx}', '').strip()
            roomNum_str = request.form.get(f'roomNum_{idx}', '').strip()
            shelfNum_str = request.form.get(f'shelfNum_{idx}', '').strip()
            pNotes = request.form.get(f'pNotes_{idx}', '').strip()

            if not pieceNum_str:
                flash("Piece number is required for each piece.")
                return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

            if (not pieceNum_str.isdigit() or not length_str.isdigit() or not width_str.isdigit() or 
                not height_str.isdigit() or not roomNum_str.isdigit() or not shelfNum_str.isdigit()):
                flash("Piece numeric fields must be integers. No item or donor record created.")
                return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

            pieceNum = int(pieceNum_str)
            length = int(length_str)
            width = int(width_str)
            height = int(height_str)
            roomNum = int(roomNum_str)
            shelfNum = int(shelfNum_str)

            if len(pDescription) > 200:
                flash("Piece description is too long (max 200 characters).")
                return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)
            if len(pNotes) > 500:
                flash("Piece notes are too long (max 500 characters).")
                return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

            # Check location existence
            cursor.execute("SELECT 1 FROM Location WHERE roomNum=%s AND shelfNum=%s", (roomNum, shelfNum))
            if cursor.fetchone() is None:
                flash(f"Location (roomNum={roomNum}, shelfNum={shelfNum}) does not exist. No item or donor record created.")
                return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

            piece_data_list.append({
                'pieceNum': pieceNum,
                'pDescription': pDescription,
                'length': length,
                'width': width,
                'height': height,
                'roomNum': roomNum,
                'shelfNum': shelfNum,
                'pNotes': pNotes
            })

        # Insert item and pieces
        try:
            if user_provided_item_id is not None:
                cursor.execute("""
                    INSERT INTO Item (ItemID, iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_provided_item_id, iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory))
                item_id = user_provided_item_id
            else:
                cursor.execute("""
                    INSERT INTO Item (iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (iDescription, photo, color, isNew, hasPieces, material, mainCategory, subCategory))
                item_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO DonatedBy (ItemID, userName, donateDate)
                VALUES (%s, %s, CURDATE())
            """, (item_id, donor_user))

            for p in piece_data_list:
                cursor.execute("""
                    INSERT INTO Piece (ItemID, pieceNum, pDescription, length, width, height, roomNum, shelfNum, pNotes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (item_id, p['pieceNum'], p['pDescription'], p['length'], p['width'], p['height'], p['roomNum'], p['shelfNum'], p['pNotes']))

            db.commit()
            flash("Donation accepted successfully!")
            return redirect(url_for('auth.index'))

        except mysql.connector.IntegrityError as e:
            db.rollback()
            flash(f"Database error occurred: {e}. No data was inserted.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)
        except Exception as e:
            db.rollback()
            flash(f"An unexpected error occurred: {e}. No data was inserted.")
            return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)

    # GET request
    donors = get_all_donors()
    main_categories, sub_categories = get_all_categories()
    return render_template('donations/accept_donation.html', donors=donors, main_categories=main_categories, sub_categories=sub_categories)
