from flask import Flask, redirect, request, render_template, url_for, send_from_directory, jsonify, make_response
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from werkzeug.utils import secure_filename
from passlib.hash import sha512_crypt
from random import randint
from time import asctime
from functools import wraps
import pickle
import os

def load_database():
    if not os.path.exists("db/db.pickle"):
        return {}
    with open("db/db.pickle", "rb") as dbfile:
        return pickle.load(dbfile)

def save_database(database):
    os.makedirs('db', exist_ok=True)
    with open('db/db.pickle', 'wb') as f:
        pickle.dump(database, f)

def ensure_content_log():
    os.makedirs('db', exist_ok=True)
    os.makedirs('db/contents', exist_ok=True)
    if not os.path.exists('db/content-log.log'):
        with open('db/content-log.log', 'w') as f:
            pass

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = "nikhilisalpha966313022001"

# Initialize Flask-RESTX
api = Api(app, version='1.0', title='Social Media API',
    description='A social media API for managing posts',
    doc='/api/docs',
    default='posts',
    default_label='Post operations'
)

# Define models for Swagger documentation
post_model = api.model('Post', {
    'filename': fields.String(required=True, description='Name of the uploaded file'),
    'posted_at': fields.String(description='Timestamp when the post was created'),
    'username': fields.String(description='Username of the post creator'),
    'caption': fields.String(description='Caption for the post')
})

pagination_model = api.model('PaginationMetadata', {
    'current_page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Items per page'),
    'total_items': fields.Integer(description='Total number of items'),
    'total_pages': fields.Integer(description='Total number of pages'),
    'has_next': fields.Boolean(description='Whether there is a next page'),
    'has_prev': fields.Boolean(description='Whether there is a previous page')
})

post_list_model = api.model('PostList', {
    'posts': fields.List(fields.Nested(post_model)),
    'pagination': fields.Nested(pagination_model)
})

error_model = api.model('Error', {
    'error': fields.String(description='Error message')
})

# Namespace for posts
posts_ns = api.namespace('posts', description='Post operations')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def repr(self):
        return self.id

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    ensure_content_log()
    content = []
    with open('db/content-log.log') as f:
        data = f.read().rstrip('\n')
        if data == '':
            content = None
        else:
            for line in data.split('\n'):
                content.append(line.split("???:???"))

    return render_template("home.html", uname=current_user.get_id().lower(), contents=content)

@app.route('/view-post/<filename>', methods=['GET'])
@login_required
def view_post(filename):
    ensure_content_log()
    post_data = None
    with open('db/content-log.log') as f:
        for line in f:
            parts = line.strip().split("???:???")
            if parts[0] == filename:
                post_data = {
                    'filename': parts[0],
                    'posted_at': parts[1],
                    'username': parts[2],
                    'caption': parts[3]
                }
                break
    
    if post_data is None:
        return redirect(url_for('home'))
        
    return render_template("view_post.html", 
                         post=post_data,
                         uname=current_user.get_id().lower())

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        uname = request.form['username'].lower()
        password = request.form['password']
        database = load_database()
        if uname in database and sha512_crypt.verify(password, database[uname]):
            login_user(User(uname))
            return redirect(url_for('home'))
        else:
            error = "Invalid Credentials!"

    return render_template("login.html", error=error)

@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == "POST":
        if ' ' in request.form['username']:
            error = "Username cannot contain spaces!"
        elif request.form['password0'] != request.form['password1']:
            error = "Passwords must Match!"
        else:
            database = load_database()
            if request.form['username'].lower() in database:
                error = "User already Exists!"
            else:
                user_name = request.form['username'].lower()
                password = sha512_crypt.hash(request.form['password0'])
                database[user_name] = password
                save_database(database)
                login_user(User(user_name))
                return redirect(url_for('home'))

    return render_template("signup.html", error=error)

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(userid):
    return User(userid)

@app.route('/chat-history/<path:path>', methods=['GET', 'POST'])
def send_log(path):
    return send_from_directory('db', 'chat-log.log')

@app.route("/post-chat/", methods=["GET", "POST"])
def post_chat():
    if request.form['chat_input'] != '':
        with open('db/chat-log.log', 'r') as f:
            prev_data = f.read()

        with open('db/chat-log.log', 'w') as f:
            f.write("""<strong>{}</strong>: {}\n<br>\n""".format(current_user.get_id().lower(),
                                                                 request.form['chat_input']) + prev_data)

    return render_template("chat-textbox.html")

@app.route('/delete-post/<filename>', methods=['POST'])
@login_required
def delete_post(filename):
    ensure_content_log()
    with open("db/content-log.log", 'r') as f:
        lines = f.readlines()
    updated_lines = []
    for line in lines:
        parts = line.strip().split("???:???")
        if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
            try:
                os.remove(os.path.join("db/contents", filename))
            except:
                pass
        else:
            updated_lines.append(line)
    with open("db/content-log.log", 'w') as f:
        f.writelines(updated_lines)
    return redirect(url_for('home'))

