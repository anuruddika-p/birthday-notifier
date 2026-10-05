# Birthday Notification Manager

**Version:** 1.0  
**For:** Toastmasters Club

This application automatically finds members who have a birthday today and sends them a personalized birthday email.

---

## What This App Does

- Reads member details from an Excel file
- Detects whose birthday is today
- Sends birthday wish emails automatically
- Lets you customize the birthday message

---

## Folder Structure (After Installation)

When you receive the application, you will see a folder like this:

Birthday Notification Manager/

├── Birthday Notification Manager.exe     ← Double-click this to open the app

├── assets/

│   ├── members.xlsx                      ← Put your membership Excel file here

│   └── birthday_message.txt              ← (Optional) Custom birthday message

├── .env                                  ← Email configuration file

└── README.md                             ← This instruction file
text


---

## How to Set Up (First Time Only)

### Step 1: Configure Email

1. Open the file named **`.env`** (you can open it with Notepad).
2. Fill in your email details:

```env
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_16_digit_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**Important for Gmail users**

You must create a Gmail App Password.

Normal Gmail password will not work.
How to create Gmail App Password:

Go to your Google Account → Security
1. Turn on 2-Step Verification
2. Search for App passwords
3. Create a new password for “Mail”
4. Copy the 16-character password and paste it in the .env file

### Step 2: Add Membership Excel File

1. Open the assets folder
2. Place your membership Excel file inside it
3. Rename the file to members.xlsx (recommended)

Required columns in the Excel file:

```
Name
Email
Date of Birth
Mobile Phone / Home Phone (optional)
```
### Step 3: (Optional) Customize Birthday Message

1. Open the file: assets/birthday_message.txt
2. Write your own message
3. Use {name} where you want the member’s name to appear

Example:
```
Dear {name},

Wishing you a very Happy Birthday! 🎉

May this special day bring you joy, success, and good health.

Best regards,
Toastmasters Club
```
If this file is missing, the app will use a default message.

## How to Use the App

1. Double-click Birthday Notification Manager.exe
2. The app will load members automatically
3. Today’s birthdays will be highlighted in orange
4. Click Send Birthday Emails
5. Check the Activity Log to see the results


## Buttons Explained

![img_1.png](img_1.png)

## Important Notes

* The app only sends emails to members whose birthday (month and day) matches today.
* Members without an email address will be skipped.
* You can update the Excel file anytime — just replace it in the assets folder.
* Keep the .env file private. Do not share it with others.

### Troubleshooting

![img_2.png](img_2.png)

### Support
If you face any issues, please contact the developer.

