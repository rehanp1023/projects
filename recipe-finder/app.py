from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from cs50 import SQL
import requests

# Simple secret key for development
app = Flask(__name__)
app.config['SECRET_KEY'] = 'developmentsecretkey'
db = SQL("sqlite:///recipes.db")

SPOONACULAR_API_KEY = 'cd31b9c317be4ef4889d47e752411e51'
OPENAI_API_KEY = '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'

# Initialize the database
@app.before_request
def init_db():
    db.execute('''CREATE TABLE IF NOT EXISTS users ( id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL )''')
    db.execute('''CREATE TABLE IF NOT EXISTS recipes ( id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, details TEXT NOT NULL )''')
    db.execute('''CREATE TABLE IF NOT EXISTS favorites ( id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (recipe_id) REFERENCES recipes (id) )''')


@app.route('/')
def index():
    return render_template('index.html')

# Signup feature
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', username, hashed_password)
            flash('Account created successfully', 'success')
            return render_template('login.html')
        except:
            flash('Username already exists', 'danger')
            return render_template('login.html')
    return render_template('signup.html')

# Login feature
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Forgets any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensures username was submitted
        if not request.form.get("username"):
            flash('Invalid username', 'danger')
            return redirect("/")


        # Ensures password was submitted
        elif not request.form.get("password"):
            flash('Invalid password', 'danger')
            return redirect("/")


        # Queries database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensures username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["password"], request.form.get("password")
        ):
            flash('Username and/or Password does not exist', 'danger')
            return render_template('login.html')

        # Remembers which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirects user to home page
        return render_template('dashboard.html')
    else:
        return render_template('login.html')

# Logs User Out
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))


# Initial route for recipe query
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        recipes = search_recipes(ingredients)
        return render_template('dashboard.html', recipes=recipes)
    return render_template('dashboard.html')

# Showcases the result of the query
@app.route('/recipes', methods=['GET', 'POST'])
def recipes():
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        recipes = search_recipes(ingredients)
        return render_template('recipes.html', recipes=recipes)
    else:
        return render_template('recipes.html')

def search_recipes(ingredients):
    url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={ingredients}&number=5&apiKey={SPOONACULAR_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response Text: {response.text}")
        return []
    try:
        data = response.json()
    except ValueError as e:
        print("JSON Decode Error:", e)
        print("Response Text:", response.text)
        return []
    recipes = []
    for item in data:
        recipe_id = item['id']
        recipe_title = item['title']
        recipe_details = get_recipe_details(recipe_id, response)
        gpt_details = get_chatgpt_recipe_description(recipe_title)
        db.execute('INSERT INTO recipes (title, description, details) VALUES (?, ?, ?)', recipe_title, recipe_details['summary'], gpt_details)
        recipe = {
            'id': db.execute('SELECT id FROM recipes WHERE title = ? AND description = ?', recipe_title, recipe_details['summary'])[0]['id'],
            'title': recipe_title,
            'description': recipe_details['summary'],
            'details': gpt_details
        }
        recipes.append(recipe)
    return recipes

def get_recipe_details(recipe_id, response):
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/summary?apiKey={SPOONACULAR_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response Text: {response.text}")
        return []
    try:
        data = response.json()
        return data
    except ValueError as e:
        print("JSON Decode Error:", e)
        print("Response Text:", response.text)
        return []

def get_chatgpt_recipe_description(recipe_title):

    CHATGPT_API_KEY = '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'

    headers = {
        'Authorization': f'Bearer {CHATGPT_API_KEY}', 'Content-Type': 'application/json'
    }
    prompt = f"Provide a detailed description of the recipe for {recipe_title}, focusing on the taste, texture, and whether it is savory or sweet."
    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500, 'temperature': 0.7
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data,)
    response_data = response.json()
    if 'choices' in response_data and response_data['choices']:
        food_description = response_data['choices'][0]['message']['content']
    else:
        food_description = 'Description not available'
    return food_description


# Places recipes into favorites
@app.route('/favorite/<int:recipe_id>')
def favorite(recipe_id):
    if 'user_id' in session:
        user_id = session['user_id']
        db.execute('INSERT INTO favorites (user_id, recipe_id) VALUES (?, ?)', user_id, recipe_id)
        flash('Recipe added to favorites', 'success')
    return redirect(url_for('recipes'))

# Removes recipes from favorites
@app.route('/remove/<int:recipe_id>')
def remove(recipe_id):
    if 'user_id' in session:
        user_id = session['user_id']
        db.execute('DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?', user_id, recipe_id)
        flash('Recipe removed from favorites', 'success')
    return redirect(url_for('favorites'))

# Shocases all recipes in favorites to the user
@app.route('/favorites')
def favorites():
    if 'user_id' in session:
        user_id = session['user_id']
        favorites = db.execute('SELECT recipes.id, recipes.title, recipes.description FROM recipes INNER JOIN favorites ON recipes.id = favorites.recipe_id WHERE favorites.user_id = ?', user_id)
        return render_template('favorites.html', favorites=favorites)
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=False)