@app.route('/uploader/', methods=['GET', 'POST'])
def upload_file():
    ensure_content_log()
    if request.method == 'POST':
        f = request.files['meme-file']
        file_name = secure_filename(f.filename)
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'ogg'}
        if '.' not in file_name or file_name.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return redirect(url_for('home'))
        f.save("db/contents/" + file_name)
        with open("db/content-log.log", 'r') as f:
            prev_data = f.read()
        with open("db/content-log.log", 'w') as f:
            f.write(file_name + "???:???" + asctime() + "???:???" + current_user.get_id() + "???:???" + request.form["caption-text"] + "\n" + prev_data)
        return redirect(url_for('home'))

@app.route('/edit-caption/<filename>', methods=['GET', 'POST'])
@login_required
def edit_caption(filename):
    ensure_content_log()
    if request.method == 'POST':
        new_caption = request.form['new_caption']
        updated_lines = []
        with open("db/content-log.log", 'r') as f:
            for line in f:
                parts = line.strip().split("???:???")
                if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
                    parts[3] = new_caption
                updated_lines.append("???:???".join(parts))
        with open("db/content-log.log", 'w') as f:
            f.write("\n".join(updated_lines) + "\n")
        return redirect(url_for('home'))
    return render_template("edit_caption.html", filename=filename)

@app.route('/scripts/<path:path>', methods=['GET', 'POST'])
def send_js(path):
    return send_from_directory('scripts', path)

@app.route('/templates/<path:path>', methods=['GET', 'POST'])
def send_html(path):
    return send_from_directory('templates', path)

@app.route('/content/<path:path>', methods=['GET', 'POST'])
def send_content(path):
    return send_from_directory('db/contents', path)

def add_post_links(post_data, base_url):
    """Add HATEOAS links to a post"""
    return {
        **post_data,
        '_links': {
            'self': f"{base_url}/api/posts/{post_data['filename']}",
            'delete': f"{base_url}/api/posts/{post_data['filename']}",
            'update': f"{base_url}/api/posts/{post_data['filename']}",
            'content': f"{base_url}/content/{post_data['filename']}"
        }
    }

# Add custom decorator for API authentication
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return {'error': 'Authentication required'}, 401
        return f(*args, **kwargs)
    return decorated_function

