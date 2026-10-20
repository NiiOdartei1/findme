# FindMe - E-Commerce Platform

A premium fashion e-commerce platform built with Flask, featuring a complete storefront and admin dashboard for managing products, orders, and inventory.

## Features

### Storefront
- ✅ Product catalog with filters and search
- ✅ Product detail pages with image galleries
- ✅ Shopping cart functionality
- ✅ Customer registration, sign-in, and account profile
- ✅ Paystack checkout in Ghanaian cedis (GHS)
- ✅ Payment-verified orders and order history
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
Install Python 3.12 from [python.org](https://www.python.org/downloads/)

### 2. Install Dependencies
```bash
cd /path/to/FINDME
pip install -r requirements.txt
```

### 3. Set up the database

For a new local database, apply migrations and load the starter catalog and
administrator:

```powershell
$env:SKIP_DATABASE_INIT = "1"
python -m flask --app app db upgrade
python -m flask --app app seed
Remove-Item Env:SKIP_DATABASE_INIT
```

If you already have a local database created by an older version of FindMe,
mark its existing schema as the pre-payment baseline, then apply the payment
migration:

```powershell
$env:SKIP_DATABASE_INIT = "1"
python -m flask --app app db stamp f2e57206e157
python -m flask --app app db upgrade
Remove-Item Env:SKIP_DATABASE_INIT
```

Back up your database before migrating. Do not stamp a brand-new/empty database;
use `db upgrade` directly for that case.

### 4. Run the Application
```bash
python app.py
```

The app will start on `http://127.0.0.1:5000`

Access the admin panel at: `http://127.0.0.1:5000/admin/login` using the
administrator credentials you configured above.

## Project Structure

```
findme/
├── app.py                 # Flask application
├── models.py              # Database models (SQLAlchemy)
├── migrations/            # Database schema history
├── requirements.txt       # Python dependencies
├── findme.db              # Local SQLite database
├── public/static/         # Storefront/admin CSS and JavaScript
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

### Users
- Email and password
- Profile information
- Order history

### Reviews
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
- `/checkout` - Sign-in required; Paystack checkout
- `/account` - Customer profile and order history
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
- `/admin/categories/edit/<id>` - Edit a category
- `/admin/logout` - Sign out (POST)

## Database

The app uses **SQLite** locally and PostgreSQL when deployed. Manage schema
changes with Flask-Migrate (`flask db upgrade`). The `flask seed` command
creates the starter products and categories when the catalog is empty and
creates an initial administrator only when none exists.

Local development uses `admin@findme.shop` / `admin123` unless `ADMIN_EMAIL`
and `ADMIN_PASSWORD` are set. Hosted deployments must configure those
environment variables before running `flask seed`. Existing database records
are not deleted by application startup or migrations; back up and deliberately
clear a database only when you intend to discard that data.

## Deployment to Vercel

This project is configured as a zero-configuration Flask deployment: Vercel
detects the Flask `app` in the root `app.py`, installs Python dependencies from
`requirements.txt`, and serves files from `public/` through its CDN. The
`.python-version` file selects Python 3.12. Vercel's Flask integration is
zero-configuration, so a custom `vercel.json` is not needed.

### 1. Connect the repository

1. Import this GitHub repository in Vercel and select the project root.
2. Keep the detected Flask framework and default build settings; do not add a
   custom build or start command.
3. Add a managed PostgreSQL database (for example, Neon or Supabase) and copy
   its connection string.

SQLite is intended for local development only. Vercel Functions do not provide
persistent local storage for the SQLite database.

### 2. Configure environment variables

Add these variables in the Vercel project's **Settings → Environment Variables**.
Set them for Production and Preview as appropriate:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string from your database provider |
| `SECRET_KEY` | Yes | Random secret used to sign Flask sessions |
| `ADMIN_NAME` | First deployment | Name for the initial admin account |
| `ADMIN_EMAIL` | First deployment | Email for the initial admin account |
| `ADMIN_PASSWORD` | First deployment | Strong password for the initial admin account |
| `PAYSTACK_SECRET_KEY` | Before accepting payments | Paystack test key in Preview; use a live key only in Production |

Generate a session secret locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The initial admin is created only when the database has no admin account.
Keep `ADMIN_PASSWORD` private and do not use the local default credentials in
production. Changing these variables later does not reset an existing admin's
password.

### 3. Deploy and verify

Deploy from the Vercel dashboard or use the Vercel CLI:

```bash
npx vercel
npx vercel --prod
```

After deployment, visit `/` for the storefront and `/admin/login` to sign in.
Use Vercel CLI 48.2.10 or later for local development with `npx vercel dev`,
after configuring the same environment variables in Vercel's local environment
file.

Run migrations and seed the starter catalog and first admin once before the
first deployment. The app does not create tables or records when a Vercel
Function imports it. In PowerShell, set the variables from the Vercel project
and run:

```powershell
$env:VERCEL = "1"
$env:DATABASE_URL = "your-postgresql-connection-string"
$env:SECRET_KEY = "your-generated-session-secret"
$env:ADMIN_NAME = "Store Admin"
$env:ADMIN_EMAIL = "your-admin-email"
$env:ADMIN_PASSWORD = "your-strong-admin-password"
$env:PAYSTACK_SECRET_KEY = "your-paystack-test-secret-key"
python -m flask --app app db upgrade
python -m flask --app app seed
```

This adds the starter products and categories if the catalog is empty, and
creates an initial admin only if none exists. No customer accounts or orders
are seeded. Changing the `ADMIN_*` variables later does not reset an existing
admin's password. Migrations create or update the schema but do not copy data
from a local SQLite database. Use a new, empty PostgreSQL database for a clean
deployment; do not point production at an existing database unless you intend
to retain its records.

In the Paystack dashboard, configure the webhook URL as
`https://your-domain.example/payments/paystack/webhook`. Test the complete flow
with Paystack test credentials and test payment methods before switching the
production environment to a live key. Never commit payment keys or database
credentials to source control.

### Updating Your Store
Push changes to the connected GitHub branch to create a Vercel deployment.
Apply database migrations as a controlled one-off step before serving code
that depends on a new schema.

## Customization

### Change Admin Password
Use the admin account management process for your deployment; do not edit a
production password in source code or rely on the local development defaults.

### Add More Products
Add real products and categories through the admin dashboard after deployment.

### Customize Styling
Edit `public/static/css/styles.css` to customize colors, fonts, and layout.

## Future Enhancements

- [ ] Email notifications
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
