class QueryManager:
    def __init__(self, cursor):
        self.cursor = cursor


    def add_user(self, user_id, action):
        try:
            self.cursor.execute(f"INSERT INTO ModerationActions (user_id, action) VALUES ({user_id}, {action});")
        except:
            print("Query failed!")


    def get_all_records(self):
        try:
            self.cursor.execute(f"SELECT * FROM ModerationActions;")
            return self.cursor.fetchall()
        except:
            print("Query failed!")


    def display_records(self):
        records = self.get_all_records()
        if records:
            for record in records:
                readable_date = record["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"{record['id']} || {record['action']} || {readable_date}")