# Add custom decorator for post ownership
def check_post_ownership(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'filename' in kwargs:
            with open('db/content-log.log', 'r') as log:
                for line in log:
                    parts = line.strip().split("???:???")
                    if parts[0] == kwargs['filename']:
                        if parts[2].lower() != current_user.get_id().lower():
                            return {'error': 'Forbidden - You do not own this post'}, 403
                        break
        return f(*args, **kwargs)
    return decorated_function

@posts_ns.route('/')
class PostList(Resource):
    @posts_ns.doc('list_posts',
        params={
            'page': {'description': 'Page number', 'type': 'integer', 'default': 1},
            'per_page': {'description': 'Items per page', 'type': 'integer', 'default': 10}
        }
    )
    @posts_ns.response(200, 'Success', post_list_model)
    @api_login_required
    def get(self):
        """List all posts with pagination"""
        return get_posts()

    @posts_ns.doc('create_post')
    @posts_ns.response(201, 'Post created successfully')
    @posts_ns.response(400, 'Validation Error', error_model)
    @posts_ns.expect(post_model)
    @api_login_required
    def post(self):
        """Create a new post"""
        return create_post()

@posts_ns.route('/<filename>')
@posts_ns.param('filename', 'The post filename')
class Post(Resource):
    @posts_ns.doc('get_post')
    @posts_ns.response(200, 'Success', post_model)
    @posts_ns.response(404, 'Post not found', error_model)
    @api_login_required
    def get(self, filename):
        """Get a specific post"""
        return get_post(filename)

    @posts_ns.doc('delete_post')
    @posts_ns.response(200, 'Post deleted successfully')
    @posts_ns.response(404, 'Post not found', error_model)
    @api_login_required
    @check_post_ownership
    def delete(self, filename):
        """Delete a post"""
        return delete_post_api(filename)

    @posts_ns.doc('update_post')
    @posts_ns.response(200, 'Post updated successfully')
    @posts_ns.response(400, 'Validation Error', error_model)
    @posts_ns.response(404, 'Post not found', error_model)
    @posts_ns.expect(post_model)
    @api_login_required
    @check_post_ownership
    def patch(self, filename):
        """Update a post's caption"""
        return update_post_caption(filename)

@app.route('/api/posts', methods=['GET'])
@api_login_required
def get_posts():
    """
    Get all posts with pagination.
    
    Query Parameters:
        page (int): Page number (default: 1)
        per_page (int): Number of items per page (default: 10)
    
    Returns:
        JSON response containing:
        - List of posts with their details
        - Pagination metadata
        - HATEOAS links for navigation
    """
    ensure_content_log()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    base_url = request.url_root.rstrip('/')
    
    content = []
    with open('db/content-log.log') as f:
        data = f.read().rstrip('\n')
        if data != '':
            for line in data.split('\n'):
                parts = line.split("???:???")
                post_data = {
                    'filename': parts[0],
                    'posted_at': parts[1],
                    'username': parts[2],
                    'caption': parts[3]
                }
                content.append(add_post_links(post_data, base_url))
    
    # Calculate pagination
    total_items = len(content)
    total_pages = (total_items + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    paginated_content = content[start_idx:end_idx]
    
    response_data = {
        'posts': paginated_content,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        },
        '_links': {
            'self': f"{base_url}/api/posts?page={page}&per_page={per_page}",
            'first': f"{base_url}/api/posts?page=1&per_page={per_page}",
            'last': f"{base_url}/api/posts?page={total_pages}&per_page={per_page}",
            'create': f"{base_url}/api/posts"
        }
    }
    
    if page > 1:
        response_data['_links']['prev'] = f"{base_url}/api/posts?page={page-1}&per_page={per_page}"
    if page < total_pages:
        response_data['_links']['next'] = f"{base_url}/api/posts?page={page+1}&per_page={per_page}"
    
    response = make_response(jsonify(response_data))
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/api/posts/<filename>', methods=['GET'])
def get_post(filename):
    """
    Get a specific post by filename
    """
    ensure_content_log()
    post_data = None
    with open('db/content-log.log', 'r') as f:
        for line in f:
            parts = line.strip().split("???:???")
            if parts[0] == filename:
                post_data = {
                    'filename': parts[0],
                    'posted_at': parts[1],
                    'username': parts[2],
                    'caption': parts[3]
                }
                break
    
    if post_data is None:
        return jsonify({'error': 'Post not found'}), 404

    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
        
    post_data = add_post_links(post_data, request.base_url)
    return jsonify(post_data)

@app.route('/api/posts', methods=['POST'])
@api_login_required
def create_post():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    caption = request.form.get('caption', '')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    filename = secure_filename(file.filename)
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'ogg'}
    
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'error': 'Invalid file type'}), 400
        
    ensure_content_log()
    file.save(os.path.join("db/contents", filename))
    
    with open("db/content-log.log", 'r') as f:
        prev_data = f.read()
    with open("db/content-log.log", 'w') as f:
        f.write(filename + "???:???" + asctime() + "???:???" + current_user.get_id() + "???:???" + caption + "\n" + prev_data)
    
    return jsonify({
        'message': 'Post created successfully',
        'filename': filename,
        'posted_at': asctime(),
        'username': current_user.get_id(),
        'caption': caption
    }), 201

@app.route('/api/posts/<filename>', methods=['DELETE'])
@api_login_required
@check_post_ownership
def delete_post_api(filename):
    ensure_content_log()
    deleted = False
    with open("db/content-log.log", 'r') as f:
        lines = f.readlines()
    updated_lines = []
    for line in lines:
        parts = line.strip().split("???:???")
        if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
            try:
                os.remove(os.path.join("db/contents", filename))
                deleted = True
            except:
                pass
        else:
            updated_lines.append(line)
    
    if not deleted:
        return jsonify({'error': 'Post not found or unauthorized'}), 404
        
    with open("db/content-log.log", 'w') as f:
        f.writelines(updated_lines)
    return jsonify({'message': 'Post deleted successfully'}), 200

@app.route('/api/posts/<filename>', methods=['PATCH'])
@api_login_required
@check_post_ownership
def update_post_caption(filename):
    ensure_content_log()
    new_caption = request.json.get('caption')
    if not new_caption:
        return jsonify({'error': 'Caption is required'}), 400
        
    updated = False
    updated_lines = []
    with open("db/content-log.log", 'r') as f:
        for line in f:
            parts = line.strip().split("???:???")
            if parts[0] == filename and parts[2].lower() == current_user.get_id().lower():
                parts[3] = new_caption
                updated = True
            updated_lines.append("???:???".join(parts))
            
    if not updated:
        return jsonify({'error': 'Post not found or unauthorized'}), 404
        
    with open("db/content-log.log", 'w') as f:
        f.write("\n".join(updated_lines) + "\n")
        
    return jsonify({
        'message': 'Caption updated successfully',
        'filename': filename,
        'new_caption': new_caption
    })

if __name__ == "__main__":
    app.run(debug=True, threaded=True, host='0.0.0.0', port=8000)
