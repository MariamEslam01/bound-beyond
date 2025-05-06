import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import pandas as pd
import torch
import json
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

app = Flask(__name__)
app.secret_key = "beyond123"

# Load data
base_movie_poster_url = "https://image.tmdb.org/t/p/w500"

books = pd.read_csv("books_cleaned2.csv")
books = books.rename(columns={'description': 'content'})
books['type'] = 'book'
books['image_url'] = None

movies = pd.read_csv("movies_cleaned.csv")
movies = movies.rename(columns={'overview': 'content', 'release_year': 'published_year'})
movies['type'] = 'movie'
movies['image_url'] = base_movie_poster_url + movies['poster_path'].fillna("")
movies['author'] = None

books_subset = books[['title', 'content', 'author', 'published_year', 'average_rating', 'genres', 'image_url', 'type']]
movies_subset = movies[['title', 'content', 'published_year', 'average_rating', 'genres', 'image_url', 'type', 'author']]
combined = pd.concat([books_subset, movies_subset], ignore_index=True)
combined['content'] = combined['content'].fillna('')

# Genre list
all_genres = sorted([
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary',
    'Drama', 'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery',
    'Romance', 'Science Fiction', 'TV Movie', 'Thriller', 'War', 'Western'
])

# Load embedding model
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# User storage
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

#ROUTES

@app.route("/")
def home():
    return render_template("index.html", user=session.get("user"), name=session.get("name"))

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return redirect(url_for('home'))

    result = combined[combined['title'].str.lower() == query.lower()]
    if result.empty:
        return render_template("not_found.html", query=query, user=session.get("user"))

    row = result.iloc[0]
    return redirect(url_for("details", title=row["title"], type=row["type"]))

@app.route("/genres")
def genres():
    media_type = request.args.get("type", "book")
    return render_template("genres.html", type=media_type, genres=all_genres, user=session.get("user"))

@app.route("/recommendations")
def recommendations_page():
    return render_template("recommendations.html", user=session.get("user"))

@app.route("/details")
def details():
    return render_template("details.html", user=session.get("user"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Validate email domain
        if not (username.endswith("@gmail.com") or username.endswith("@acuq.ae")):
            flash("Email must end with @gmail.com or @acuq.ae", "danger")
            return redirect(url_for("register"))

        # Validate password strength
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{6,}$', password):
            flash("Password must include uppercase, lowercase, number, and a special character.", "danger")
            return redirect(url_for("register"))

        users = load_users()
        if username in users:
            flash("Username already exists. Please choose another.", "danger")
            return redirect(url_for("register"))

        # Store full user info
        users[username] = {
            "name": name,
            "password": password
        }

        save_users(users)
        flash("Account created successfully. Please login!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        users = load_users()

        if username not in users:
            flash("This user is not registered. Please sign up first.", "warning")
            return redirect(url_for("login"))

        if users[username]["password"] != password:
            flash("Incorrect password. Please try again.", "danger")
            return redirect(url_for("login"))

        # Login successful
        session["user"] = username
        session["name"] = users[username]["name"]

        flash("Logged in successfully!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# ========== API ENDPOINTS ==========

@app.route("/api/recommend", methods=["GET"])
def recommend():
    media_type = request.args.get('type')
    genre = request.args.get('genre')

    filtered = combined[(combined['type'] == media_type.lower()) &
                        (combined['genres'].str.contains(genre, case=False, na=False))]

    if filtered.empty:
        return jsonify([])

    vectors = model.encode(filtered['content'].tolist())
    knn = NearestNeighbors(n_neighbors=20, metric='cosine')
    knn.fit(vectors)

    query_vector = model.encode([genre])
    distances, indices = knn.kneighbors(query_vector)

    recommendations = []
    for idx in indices[0]:
        item = filtered.iloc[idx]
        image = item['image_url']
        if pd.isna(image) or image == "":
            image = "/static/images/Books_Default.png" if item['type'] == "book" else "/static/images/2503508.png"

        recommendations.append({
            "title": item['title'],
            "author": item.get('author'),
            "year": int(item['published_year']) if not pd.isna(item['published_year']) else "Unknown",
            "rating": float(item.get('average_rating', 0)),
            "image": image,
            "content": item['content'],
            "type": item['type']
        })

    return jsonify(recommendations)

@app.route("/api/details", methods=["GET"])
def get_details():
    title = request.args.get('title')
    media_type = request.args.get('type')

    item = combined[(combined['title'] == title) & (combined['type'] == media_type.lower())]
    if item.empty:
        return jsonify({'error': 'Item not found'}), 404

    row = item.iloc[0]
    return jsonify({
        "title": row['title'],
        "author": row.get('author'),
        "year": int(row['published_year']) if not pd.isna(row['published_year']) else "Unknown",
        "rating": float(row.get('average_rating', 0)),
        "image": row['image_url'],
        "content": row['content'],
        "type": row['type']
    })

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

