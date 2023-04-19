from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,  RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import decouple

# environment variables
TOP_SECRET_KEY = decouple.config('SECRET_KEY')
POSTGRESQL_DATABASE = decouple.config('POSTGRESQL_URL')

app = Flask(__name__)
app.config['SECRET_KEY'] = TOP_SECRET_KEY
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False,
                    force_lower=False, use_ssl=False, base_url=None)


# CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRESQL_DATABASE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))


# CONFIGURE TABLES

# CREATE TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    # posts = relationship("BlogPost", back_populates="author")
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Create reference to the User object, the "posts" refers to the posts' property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Create reference to the User object, the "comments" refers to the posts' property in the User class.
    author = relationship("User", back_populates="comments")
    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"), nullable=False)
    parent_post = relationship("BlogPost", back_populates="comments")


# db.create_all()

# #
# with app.app_context():
#     db.drop_all()
#     db.create_all()

# with app.app_context():
#     db.create_all()


@app.route('/')
def get_all_posts():
    with app.app_context():
        posts = db.session.query(BlogPost).all()
        users = db.session.query(User).all()
    # return render_template("index.html", all_posts=posts, logged_in=True)
    return render_template("index.html", all_posts=posts, current_user=current_user, all_users=users, time=date.today().strftime("%Y"))

@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = db.session.query(BlogPost).get(post_id)
    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=comment_form.content.data,
            author=current_user,
            parent_post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form, time=date.today().strftime("%Y"))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user, time=date.today().strftime("%Y"))


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user, time=date.today().strftime("%Y"))



@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        if db.session.query(User).filter_by(email=register_form.email.data).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        # hash and salt password
        hash_and_salted_password = generate_password_hash(
            password=register_form.password.data,
            method="pbkdf2:sha256",
            salt_length=8,
        )

        new_user = User(
            email=register_form.email.data,
            password=hash_and_salted_password,
            name=register_form.name.data,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        # return redirect(url_for('get_all_posts', name=current_user.name, logged_in=True))
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=register_form, current_user=current_user, time=date.today().strftime("%Y"))


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data

        # Find user by email entered.
        user = db.session.query(User).filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))

        # Password incorrect
        elif not check_password_hash(pwhash=user.password, password=password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))

        else:
            login_user(user)
            # return redirect(url_for("get_all_posts", name=current_user.name, logged_in=True))
            return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=login_form, current_user=current_user, time=date.today().strftime("%Y"))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))



#Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

@app.route("/new-post", methods=["GET", "POST"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():

        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user, time=date.today().strftime("%Y"))


@app.route("/edit-post/<int:post_id>", methods=["GET", "PUT"])
@login_required
@admin_only
def edit_post(post_id):
    post = db.session.query(BlogPost).get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user, is_edit=True, time=date.today().strftime("%Y"))


@app.route("/delete/<int:post_id>", methods=["DELETE"])
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = db.session.query(BlogPost).get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts', current_user=current_user))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
