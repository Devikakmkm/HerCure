# Hercure – Women's Health & Wellness Platform
Demo- https://drive.google.com/file/d/1fJOLr3Vf50YrsIrxw6ljKXgam3XGjrk4/view?usp=drive_link

## 🚀 Features

### Health Tracking
- **Menstrual Cycle Tracking**: Log and predict menstrual cycles with precision
- **Symptom Journal**: Record and analyze symptoms, moods, and patterns
- **Health Analytics**: Visualize your health data with interactive charts

### E-Commerce
- **Product Catalog**: Browse health and wellness products
- **Shopping Cart**: Add, update, and remove items
- **Secure Checkout**: Process payments using Stripe

## 🛠️ Tech Stack

### Frontend
- **HTML5** - Structure and semantics
- **CSS3/Tailwind CSS** - Styling and responsive design
- **JavaScript** - Client-side interactivity
- **jQuery** - DOM manipulation and event handling
- **Chart.js** - Data visualization
- **Alpine.js** - Minimal framework for JavaScript behavior

### Backend
- **Python 3.9+** - Core programming language
- **Flask 2.3.3** - Web framework
- **Flask-RESTful** - REST API support
- **Flask-CORS** - Cross-origin resource sharing
- **Flask-Login** - Session management
- **Flask-JWT-Extended** - JWT authentication
- **Flask-Bcrypt** - Password hashing

### Database
- **MongoDB 5.0+** - NoSQL database
- **PyMongo** - MongoDB driver for Python
- **Flask-PyMongo** - Flask integration with MongoDB

### APIs & Services
- **Stripe API** - Payment processing
- **Google Maps API** - Location services
- **Google OAuth** - Social authentication
- **GROQ API** - Health data integration

### AI/ML
- **scikit-learn** - Machine learning algorithms
- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computing
- **transformers** - Natural language processing
- **torch** - Deep learning framework

### Development Tools
- **Git** - Version control
- **Pip** - Package management
- **pytest** - Testing framework
- **black** - Code formatter
- **flake8** - Code linter
- **gunicorn** - Production WSGI server

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- MongoDB 5.0+
- Stripe account (for payments)
- Google Cloud Platform account (for OAuth and Maps)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/HerCure.git
   cd HerCure
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```env
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   MONGO_URI=mongodb://localhost:27017/hercure
   STRIPE_PUBLIC_KEY=your-stripe-public-key
   STRIPE_SECRET_KEY=your-stripe-secret-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   JWT_SECRET_KEY=your-jwt-secret
   ```

5. **Initialize the database**
   ```bash
   python -c "from app import create_app; app = create_app(); from app.models import init_models; init_models()"
   ```

6. **Run the application**
   ```bash
   # Development
   python run.py
   
   # Production
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

The application will be available at `http://localhost:5000`

## 📂 Project Structure

```
Hercure/
├── app/                    # Application package
│   ├── __init__.py        # Application factory
│   ├── extensions.py      # Flask extensions
│   ├── models/            # Database models
│   ├── routes/            # Application routes
│   ├── static/            # Static files
│   │   ├── css/           # CSS files
│   │   ├── js/            # JavaScript files
│   │   └── img/           # Image assets
│   └── templates/         # Jinja2 templates
│       ├── auth/          # Authentication templates
│       ├── menstrual/     # Menstrual tracking templates
│       └── shop/          # E-commerce templates
├── tests/                 # Test cases
├── .env.example          # Example environment variables
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── run.py               # Application entry point
```

## 🌐 API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Menstrual Tracking
- `GET /api/cycles` - Get cycle history
- `POST /api/cycles` - Log new cycle data
- `GET /api/predictions` - Get cycle predictions

### Shop
- `GET /shop/` - View products
- `GET /api/products` - Get all products (JSON)
- `POST /api/cart` - Add to cart
- `GET /api/orders` - Get order history

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  Made with ❤️ by the Hercure Team
</div>
