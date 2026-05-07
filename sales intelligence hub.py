import streamlit as st
import pandas as pd
import mysql.connector

st.set_page_config(page_title="Sales Intelligence Hub", layout="wide")

# ---------------- DB ----------------
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="niki@2018",
        database="sales_management_system"
    )

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password, role, branch_id FROM users WHERE username=%s",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and password == user[0]:
            st.session_state.logged_in = True
            st.session_state.role = user[1]
            st.session_state.branch_id = user[2]
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------- LOGOUT ----------------
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- LOAD BRANCH ----------------
@st.cache_data
def load_branches():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM branches", conn)
    conn.close()
    return df

branch_df = load_branches()

# ---------------- HEADER ----------------
st.title("📊 Sales Intelligence Hub")

# ---------------- FILTERS ----------------
st.sidebar.header("🔍 Filters")
start_date = st.sidebar.date_input("Start Date",value=pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date")
product_filter = st.sidebar.selectbox("Product", ["All","DS","DA","BA","FSD"])

# ---------------- SUPER ADMIN FILTER ----------------
selected_branch_id = None
selected_branch_name = None

if st.session_state.role == "Super Admin":
    col1, col2 = st.columns(2)

    with col1:
        selected_branch_name = st.selectbox(
            "Branch Name", ["All"] + list(branch_df['branch_name'])
        )

# ---------------- FILTER QUERY ----------------
def build_filter():
    conditions = []

    if st.session_state.role != "Super Admin":
        conditions.append(f"cs.branch_id = {st.session_state.branch_id}")

    if selected_branch_id != "All" and selected_branch_id:
        conditions.append(f"cs.branch_id = {selected_branch_id}")

    if selected_branch_name != "All" and selected_branch_name:
        branch_id = branch_df[
            branch_df['branch_name'] == selected_branch_name
        ]['branch_id'].values[0]
        conditions.append(f"cs.branch_id = {branch_id}")

    if start_date:
        conditions.append(f"DATE(cs.date) >= '{start_date}'")

    if end_date:
        conditions.append(f"DATE(cs.date) <= '{end_date}'")

    if product_filter != "All":
        conditions.append(f"cs.product_name = '{product_filter}'")

    return " WHERE " + " AND ".join(conditions) if conditions else ""

# ---------------- MENU ----------------
menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard","Add Sale","Add Payment","View Sales","Upload CSV","SQL Analyzer"]
)

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    conn = get_connection()#creates DB CONNECTION
    where = build_filter()

    total = pd.read_sql(f"""
    SELECT SUM(gross_sales) FROM customer_sales cs {where}
    """, conn).iloc[0,0] or 0

    received = pd.read_sql(f"""
    SELECT SUM(ps.amount_paid)
    FROM payment_splits ps
    JOIN customer_sales cs ON cs.sale_id = ps.sale_id
    {where}
    """, conn).iloc[0,0] or 0

    pending = total - received

    c1,c2,c3 = st.columns(3)
    c1.metric("Total", total)
    c2.metric("Received", received)
    c3.metric("Pending", pending)

    conn.close()#STORES DB CONNECTION

    conn = get_connection()

    df = pd.read_sql(f"""
    SELECT cs.sale_id,b.branch_name,cs.date,cs.name,
           cs.mobile_number,cs.product_name,cs.gross_sales
    FROM customer_sales cs
    JOIN branches b ON cs.branch_id=b.branch_id
    {build_filter()}
    ORDER BY cs.date DESC
    """, conn)

    st.dataframe(df)

    conn.close()


# ---------------- ADD SALE ----------------
elif menu == "Add Sale":
    conn = get_connection()#creates DB CONNECTION

    if st.session_state.role == "Super Admin":
        branch_map = dict(zip(branch_df.branch_name, branch_df.branch_id))
        branch = st.selectbox("Branch", list(branch_map.keys()))
        branch_id = branch_map[branch]
    else:
        branch_id = st.session_state.branch_id

    name = st.text_input("Customer Name")
    mobile = st.text_input("Mobile")
    product = st.selectbox("Product", ["DS","DA","BA","FSD"])
    gross = st.number_input("Gross", min_value=0)

    if st.button("Add"):
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO customer_sales
        (branch_id,date,name,mobile_number,product_name,gross_sales)
        VALUES (%s,CURDATE(),%s,%s,%s,%s)
        """,(branch_id,name,mobile,product,gross))
        conn.commit()
        st.success("Sale Added")

    conn.close()

# ---------------- ADD PAYMENT ----------------
elif menu == "Add Payment":
    conn = get_connection()#creates DB CONNECTION

    df = pd.read_sql("SELECT sale_id,name FROM customer_sales", conn)

    sale = st.selectbox("Sale", df['sale_id'])
    amt = st.number_input("Amount", min_value=0)
    method = st.selectbox("Method", ["Cash","UPI","Card"])

    if st.button("Pay"):
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO payment_splits
        VALUES (NULL,%s,CURDATE(),%s,%s)
        """,(sale,amt,method))
        conn.commit()
        st.success("Payment Added")

    conn.close()

