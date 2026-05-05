# 📱 Diamond Tree Ventures

**Developer:** Kipngeno Abednego  
**Project Type:** Capstone Project  
**Deployment:** Live on [diamondtreeventures.top](https://diamondtreeventures.top)

---

## 🔍 Overview

**Diamond Tree Ventures** is a role-based mobile device sales and management platform designed to streamline commerce and enhance customer engagement. It provides tailored experiences for three distinct user roles:

### 👤 Customers
- Browse devices and view detailed specifications  
- Place cash or credit orders  
- Track orders with real-time status notifications  
- Manage delivery addresses and personal profiles  
- Access support and view service history  

### 🧑‍💼 Staff
- Manage and fulfill customer orders  
- Mark orders as **Awaiting Approval**, **Completed**, or **Rejected** (with reason)  
- View assigned tasks via a dedicated staff dashboard  
- Receive real-time alerts and updates  

### 🛠️ Admins
- Monitor sales activity and manage customer service requests  
- Assign staff to orders and track responsibilities  
- Add, update, and manage device inventory (IMEI-based)  
- Manage user accounts (add, activate, deactivate)  
- Approve or reject pending orders  
- Customize workflow processes  
- Access platform-wide notifications, analytics, and reports  

---

## ✅ Features Implemented

### 🔧 Core System
- 🟢 Successfully deployed on **diamondtreeventures.top**

### 🧑‍💼 Admin Functionality
- Add devices to inventory and public homepage  
- Manage user accounts (add, deactivate)  
- View customer orders and assigned staff  
- Approve or disapprove orders  

### 👷 Staff Functionality
- View and update customer order statuses  
- Reject orders with specified reasons  
- View assigned orders on dashboard  

### 👥 Customer Functionality
- Browse available devices  
- Add devices to cart and place orders  
- Track orders from dashboard  
- Register, log in, and edit profile  
- View successful order history  

---

## 🔧 Pending Tasks (TODO)

- [ ] Improve mobile responsiveness (UI/UX on smaller screens)  
- [ ] Integrate barcode scanner for automatic device detail extraction  
- [ ] Implement receipt/invoice generation  
- [ ] Add "Forgot Password" recovery functionality  
- [ ] Complete reporting and sales management dashboard  

---

## � Setup Instructions

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd dtv-admin-panel
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database:**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

6. **Create admin user:**
   ```bash
   python create_admin.py
   ```

7. **Run the application:**
   ```bash
   python run.py
   ```

### Database Configuration

This project supports both SQLite (development) and PostgreSQL (production):

- **SQLite (Default for development):**
  - Set `DB_TYPE=sqlite` in your `.env` file
  - Database file will be created as `app.db` in the project root
  - No additional setup required

- **PostgreSQL (For production):**
  - Set `DB_TYPE=postgresql` in your `.env` file
  - Configure `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
  - Or use `DATABASE_URL` for connection string

---

## �🛠️ Tech Stack

- **Backend:** Flask 3.1.1, Flask-Login, SQLAlchemy  
- **Frontend:** Jinja2 Templates, Bootstrap 5  
- **Database:** SQLite (development), PostgreSQL (production)  
- **Deployment:** Render  

---

## 📬 Contact

For inquiries or feedback, please reach out to:  
**Kipngeno Abednego** — [Your email/contact info here]

---

> This project was developed as part of a capstone for educational and portfolio purposes.
