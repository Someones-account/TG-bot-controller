from datetime import datetime
import pymysql
from src.Bot.Connector import open_connection


class QueryManager:
    def __init__(self, cursor):
        self.cursor = cursor


    def create_entry(self, user_id, action, lift_time, chat_id):
        self.__ensure_connection()
        try:
            query = "INSERT INTO ModerationActions (user_id, action, timestamp, lift_time, chat_id) VALUES (%s, %s, %s, %s, %s);"
            self.cursor.execute(query, (user_id, action, datetime.now(), lift_time, chat_id))
            self.cursor.connection.commit()

        except:
            print("Query failed!")


    def get_banned_users(self):
        self.__ensure_connection()
        try:
            query = "SELECT * FROM ModerationActions WHERE action = 'Ban' AND lift_time > %s;"
            self.cursor.execute(query, (datetime.now(),))
            return self.cursor.fetchall()
        except:
            print("Query failed!")


    def get_all_records(self):
        self.__ensure_connection()
        try:
            self.cursor.connection.commit()
            self.cursor.execute(f"SELECT * FROM ModerationActions;")
            return self.cursor.fetchall()
        except:
            print("Query failed!")


    def format_records(self, records):
        self.__ensure_connection()
        result = ""
        if records:
            for record in records:
                readable_date = record["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                if record["lift_time"]:
                    readable_lift_date = record["lift_time"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    readable_lift_date = "empty"
                result += f"{record['id']} || {record['action']} || {readable_date} || {readable_lift_date} \n"

        return result


    def log_user(self, user):
        self.__ensure_connection()
        self.cursor.connection.ping(reconnect=True)
        username = user.username
        first_name = user.first_name

        query = """
        INSERT INTO Users (user_id, username, first_name) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE username = %s, first_name = %s;
        """
        self.cursor.execute(query, (user.id, username, first_name, username, first_name))
        self.cursor.connection.commit()


    def revoke_action(self, user_id, action):
        self.__ensure_connection()
        update_query = """
                UPDATE ModerationActions 
                SET lift_time = %s 
                WHERE user_id = %s AND action = %s AND (lift_time > %s);
                """

        self.cursor.execute(update_query, (datetime.now(), user_id, action, datetime.now()))
        self.cursor.connection.commit()

    def is_user_banned(self, user_id, chat_id):
        self.__ensure_connection()

        query = """
        SELECT 1 FROM ModerationActions 
        WHERE user_id = %s 
          AND chat_id = %s 
          AND action = 'Ban' 
          AND (lift_time > NOW())
        LIMIT 1;
        """

        self.cursor.execute(query, (user_id, chat_id))
        return self.cursor.fetchone() is not None

    def subscribe_user(self, user_id, chat_id):
        self.__ensure_connection()
        try:
            query = "INSERT IGNORE INTO Subscriptions (user_id, chat_id) VALUES (%s, %s);"
            self.cursor.execute(query, (user_id, chat_id))
            self.cursor.connection.commit()
            return True
        except Exception as e:
            print(f"Failed to subscribe user: {e}")
            self.cursor.connection.rollback()
            return False

    def unsubscribe_user(self, user_id, chat_id):
        self.__ensure_connection()
        try:
            query = "DELETE FROM Subscriptions WHERE user_id = %s AND chat_id = %s;"
            self.cursor.execute(query, (user_id, chat_id))
            self.cursor.connection.commit()
            return True
        except Exception as e:
            print(f"Failed to unsubscribe user: {e}")
            self.cursor.connection.rollback()
            return False

    def get_subscribers(self, chat_id):
        self.__ensure_connection()
        try:
            query = "SELECT user_id FROM Subscriptions WHERE chat_id = -1003713767184;"
            self.cursor.execute(query)
            return [row['user_id'] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Failed to fetch subscribers: {e}")
            return []


    def __ensure_connection(self):
        try:
            self.cursor.connection.ping(reconnect=True)
        except (pymysql.MySQLError, AttributeError):
            print("Database connection lost!")