# ---------------- SQL ANALYZER ----------------
elif menu == "SQL Analyzer":

    if st.session_state.role != "Super Admin":
        st.error("Access Denied")
        st.stop()

    queries = [
        "Retrieve all records from the customer_sales table",
        "Retrieve all records from the branches table.",
        "Retrieve all records from the payment_splits table.",
        "Retrieve all sales belonging to the Chennai branch.",
        "Find the average gross sales amount.",
        "Calculate the total received amount across all sales.",
        "Calculate the total pending amount across all sales.",
        "Count the total number of sales per branch.",
        "Retrieve sales details along with the branch name.",
        "Retrieve sales details along with total payment received (using payment_splits).",
        "Show branch-wise total gross sales (using JOIN & GROUP BY).",
        "Display sales along with payment method used.",
        "Find sales where the pending amount is greater than 5000.",
        "Retrieve top 3 highest gross sales.",  
        "Retrieve monthly sales summary (group by month & year)."
    ]

    q = st.selectbox("Select Query", queries)

    if st.button("Run"):
        conn = get_connection()#creates DB CONNECTION
        if q == "Retrieve all records from the customer_sales table":
            query="Select * from customer_sales"
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve all records from the branches table.":
            query="Select * from branches"
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve all records from the payment_splits table.":
            query="Select * from payment_splits"
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve all sales belonging to the Chennai branch.":
            query="""
            SELECT cs.*
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id=b.branch_id
            WHERE b.branch_name='Chennai'
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Find the average gross sales amount.":
            query="SELECT AVG(gross_sales) AS average_gross_sales FROM customer_sales"
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Calculate the total received amount across all sales.": 
            query="SELECT SUM(amount_paid) AS total_received FROM payment_splits"
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Calculate the total pending amount across all sales.":
            query="""
            SELECT 
                (SELECT SUM(gross_sales) FROM customer_sales) - 
                (SELECT SUM(amount_paid) FROM payment_splits) AS total_pending
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Count the total number of sales per branch.":
            query="""
            SELECT b.branch_name, COUNT(*) AS total_sales
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id=b.branch_id
            GROUP BY b.branch_name
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve sales details along with the branch name.":
            query="""
            SELECT cs.*, b.branch_name
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id=b.branch_id
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve sales details along with total payment received (using payment_splits).":
            query="""
            SELECT cs.*, ps.total_payment
            FROM customer_sales cs
            JOIN (
                SELECT sale_id, SUM(amount_paid) AS total_payment
                FROM payment_splits
                GROUP BY sale_id
            ) ps ON cs.sale_id = ps.sale_id
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Show branch-wise total gross sales (using JOIN & GROUP BY).":    
            query="""
            SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sales
            FROM customer_sales cs
            JOIN branches b ON cs.branch_id=b.branch_id
            GROUP BY b.branch_name
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Display sales along with payment method used.":
            query="""
            SELECT cs.*, ps.payment_method
            FROM customer_sales cs
            JOIN payment_splits ps ON cs.sale_id=ps.sale_id
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Find sales where the pending amount is greater than 5000.":
            query="""
            SELECT cs.*
            FROM customer_sales cs
            WHERE cs.gross_sales - (
                SELECT SUM(amount_paid)
                FROM payment_splits
                WHERE sale_id = cs.sale_id
            ) > 5000
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve top 3 highest gross sales.":
            query="""
            SELECT *
            FROM customer_sales
            ORDER BY gross_sales DESC
            LIMIT 3
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        elif q == "Retrieve monthly sales summary (group by month & year).":
            query="""
            SELECT 
                YEAR(date) AS year, 
                MONTH(date) AS month, 
                SUM(gross_sales) AS total_gross_sales
            FROM customer_sales
            GROUP BY YEAR(date), MONTH(date)
            ORDER BY year, month
            """
            df = pd.read_sql(query, conn)
            st.dataframe(df)
            conn.close()
        
# ---------------- CSV ----------------
elif menu == "Upload CSV":
    file = st.file_uploader("Upload CSV")

    if file:
        df = pd.read_csv(file)
        st.dataframe(df)

        if st.button("Insert"):
            conn = get_connection()
            cursor = conn.cursor()

            for _, row in df.iterrows():
                cursor.execute("""
                INSERT INTO customer_sales
                (branch_id,date,name,mobile_number,product_name,gross_sales)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,(row['branch_id'],row['date'],row['name'],
                     row['mobile_number'],row['product_name'],row['gross_sales']))

            conn.commit()
            conn.close()
            st.success("Uploaded Successfully")