import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html", database=db.execute("SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ? GROUP BY symbol", session["user_id"]), cash=db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        if request.form.get("symbol"):
            pass
        else:
            return apology("Please provide symbol.")

        if lookup(request.form.get("symbol").upper()) == None:
            return apology("That symbol is invalid.")

        for char in request.form.get("shares"):
            if char.isnumeric():
                if float(request.form.get("shares")) < 0:
                    return apology("Invalid number of shares.")
            else:
                return apology("Invalid number of shares.")

        if db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"] < (int(request.form.get("shares")) * lookup(request.form.get("symbol").upper())["price"]):
            return apology("Insufficient funds.")

        db.execute("UPDATE users SET cash = ? WHERE id = ?", round(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[
                   0]["cash"] - float(request.form.get("shares")) * lookup(request.form.get("symbol").upper())["price"], 2), session["user_id"])

        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)", session["user_id"], lookup(request.form.get(
            "symbol").upper())["symbol"], float(request.form.get("shares")), round(lookup(request.form.get("symbol").upper())["price"], 2), datetime.now())

        flash("Purchase Successful!")

        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return render_template("history.html", transactions=db.execute("SELECT * FROM transactions WHERE user_id = ?", session["user_id"]))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        if request.form.get("symbol"):
            pass
        else:
            return apology("Please provide symbol")

        if lookup(request.form.get("symbol").upper()) == None:
            return apology("That symbol is invalid")

        return render_template("quoted.html", name=lookup(request.form.get("symbol").upper())["name"], price=lookup(request.form.get("symbol").upper())["price"], symbol=lookup(request.form.get("symbol").upper())["symbol"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        if request.form.get("username"):
            pass
        else:
            return apology("Username Required")

        if request.form.get("password"):
            pass
        else:
            return apology("Password Required")

        if request.form.get("confirmation"):
            pass
        else:
            return apology("Must Give Confirmation")

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords are not the same")

        try:
            user = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get(
                "username"), generate_password_hash(request.form.get("password")))
        except:
            return apology("Username already exists")

        session["user_id"] = user
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html", symbols=[stock["symbol"] for stock in db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", session["user_id"])])
    else:
        if not request.form.get("symbol"):
            return apology("Please provide symbol.")

        if lookup(request.form.get("symbol").upper()) == None:
            return apology("Please provide symbol.")

        if float(request.form.get("shares")) < 0:
            return apology("Invalid number of shares.")

        if float(request.form.get("shares")) > db.execute("SELECT shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", session["user_id"], request.form.get("symbol"))[0]["shares"]:
            return apology("You Do Not Have This Amount Od Shares")

        db.execute("UPDATE users SET cash = ? WHERE id = ?", db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[
                   0]["cash"] + (float(request.form.get("shares")) * lookup(request.form.get("symbol").upper())["price"]), session["user_id"])

        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)", session["user_id"], lookup(request.form.get(
            "symbol").upper())["symbol"], (-1) * float(request.form.get("shares")), lookup(request.form.get("symbol").upper())["price"], datetime.now())

        flash("Sale Successful!")

        return redirect("/")


@app.route("/add_cash", methods=["GET", "POST"])
@login_required
def add_cash():
    """Allow user to add additional cash to their account."""
    if request.method == "GET":
        return render_template("add_cash.html")
    else:
        if float(request.form.get("additional_cash")):
            pass
        else:
            return apology("Please provide a valid amount of cash.")

        db.execute("UPDATE users SET cash = ? WHERE id = ?", db.execute("SELECT cash FROM users WHERE id = ?",
                   session["user_id"])[0]["cash"] + float(request.form.get("additional_cash")), session["user_id"])

        return redirect("/")
