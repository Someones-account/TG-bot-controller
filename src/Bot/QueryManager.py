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
                if record["lift_time"]:
                    readable_lift_date = record["lift_time"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    readable_lift_date = "empty"
                print(f"{record['id']} || {record['action']} || {readable_date} || {readable_lift_date}")

