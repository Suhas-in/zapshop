from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, hashlib, os, json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zapshop.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        role TEXT DEFAULT 'user', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        category TEXT NOT NULL, price INTEGER NOT NULL, image TEXT,
        description TEXT DEFAULT '', clicks INTEGER DEFAULT 0)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        user_name TEXT, user_email TEXT, items TEXT NOT NULL, total INTEGER NOT NULL,
        address TEXT NOT NULL, city TEXT NOT NULL, pincode TEXT NOT NULL,
        phone TEXT NOT NULL, status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS user_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER,
        action TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    try:
        conn.execute("INSERT INTO users(username,email,password,role) VALUES(?,?,?,?)",
                     ("admin","admin@zapshop.com",hash_pw("admin123"),"admin"))
    except: pass
    c = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    if c == 0:
        prods = [
            ("iPhone 15 Pro","Electronics",999,"https://dummyimage.com/300x200/1a1a2e/00d4ff&text=iPhone+15","Latest iPhone with titanium design and A17 Pro chip"),
            ("MacBook Air M3","Electronics",1299,"https://dummyimage.com/300x200/16213e/00d4ff&text=MacBook+Air","Ultra-thin laptop with Apple M3 chip, all-day battery"),
            ("Nike Air Max","Fashion",150,"https://dummyimage.com/300x200/0f3460/e94560&text=Nike+AirMax","Iconic sneakers with Air cushioning for all-day comfort"),
            ("Apple Watch Ultra","Accessories",799,"https://dummyimage.com/300x200/533483/ffffff&text=Apple+Watch","Rugged smartwatch for extreme sports and adventures"),
            ("Sony WH-1000XM5","Electronics",350,"https://dummyimage.com/300x200/2b2d42/ef233c&text=Sony+WH1000","Industry-leading noise canceling wireless headphones"),
            ("Ray-Ban Aviators","Fashion",180,"https://dummyimage.com/300x200/1b4332/52b788&text=Ray-Ban","Classic aviator sunglasses with UV400 protection"),
            ("Osprey Backpack","Accessories",140,"https://dummyimage.com/300x200/3d405b/f4f1de&text=Osprey+Pack","Premium hiking backpack with ergonomic suspension"),
            ("Sony Alpha A7IV","Electronics",1800,"https://dummyimage.com/300x200/264653/2a9d8f&text=Sony+A7IV","Full-frame mirrorless camera with 33MP sensor"),
            ("Levi's 501 Jeans","Fashion",80,"https://dummyimage.com/300x200/1d3557/457b9d&text=Levis+501","Original straight fit jeans, timeless American style"),
            ("Kindle Paperwhite","Electronics",140,"https://dummyimage.com/300x200/2d6a4f/95d5b2&text=Kindle","Waterproof e-reader with 6.8 inch glare-free display"),
        ]
        conn.executemany("INSERT INTO products(name,category,price,image,description) VALUES(?,?,?,?,?)", prods)
    conn.commit(); conn.close()

init_db()

# ── Static files ──────────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
@app.route('/admin.html')
def serve_admin():
    return send_from_directory('.', 'admin.html')
from flask import send_from_directory

# serve frontend files
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/admin")
def admin():
    return send_from_directory(".", "admin.html")
@app.route('/auth')
@app.route('/auth.html')
def serve_auth():
    return send_from_directory('.', 'auth.html')

# ── Health check (admin uses /api/ to test connection) ───────────────────────

@app.route("/api/")
@app.route("/api")
def api_health():
    return jsonify({"status": "ok", "message": "ZapShop API running ⚡"})

# ── AUTH ──────────────────────────────────────────────────────────────────────

@app.route("/auth/signup", methods=["POST"])
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    d = request.get_json() or {}
    username=(d.get("username") or "").strip()
    email=(d.get("email") or "").strip().lower()
    password=d.get("password") or ""
    if not all([username,email,password]): return jsonify({"error":"All fields required"}),400
    if len(password)<6: return jsonify({"error":"Password needs 6+ characters"}),400
    conn=get_db()
    try:
        conn.execute("INSERT INTO users(username,email,password,role) VALUES(?,?,?,?)",(username,email,hash_pw(password),"user"))
        conn.commit()
        u=conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        conn.close()
        return jsonify({"success":True,"user":{"id":u["id"],"username":u["username"],"email":u["email"],"role":u["role"]}})
    except:
        conn.close()
        return jsonify({"error":"Email or username already exists"}),409

