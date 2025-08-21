# Chopsticks & Bowls Django Backend

A comprehensive Django backend for the Chopsticks & Bowls restaurant, featuring QR loyalty system, Paystack payment integration, Google OAuth, and modern admin interface.

## 🚀 Features

### Core Functionality
- **Restaurant Management**: Complete restaurant settings and configuration system
- **Order Management**: Comprehensive order processing with delivery tracking and status management
- **Menu Management**: Flexible menu system with categories, items, and featured selections
- **User Authentication**: JWT-based authentication with custom user model and social login
- **Address Management**: Delivery address handling with Google Maps geocoding integration

### Payment & Loyalty
- **Paystack Integration**: Secure NGN payment processing with webhook support
- **QR Loyalty System**: Complete loyalty card management with QR code generation and scanning
- **Points Management**: Automatic points calculation, redemption, and rewards system
- **Promotional Codes**: Discount and promotion management for orders

### Admin & Management
- **Modern Admin Interface**: Django Unfold for a beautiful, responsive admin experience
- **QR Scanner**: Built-in QR scanner in admin interface for loyalty card scanning
- **Import/Export**: Data management with django-import-export
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation

### Technical Features
- **RESTful API**: Comprehensive API with JWT authentication
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Google OAuth**: Social authentication with Google accounts
- **Image Handling**: Pillow integration for image processing
- **Environment Management**: Secure configuration with python-decouple

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- pip
- virtual environment tool

### Setup Steps

1. **Clone and navigate to project**
   ```bash
   cd chopsticks-website/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for lightweight hosting)
DATABASE_URL=sqlite:///db.sqlite3

# CORS for frontend integration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Paystack Configuration
PAYSTACK_SECRET_KEY=sk_test_...
PAYSTACK_PUBLIC_KEY=pk_test_...
PAYSTACK_WEBHOOK_SECRET=whsec_...

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Paystack Setup

1. Create a Paystack account at [https://paystack.com](https://paystack.com)
2. Get your test/live API keys from the dashboard
3. Configure webhook URL: `https://yourdomain.com/api/payments/webhook/`
4. Update `.env` with your Paystack credentials

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API and OAuth 2.0
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs
6. Update `.env` with your Google OAuth credentials

## 🔐 Authentication & Security

### JWT Authentication
All API endpoints require JWT authentication:
```http
Authorization: Bearer <access_token>
```

### Social Authentication
- Google OAuth integration for seamless login
- Automatic account creation for new social users
- Profile completion workflow

### Security Features
- Environment variables for sensitive data
- JWT token authentication with refresh tokens
- Webhook signature verification (Paystack)
- Input validation and sanitization
- CORS configuration
- HTTPS enforcement in production

## 📱 API Endpoints

### Authentication
- `POST /auth/register/` - User registration
- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `GET /auth/profile/` - User profile
- `POST /auth/social/login/` - Social authentication
- `GET /auth/google/oauth-url/` - Google OAuth URL

### Orders
- `GET /orders/` - List user orders
- `POST /orders/create/` - Create new order
- `GET /orders/{id}/` - Get order details
- `POST /orders/{id}/cancel/` - Cancel order
- `GET /orders/tracking/{orderNumber}/` - Track order
- `POST /orders/apply-promotion/` - Apply promotional code

### Menu
- `GET /menu/categories/` - List menu categories
- `GET /menu/items/` - List menu items
- `GET /menu/featured/` - Get featured items
- `GET /menu/search/` - Search menu items

### Payments
- `POST /payments/initialize/` - Initialize payment
- `GET /payments/verify/{reference}/` - Verify payment status
- `POST /payments/webhook/` - Paystack webhook handler

### Loyalty
- `GET /loyalty/points/` - Get user points balance
- `GET /loyalty/summary/` - Get loyalty summary
- `GET /loyalty/rewards/available/` - Get available rewards
- `POST /loyalty/rewards/redeem/` - Redeem points for rewards

### Core
- `GET /core/restaurant-settings/` - Get restaurant configuration
- `GET /core/info/` - Get restaurant information
- `GET /core/health/` - Health check endpoint

