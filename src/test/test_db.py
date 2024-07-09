from unet.database import UNetDatabase

try:
    db = UNetDatabase('test.db')
    db.run_script("""
    CREATE TABLE IF NOT EXISTS Students
    (
        id INT PRIMARY KEY AUTOINCREMENT,
        first_name VARCHAR(16),
        last_name VARCHAR(16)
    );
                
    INSERT INTO Students (first_name, last_name) VALUES
    ("John", "Doe"),
    ("Will", "Smith");
    """)

    print(db.query('SELECT * FROM Students'))
except Exception as e:
    exit()