@app.route("/auth/login", methods=["POST"])
@app.route("/api/auth/login", methods=["POST"])
def login():
    d = request.get_json() or {}
    email=(d.get("email") or "").strip().lower()
    password=d.get("password") or ""
    if not all([email,password]): return jsonify({"error":"Email and password required"}),400
    conn=get_db()
    u=conn.execute("SELECT * FROM users WHERE email=? AND password=?",(email,hash_pw(password))).fetchone()
    conn.close()
    if not u: return jsonify({"error":"Invalid email or password"}),401
    return jsonify({"success":True,"user":{"id":u["id"],"username":u["username"],"email":u["email"],"role":u["role"]}})

@app.route("/auth/users")
@app.route("/api/auth/users")
def get_users():
    conn=get_db()
    users=conn.execute("SELECT id,username,email,role,created_at FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

# ── PRODUCTS ──────────────────────────────────────────────────────────────────

@app.route("/products")
@app.route("/api/products")
def products():
    conn=get_db()
    data=conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(x) for x in data])

@app.route("/addproducts")
@app.route("/api/addproducts")
def add_products():
    conn=get_db()
    conn.execute("DELETE FROM products")
    prods=[
        ("iPhone 15 Pro","Electronics",999,"https://dummyimage.com/300x200/1a1a2e/00d4ff&text=iPhone+15","Latest iPhone with titanium design and A17 Pro chip"),
        ("MacBook Air M3","Electronics",1299,"https://dummyimage.com/300x200/16213e/00d4ff&text=MacBook+Air","Ultra-thin laptop with Apple M3 chip"),
        ("Nike Air Max","Fashion",150,"https://dummyimage.com/300x200/0f3460/e94560&text=Nike+AirMax","Iconic sneakers with Air cushioning"),
        ("Apple Watch Ultra","Accessories",799,"https://dummyimage.com/300x200/533483/ffffff&text=Apple+Watch","Rugged smartwatch for extreme sports"),
        ("Sony WH-1000XM5","Electronics",350,"https://dummyimage.com/300x200/2b2d42/ef233c&text=Sony+WH1000","Industry-leading noise canceling headphones"),
        ("Ray-Ban Aviators","Fashion",180,"https://dummyimage.com/300x200/1b4332/52b788&text=Ray-Ban","Classic aviator sunglasses UV400"),
        ("Osprey Backpack","Accessories",140,"https://dummyimage.com/300x200/3d405b/f4f1de&text=Osprey+Pack","Premium hiking backpack"),
        ("Sony Alpha A7IV","Electronics",1800,"https://dummyimage.com/300x200/264653/2a9d8f&text=Sony+A7IV","Full-frame mirrorless camera 33MP"),
        ("Levi's 501 Jeans","Fashion",80,"https://dummyimage.com/300x200/1d3557/457b9d&text=Levis+501","Original straight fit jeans"),
        ("Kindle Paperwhite","Electronics",140,"https://dummyimage.com/300x200/2d6a4f/95d5b2&text=Kindle","Waterproof e-reader 6.8 inch"),
    ]
    conn.executemany("INSERT INTO products(name,category,price,image,description) VALUES(?,?,?,?,?)",prods)
    conn.commit(); conn.close()
    return jsonify({"status":"reset ✅"})

@app.route("/addproduct", methods=["POST"])
@app.route("/api/addproduct", methods=["POST"])
def add_product():
    d=request.get_json() or {}
    name=(d.get("name") or "").strip()
    category=d.get("category","")
    price=d.get("price")
    image=d.get("image") or f"https://dummyimage.com/300x200/1a1a2e/00d4ff&text={name.replace(' ','+')}"
    desc=d.get("description","")
    if not all([name,category,price]): return jsonify({"error":"Missing fields"}),400
    conn=get_db()
    conn.execute("INSERT INTO products(name,category,price,image,description) VALUES(?,?,?,?,?)",(name,category,int(price),image,desc))
    conn.commit(); conn.close()
    return jsonify({"status":"added"})

@app.route("/edit/<int:id>", methods=["POST"])
@app.route("/api/edit/<int:id>", methods=["POST"])
def edit_product(id):
    d=request.get_json() or {}
    conn=get_db()
    conn.execute("UPDATE products SET name=?,category=?,price=?,image=?,description=? WHERE id=?",
                 (d.get("name"),d.get("category"),int(d.get("price",0)),d.get("image"),d.get("description",""),id))
    conn.commit(); conn.close()
    return jsonify({"status":"updated"})

@app.route("/delete/<int:id>")
@app.route("/api/delete/<int:id>")
def delete(id):
    conn=get_db()
    conn.execute("DELETE FROM products WHERE id=?",(id,))
    conn.commit(); conn.close()
    return jsonify({"status":"deleted"})

