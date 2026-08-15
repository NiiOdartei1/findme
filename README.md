# FindMe - E-Commerce Platform

A premium fashion e-commerce platform built with Flask, featuring a complete storefront and admin dashboard for managing products, orders, and inventory.

## Features

### Storefront
- ✅ Product catalog with filters and search
- ✅ Product detail pages with image galleries
- ✅ Shopping cart functionality
- ✅ Checkout flow
- ✅ User account dashboard
- ✅ Order history
- ✅ Premium, minimalist design

### Admin Dashboard
- ✅ Product management (Add, edit, delete products)
- ✅ Category management
- ✅ Order management and tracking
- ✅ Inventory management
- ✅ Dashboard with analytics
- ✅ Admin authentication

## Installation

### 1. Install Python
Download and install Python 3.8+ from [python.org](https://www.python.org/downloads/)

### 2. Install Dependencies
```bash
cd /path/to/FINDME
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```

The app will start on `http://127.0.0.1:5000`

## Default Admin Credentials

**Email:** `admin@findme.shop`  
**Password:** `admin123`

Access the admin panel at: `http://127.0.0.1:5000/admin`

## Project Structure

```
findme/
├── app.py                 # Flask application
├── models.py              # Database models (SQLAlchemy)
├── requirements.txt       # Python dependencies
├── findme.db              # SQLite database (auto-created)
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── shop.html          # Product catalog
│   ├── product.html       # Product detail
│   ├── cart.html          # Shopping cart
│   ├── checkout.html      # Checkout page
│   ├── account.html       # User account
│   ├── order-success.html # Order confirmation
│   ├── about.html         # About page
│   ├── contact.html       # Contact & FAQ
│   ├── login.html         # Login/register
│   └── admin/             # Admin templates
│       ├── login.html
│       ├── dashboard.html
│       ├── products.html
│       ├── add_product.html
│       ├── edit_product.html
│       ├── categories.html
│       ├── add_category.html
│       ├── orders.html
│       └── order_detail.html
├── static/
│   ├── css/
│   │   └── styles.css     # Main stylesheet
│   └── js/
│       └── main.js        # JavaScript functionality
```

## Database Models

### Products
- Name, description, price, images
- Categories, colors, sizes
- Stock tracking, featured status
- Ratings and review counts

### Categories
- Name and description
- Associated products

### Orders
- Order number and status
- Customer info and address
- Line items
- Order total and shipping

### Admin Users
- Email and password (hashed)
- Admin access control

### Users (For future customer accounts)
- Email and password
- Profile information
- Order history

### Reviews (For future implementation)
- Product ratings
- Customer comments

## Admin Features

### Dashboard
- View total products, orders, and revenue
- See recent orders at a glance
- Quick actions for common tasks

### Products
- **List all products** - View inventory with filters
- **Add products** - Create new products with images, prices, stock
- **Edit products** - Update product information
- **Delete products** - Remove items from catalog
- **Categories** - Organize products by category

### Orders
- **View all orders** - See orders with status tracking
- **Order details** - View items, customer info, totals
- **Update status** - Mark orders as Pending, Processing, Shipped, or Delivered

### Categories
- **Create categories** - Add new product categories
- **Manage categories** - Organize your product catalog

## How to Add a Product

1. Go to `/admin/products/add`
2. Fill in:
   - Product name
   - Description
   - Category
   - Price & original price
   - Image URL
   - Available colors (comma-separated)
   - Available sizes (comma-separated)
   - Stock quantity
   - Rating
   - Featured status (optional)
3. Click "Create product"
4. Product appears on the storefront immediately

## How to Manage Orders

1. Go to `/admin/orders`
2. See all orders with status and date
3. Click "View" on any order to see details
4. Update the status from the dropdown
5. Click "Update status" to save changes

## Storefront Routes

- `/` - Home page
- `/shop` - Product catalog
- `/product/<id>` - Product detail
- `/cart` - Shopping cart
- `/checkout` - Checkout flow
- `/account` - User account (demo)
- `/about` - About page
- `/contact` - Contact & FAQ
- `/login` - Login page
- `/register` - Register page

## Admin Routes

- `/admin/login` - Admin login
- `/admin` - Admin dashboard
- `/admin/products` - Product management
- `/admin/products/add` - Add product
- `/admin/products/edit/<id>` - Edit product
- `/admin/orders` - Order management
- `/admin/categories` - Category management
- `/admin/logout` - Logout

## Database

The app uses **SQLite** for data storage. The database file (`findme.db`) is created automatically on first run.

### Reset Database
To reset the database and start fresh:
```bash
rm findme.db
python app.py
```

This will recreate the database with initial seed data.

## Deployment to Railway

FindMe is optimized for deployment on Railway with PostgreSQL. Follow these steps:

### Prerequisites
- A Railway account (https://railway.app)
- GitHub repository with the FindMe code

### 1. Create a Railway Project
1. Log in to Railway and create a new project
2. Connect your GitHub repository
3. Select the branch to deploy

### 2. Add PostgreSQL Plugin
1. In your Railway project, click "Add Plugin"
2. Select "PostgreSQL"
3. Railway will automatically create a `DATABASE_URL` environment variable

### 3. Set Environment Variables
In your Railway project settings, add:
- **`SECRET_KEY`**: A random string for Flask session security
  - Generate one: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### 4. Deploy
The app uses a `Procfile` to tell Railway how to start:
```
web: gunicorn app:app
```

Railway will automatically:
- Install dependencies from `requirements.txt`
- Initialize the database (via `init_db()` in `app.py`)
- Start the Flask app with gunicorn

### 5. Access Your Store
Once deployed, Railway provides a public URL like:
```
https://findme-production.up.railway.app
```

- Storefront: `https://your-url/`
- Admin panel: `https://your-url/admin`
- Admin login: `admin@findme.shop` / `admin123`

### Database Configuration
The app automatically detects the environment:
- **Local development**: Uses SQLite (`findme.db`)
- **Railway (production)**: Uses PostgreSQL via `DATABASE_URL`

No code changes needed—the app handles both seamlessly.

### Environment Variables on Railway
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` (auto-set by Railway) |
| `SECRET_KEY` | Flask secret key | Any random string |
| `PORT` | Server port | `5000` (auto-set by Railway) |

### Monitoring & Logs
In the Railway dashboard, you can:
- View real-time logs
- Monitor CPU/memory usage
- Restart the app if needed
- View recent deployments

### Updating Your Store
To deploy updates:
1. Push changes to your connected GitHub branch
2. Railway automatically redeploys
3. Database migrations (if any) run automatically

## Customization

### Change Admin Password
1. Modify `models.py` - Admin model initialization in `init_db()` function
2. Update the default admin password in `app.py`

### Add More Products
Use the admin dashboard to add products, or modify the seed data in `app.py` before first run.

### Customize Styling
Edit `static/css/styles.css` to customize colors, fonts, and layout.

## Future Enhancements

- [ ] User authentication (customer login/register)
- [ ] Payment processing (Stripe integration)
- [ ] Email notifications
- [ ] Product reviews and ratings
- [ ] Wishlist functionality
- [ ] Search and advanced filtering
- [ ] Analytics and reporting
- [ ] Image upload (instead of URLs)
- [ ] Multi-currency support
- [ ] Inventory alerts

## Troubleshooting

### Database Lock Error
If you get a database lock error, make sure only one instance of the app is running.

### Port Already in Use
If port 5000 is in use, modify the port in `app.py`:
```python
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)  # Change port here
```

### Missing Dependencies
Reinstall requirements:
```bash
pip install --upgrade -r requirements.txt
```

## Support

For issues or questions about the codebase, check:
- Product templates in `templates/admin/`
- Database models in `models.py`
- Routes in `app.py`

---

**FindMe** - A premium e-commerce platform for curated fashion.
