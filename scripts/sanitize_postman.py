import os

directories = [
    "/Users/Apple16/Desktop/SS_MIS/postman_collections",
    "/Users/Apple16/Desktop/SS_MIS_Postman_Collections"
]

replacements = [
    ('\\"Admin@123456\\"', '\\"your_password_here\\"'),
    ('\\"Cashier@123456\\"', '\\"your_password_here\\"'),
    ('\\"MobileDev@123456\\"', '\\"your_password_here\\"'),
    ('\\"username\\": \\"admin\\"', '\\"username\\": \\"your_username_here\\"'),
    ('"Admin@123456"', '"your_password_here"'),
    ('"Cashier@123456"', '"your_password_here"'),
    ('"MobileDev@123456"', '"your_password_here"')
]

for d in directories:
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith(".json"):
                fpath = os.path.join(d, f)
                with open(fpath, "r", encoding="utf-8") as file:
                    content = file.read()
                
                for old_val, new_val in replacements:
                    content = content.replace(old_val, new_val)
                
                with open(fpath, "w", encoding="utf-8") as file:
                    file.write(content)

print("Sanitized all passwords and credentials in Postman collections.")
