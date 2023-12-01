import psycopg2
from TikTokCommentsFetcher.config import DBNAME, USER, PASSWORD, HOST, PORT, TABLE_NAME


def create_table():
    conn = psycopg2.connect(dbname=DBNAME, user=USER, password=PASSWORD, host=HOST, port=PORT)
    cur = conn.cursor()

    try:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                user_link VARCHAR(255),
                user_name VARCHAR(255),
                comment_text TEXT,
                comment_date VARCHAR(32),
                comment_like SMALLINT
            );
        """)
        conn.commit()
    except Exception as ex:
        print(ex)
    finally:
        cur.close()
        conn.close()