@app.route("/click/<int:id>")
@app.route("/api/click/<int:id>")
def click(id):
    uid=request.args.get("user_id",0)
    conn=get_db()
    conn.execute("UPDATE products SET clicks=clicks+1 WHERE id=?",(id,))
    if uid: conn.execute("INSERT INTO user_history(user_id,product_id,action) VALUES(?,?,?)",(uid,id,"view"))
    conn.commit(); conn.close()
    return jsonify({"status":"ok"})

# ── AI RECOMMENDATIONS ────────────────────────────────────────────────────────

@app.route("/recommend")
@app.route("/api/recommend")
def recommend():
    uid=request.args.get("user_id",0)
    conn=get_db()
    history=[]
    if uid:
        h=conn.execute("""SELECT p.id,p.name,p.category,p.price,h.action,COUNT(*) as freq
            FROM user_history h JOIN products p ON h.product_id=p.id
            WHERE h.user_id=? GROUP BY p.id ORDER BY freq DESC LIMIT 10""",(uid,)).fetchall()
        history=[dict(x) for x in h]
    prods=[dict(p) for p in conn.execute("SELECT * FROM products").fetchall()]
    conn.close()

    if ANTHROPIC_API_KEY and prods:
        try:
            import urllib.request as urlreq
            htxt=f"User history:{json.dumps(history)}" if history else "New user"
            prompt=f"""E-commerce AI for ZapShop.
Products:{json.dumps([{"id":p["id"],"name":p["name"],"category":p["category"],"price":p["price"],"clicks":p["clicks"]} for p in prods])}
{htxt}
Recommend 4 product IDs. Reply ONLY JSON: {{"product_ids":[1,2,3,4],"reason":"one sentence"}}"""
            payload=json.dumps({"model":"claude-sonnet-4-20250514","max_tokens":120,"messages":[{"role":"user","content":prompt}]}).encode()
            req=urlreq.Request("https://api.anthropic.com/v1/messages",data=payload,
                headers={"Content-Type":"application/json","x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01"})
            with urlreq.urlopen(req,timeout=8) as resp:
                res=json.loads(resp.read())
                txt=res["content"][0]["text"].strip()
                if "```" in txt: txt=txt.split("```")[1].lstrip("json").strip()
                ai=json.loads(txt)
                ids=ai.get("product_ids",[])[:4]
                recs=[p for p in prods if p["id"] in ids]
                seen={p["id"] for p in recs}
                for p in sorted(prods,key=lambda x:x["clicks"],reverse=True):
                    if p["id"] not in seen and len(recs)<4: recs.append(p); seen.add(p["id"])
                return jsonify({"products":recs,"reason":ai.get("reason","Personalized for you ✨"),"ai_powered":True})
        except: pass

    conn2=get_db()
    data=conn2.execute("SELECT * FROM products ORDER BY clicks DESC,id DESC LIMIT 4").fetchall()
    conn2.close()
    return jsonify({"products":[dict(x) for x in data],"reason":"Trending right now 🔥","ai_powered":False})

# ── CART ──────────────────────────────────────────────────────────────────────

@app.route("/cart/<int:uid>")
@app.route("/api/cart/<int:uid>")
def cart(uid):
    conn=get_db()
    rows=conn.execute("""SELECT c.id as cart_id,c.quantity,p.id,p.name,p.price,p.image,p.category
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?""",(uid,)).fetchall()
    conn.close()
    items=[dict(r) for r in rows]
    return jsonify({"items":items,"total":sum(i["price"]*i["quantity"] for i in items),"count":len(items)})

@app.route("/cart/add/<int:uid>/<int:pid>", methods=["POST","GET"])
@app.route("/api/cart/add/<int:uid>/<int:pid>", methods=["POST","GET"])
def add_cart(uid,pid):
    conn=get_db()
    conn.execute("UPDATE products SET clicks=clicks+1 WHERE id=?",(pid,))
    ex=conn.execute("SELECT id FROM cart WHERE user_id=? AND product_id=?",(uid,pid)).fetchone()
    if ex: conn.execute("UPDATE cart SET quantity=quantity+1 WHERE id=?",(ex["id"],))
    else: conn.execute("INSERT INTO cart(user_id,product_id,quantity) VALUES(?,?,1)",(uid,pid))
    conn.execute("INSERT INTO user_history(user_id,product_id,action) VALUES(?,?,?)",(uid,pid,"cart"))
    conn.commit(); conn.close()
    return jsonify({"status":"added"})

