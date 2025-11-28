from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import select, asc, desc, or_
from books_db import Book, Session, CheckoutEvent  # import from your model file
from flask import abort
from datetime import datetime


app = Flask(__name__)

def get_book_status(events):
    if not events:
        return "Available"

    latest = events[0]  # events already ordered DESC
    if latest.event_type == "checkout":
        return "Checked Out"
    return "Available"

def get_all_books():
    with Session() as session:
        return session.execute(select(Book)).scalars().all()

def is_checked_out(book):
    """Return True if the latest event is a checkout."""
    if not book.checkout_events:
        return False
    latest_event = sorted(book.checkout_events, key=lambda e: e.timestamp)[-1]
    return latest_event.event_type == "checkout"
    
    
@app.route("/")
def index():
    sort = request.args.get("sort", "title")
    order = request.args.get("order", "asc")

    column_map = {
        "title": Book.title,
        "author": Book.author,
        "year": Book.year_of_publication,
        "genre": Book.genre,
        "barcode": Book.barcode_number
    }

    sort_column = column_map.get(sort, Book.title)
    order_func = asc if order == "asc" else desc

    with Session() as session:
        books = session.execute(
            select(Book).order_by(order_func(sort_column))
        ).scalars().all()
        total_books = len(books)
        checked_out_books = sum(1 for book in books if is_checked_out(book))
        available_books = total_books - checked_out_books

    return render_template(
        "index.html",
        books=books,
        current_sort=sort,
        current_order=order,
        total_books=total_books,
        checked_out_books=checked_out_books,
        available_books=available_books
    )
   
@app.route("/book/<int:book_id>")
def book_history(book_id):
    with Session() as session:
        book = session.get(Book, book_id)
        if not book:
            abort(404)

        events = session.execute(
            select(CheckoutEvent)
            .where(CheckoutEvent.book_id == book_id)
            .order_by(CheckoutEvent.timestamp.desc())
        ).scalars().all()

        status = get_book_status(events)

    return render_template(
        "book_history.html",
        book=book,
        events=events,
        status=status
    )


@app.route("/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        genre = request.form["genre"]
        barcode = request.form["barcode"]

        with Session() as session:
            book = Book(
                title=title,
                author=author,
                year_of_publication=int(year) if year else None,
                genre=genre,
                barcode_number=barcode
            )
            session.add(book)
            session.commit()

        return redirect(url_for("index"))

    elif request.method=="GET":
        barcode=request.args.get("barcode")
        if barcode is None: 
            barcode=""
    return render_template("add_book.html", barcode=barcode)

@app.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    with Session() as session:
        book = session.get(Book, book_id)

        if not book:
            abort(404)

        session.delete(book)
        session.commit()

    return redirect(url_for("index"))


@app.route("/checkout/<int:book_id>", methods=["POST"])
def checkout_book(book_id):
    with Session() as session:
        book = session.get(Book, book_id)
        if not book:
            abort(404)

        event = CheckoutEvent(
            book_id=book.id,
            event_type="checkout"
        )

        session.add(event)
        session.commit()

    return redirect(url_for("book_history", book_id=book_id))


@app.route("/checkin/<int:book_id>", methods=["POST"])
def checkin_book(book_id):
    with Session() as session:
        book = session.get(Book, book_id)
        if not book:
            abort(404)

        event = CheckoutEvent(
            book_id=book.id,
            event_type="checkin"
        )

        session.add(event)
        session.commit()

    return redirect(url_for("book_history", book_id=book_id))
    
@app.route("/search", methods=["GET"])
def search_books():
    query = request.args.get("query")

    if not query:
        return redirect(url_for("index"))

    with Session() as session:
        # Try converting query to integer for year search
        try:
            if len(query) > 4:
                raise ValueError
            year_val = int(query)
        except ValueError:
            year_val = None

        books = session.execute(
            select(Book).where(
                or_(
                    Book.title.ilike(f"%{query}%"),
                    Book.author.ilike(f"%{query}%"),
                    Book.genre.ilike(f"%{query}%"),
                    Book.barcode_number.ilike(f"%{query}%"),
                    Book.year_of_publication == year_val if year_val is not None else False 
                )
            )
        ).scalars().all()
        
        total_books = len(books)
        checked_out_books = sum(1 for book in books if is_checked_out(book))
        available_books = total_books - checked_out_books

    if not books:
        print(f"q='{query}'")
        try: 
            barcode_val = int(query) 
            return redirect(url_for("add_book", barcode=barcode_val))
        except ValueError:
        
            return render_template(
                "index.html",
                books=get_all_books(),
                error=f"No books found matching: {query}"
            )

    # If only one result, optionally redirect to its page
    if len(books) == 1:
        return redirect(url_for("book_history", book_id=books[0].id))

       
    return render_template(
        "index.html",
        books=books,
        total_books=total_books,
        checked_out_books=checked_out_books,
        available_books=available_books
    )
    
@app.route("/author/<author_name>")
def author_page(author_name):
    with Session() as session:
        books = session.execute(
            select(Book).where(Book.author.ilike(author_name))
        ).scalars().all()

    return render_template(
        "author.html",
        author_name=author_name,
        books=books
    )
  
@app.route("/checked-out")
def checked_out_books():
    state=request.args.get("state", "checked out")
    with Session() as session:
        books = session.query(Book).all()
        if state=="checked out":
            books_to_show = [book for book in books if is_checked_out(book)]
        else: 
            books_to_show = [book for book in books if not is_checked_out(book)]

    return render_template(
        "checked_out.html",
        books=books_to_show, 
        state=state
    )
  
if __name__ == "__main__":
    app.run(debug=True)
