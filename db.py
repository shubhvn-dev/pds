import click
from flask import current_app, g
import mysql.connector.cursor
from mysql.connector import Error
def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB']
            )
            g.db.row_factory = mysql.connector.cursor.MySQLCursorDict
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            g.db = None
    if g.db is None:
        print("Database connection failed!")
    else:
        print("Database connection successful!")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        cursor = db.cursor()
        sql_script = f.read().decode('utf8')
        cursor.execute(sql_script)
        cursor.close()


@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)