## 🎯 QR Loyalty System

### Features
- **Legacy Support**: Backward compatibility with Google Apps Script URLs
- **New Format**: LOYALTY- prefixed codes for new cards
- **Admin Scanning**: Built-in QR scanner in admin interface
- **Points Management**: Automatic points calculation and redemption
- **Rewards System**: Configurable rewards for point redemption

### Usage
1. Create loyalty cards in admin interface
2. Assign cards to users or keep unassigned
3. Use admin QR scanner to award points for physical visits
4. Track points balance and transaction history
5. Configure rewards and redemption rules

### QR Code Formats
```
Legacy: https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec?customerID=123
New: LOYALTY-A1B2C3D4E5F6
```

## 💳 Payment Integration

### Paystack Flow
1. **Initialize Payment**: Create transaction and get authorization URL
2. **Customer Payment**: Redirect to Paystack checkout
3. **Webhook Processing**: Handle payment confirmation
4. **Order Update**: Update order status and award loyalty points

### Payment Features
- Secure NGN payment processing
- Webhook signature verification
- Automatic order status updates
- Loyalty points awarding
- Payment verification endpoints

## 🎨 Admin Interface

### Django Unfold Features
- Modern, responsive design
- Custom styling and branding
- Optimized for mobile devices
- Enhanced data visualization
- QR code scanning capability

### Key Admin Sections
- **Orders**: Order management with status tracking
- **Loyalty Cards**: QR code generation and user assignment
- **Payments**: Payment tracking and verification
- **Menu**: Menu item and category management
- **Users**: Customer account management
- **Restaurant Settings**: Configuration management

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up static file serving
- [ ] Configure email backend
- [ ] Set up SSL certificates
- [ ] Configure Paystack live keys
- [ ] Set up monitoring and logging
- [ ] Configure Google OAuth production credentials

### Lightweight Hosting
This backend is optimized for free Linux hosting:
- SQLite database for simplicity
- Minimal dependencies
- Efficient static file handling
- Optimized for low-resource environments

### Deployment Commands
```bash
# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser (if needed)
python manage.py createsuperuser

# Check deployment
python manage.py check --deploy
```

## 📚 API Documentation

### Swagger/OpenAPI
- Auto-generated API documentation
- Interactive API testing interface
- Available at `/swagger/` and `/redoc/`
- Generated using drf-yasg

### Testing API
1. Start the development server
2. Navigate to `http://localhost:8000/swagger/`
3. Use the interactive interface to test endpoints
4. View detailed request/response schemas

## 🔧 Development

### Available Commands
```bash
# Run development server
python manage.py runserver

# Run tests
python manage.py test

# Check code quality
python manage.py check

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Load dummy data (if available)
python manage.py loaddata dummy_data.json
```

### Project Structure
```
backend/
├── accounts/          # User authentication and profiles
├── addresses/         # Delivery address management
├── core/             # Restaurant settings and core functionality
├── loyalty/          # Loyalty system and QR codes
├── menu/             # Menu management
├── orders/           # Order processing
├── payments/         # Payment integration
├── promotions/       # Promotional codes
├── utils/            # Utility functions
└── chopsticks_backend/  # Django project settings
```

## 🐛 Troubleshooting

### Common Issues
1. **Database errors**: Run `python manage.py migrate`
2. **Static files not loading**: Run `python manage.py collectstatic`
3. **Environment variables**: Ensure `.env` file is properly configured
4. **CORS issues**: Check `CORS_ALLOWED_ORIGINS` in settings
5. **Payment webhooks**: Verify Paystack webhook URL and secret

### Debug Mode
- Set `DEBUG=True` in `.env` for detailed error messages
- Check `server.log` for application logs
- Use Django debug toolbar for development

## 📞 Support

For issues and questions:
1. Check the API documentation at `/swagger/`
2. Review error logs in `server.log`
3. Test with Paystack test keys first
4. Ensure all environment variables are set
5. Check Django admin interface for data integrity

## 📄 License

This project is proprietary software for Chopsticks & Bowls restaurant.

---

**Built with ❤️ using Django, Django REST Framework, and modern web technologies**
