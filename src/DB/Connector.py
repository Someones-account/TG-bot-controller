import pymysql
from env.keys import PASSWORD

timeout = 10
connection = pymysql.connect(
    charset="utf8mb4",
    connect_timeout=timeout,
    cursorclass=pymysql.cursors.DictCursor,
    db="defaultdb",
    host="telegram-user-db-telegramuserdb.i.aivencloud.com",
    password=PASSWORD,
    read_timeout=timeout,
    port=16731,
    user="avnadmin",
    write_timeout=timeout,
)

def open_connection():
    try:
        cursor = connection.cursor()
        return cursor
    except:
        print("Connection to the database failed")
        return None
    #finally:
        #connection.commit()
        #connection.close()