@app.route("/cart/remove/<int:uid>/<int:cart_id>")
@app.route("/api/cart/remove/<int:uid>/<int:cart_id>")
def remove_cart(uid,cart_id):
    conn=get_db()
    conn.execute("DELETE FROM cart WHERE id=? AND user_id=?",(cart_id,uid))
    conn.commit(); conn.close()
    return jsonify({"status":"removed"})

@app.route("/cart/clear/<int:uid>")
@app.route("/api/cart/clear/<int:uid>")
def clear_cart(uid):
    conn=get_db()
    conn.execute("DELETE FROM cart WHERE user_id=?",(uid,))
    conn.commit(); conn.close()
    return jsonify({"status":"cleared"})

# ── ORDERS ────────────────────────────────────────────────────────────────────

@app.route("/order/place", methods=["POST"])
@app.route("/api/order/place", methods=["POST"])
def place_order():
    d=request.get_json() or {}
    uid=d.get("user_id")
    address=(d.get("address") or "").strip()
    city=(d.get("city") or "").strip()
    pincode=(d.get("pincode") or "").strip()
    phone=(d.get("phone") or "").strip()
    if not all([uid,address,city,pincode,phone]): return jsonify({"error":"All fields required"}),400
    conn=get_db()
    u=conn.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    rows=conn.execute("""SELECT c.quantity,p.id,p.name,p.price,p.image,p.category
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?""",(uid,)).fetchall()
    if not rows: conn.close(); return jsonify({"error":"Cart is empty"}),400
    items=[dict(r) for r in rows]
    total=sum(i["price"]*i["quantity"] for i in items)
    conn.execute("""INSERT INTO orders(user_id,user_name,user_email,items,total,address,city,pincode,phone,status)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",(uid,u["username"],u["email"],json.dumps(items),total,address,city,pincode,phone,"pending"))
    conn.execute("DELETE FROM cart WHERE user_id=?",(uid,))
    conn.commit()
    oid=conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
    conn.close()
    return jsonify({"status":"success","order_id":oid,"total":total})

@app.route("/orders/user/<int:uid>")
@app.route("/api/orders/user/<int:uid>")
def user_orders(uid):
    conn=get_db()
    rows=conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",(uid,)).fetchall()
    conn.close()
    orders=[]
    for o in rows:
        od=dict(o); od["items"]=json.loads(od["items"]); orders.append(od)
    return jsonify(orders)

@app.route("/orders/all")
@app.route("/api/orders/all")
def all_orders():
    conn=get_db()
    rows=conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    orders=[]
    for o in rows:
        od=dict(o); od["items"]=json.loads(od["items"]); orders.append(od)
    return jsonify(orders)

@app.route("/orders")
@app.route("/api/orders")
def get_orders():
    conn=get_db()
    rows=conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    orders=[]
    for o in rows:
        od=dict(o); od["items"]=json.loads(od["items"]); orders.append(od)
    return jsonify(orders)

@app.route("/order/status/<int:oid>", methods=["POST"])
@app.route("/api/order/status/<int:oid>", methods=["POST"])
def update_status(oid):
    d=request.get_json() or {}
    conn=get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?",(d.get("status","pending"),oid))
    conn.commit(); conn.close()
    return jsonify({"status":"updated"})

@app.route("/update-order/<int:id>", methods=["POST"])
@app.route("/api/update-order/<int:id>", methods=["POST"])
def update_order(id):
    d=request.get_json() or {}
    conn=get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?",(d.get("status"),id))
    conn.commit(); conn.close()
    return jsonify({"success":True})

# ── STATS (fixed: now includes total_cart_items) ──────────────────────────────

@app.route("/stats")
@app.route("/api/stats")
def stats():
    conn=get_db()
    tp=conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    tu=conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    to=conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    tc=conn.execute("SELECT COALESCE(SUM(quantity),0) as c FROM cart").fetchone()["c"]
    rev=conn.execute("SELECT COALESCE(SUM(total),0) as r FROM orders WHERE status!='cancelled'").fetchone()["r"]
    top=conn.execute("SELECT name,clicks FROM products ORDER BY clicks DESC LIMIT 5").fetchall()
    cats=conn.execute("SELECT category,COUNT(*) as count FROM products GROUP BY category").fetchall()
    pend=conn.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'").fetchone()["c"]
    conn.close()
    return jsonify({
        "total_products": tp,
        "total_users": tu,
        "total_orders": to,
        "total_cart_items": tc,
        "revenue": rev,
        "pending_orders": pend,
        "top_clicked": [dict(x) for x in top],
        "categories": [dict(x) for x in cats]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
