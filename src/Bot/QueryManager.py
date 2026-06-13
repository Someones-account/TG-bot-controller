from datetime import datetime


class QueryManager:
    def __init__(self, cursor):
        self.cursor = cursor


    def create_entry(self, user_id, action, lift_time):
        try:
            query = "INSERT INTO ModerationActions (user_id, action, lift_time) VALUES (%s, %s, %s);"
            self.cursor.execute(query, (user_id, action, lift_time))
            self.cursor.connection.commit()

        except:
            print("Query failed!")


    def get_banned_users(self):
        try:
            query = "SELECT * FROM ModerationActions WHERE action = 'Ban' AND lift_time > %s;"
            self.cursor.execute(query, (datetime.now(),))
            return self.cursor.fetchall()
        except:
            print("Query failed!")


    def get_all_records(self):
        try:
            self.cursor.connection.commit()
            self.cursor.execute(f"SELECT * FROM ModerationActions;")
            return self.cursor.fetchall()
        except:
            print("Query failed!")


    def format_records(self, records):
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
        username = user.username
        first_name = user.first_name

        upsert_query = """
        INSERT INTO Users (user_id, username, first_name) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE username = %s, first_name = %s;
        """
        self.cursor.execute(upsert_query, (user.id, username, first_name, username, first_name))
        self.cursor.connection.commit()

    def delete_entry(self, log_id):
        try:
            # SQL command to delete a specific row based on its ID
            query = "DELETE FROM ModerationActions WHERE id = %s;"
            self.cursor.execute(query, (log_id,))
            self.cursor.connection.commit()
        except Exception as e:
            print(f"Delete failed: {e}")