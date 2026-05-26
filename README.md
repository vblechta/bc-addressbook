# bc-addressbook

Company internal web address book with data from external phonebook APIs (BusinessCom, etc.)

Compatible with HTek XML format.

## Features

- **Public Directory**: Browse and search through employee contacts with phone numbers and notes
- **Private Notes & Colors**: Add color-coded personal notes to contacts (admin-only)
- **Admin Panel**: Full management interface for contact customization and settings
- **Homepage Announcement**: Admin-controlled announcement banner on the public page
- **Responsive Design**: Mobile-friendly interface with Bootstrap 5
- **Search**: Real-time search across names, phone numbers, and notes
- **User Authentication**: Secure admin panel with username/password protection

## Installation

### Requirements

- Python 3.8+
- pip
- OpenSSL (for SSL certificate generation)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r abk/requirements.txt
   ```
3. Configure environment variables (see Configuration section)
4. Run the application:
   ```bash
   python abk/start.py
   ```

## Configuration

All configuration is done via environment variables. The app supports both prefixed (`ABK_*`) and legacy variable names.

### Core Application Variables

| Variable | Legacy Name | Default | Description |
|----------|------------|---------|-------------|
| `ABK_SECRET_KEY` | `SECRET_KEY` | `change_me` | Flask session secret key for encrypting session data. **Should be changed to a strong random value in production.** |
| `ABK_ADMIN_USER` | `ADMIN_USER` | `admin` | Username for admin panel authentication. |
| `ABK_ADMIN_PASSWORD` | `ADMIN_PASSWORD` | `admin` | Password for admin panel authentication. **Should be changed in production.** |

### Phonebook Data Variables

| Variable | Legacy Name | Default | Description |
|----------|------------|---------|-------------|
| `BC_PHONEBOOKS` | `PHONEBOOK_URLS` | (empty) | Comma-separated list of XML phonebook URLs to fetch contact data from. Example: `https://api.example.com/phonebook1.xml,https://api.example.com/phonebook2.xml` |
| `ABK_VERIFY_PHONEBOOK_SSL` | (none) | `true` | Whether to verify SSL certificates when fetching phonebooks. Set to `false` to allow self-signed certificates (not recommended for production). Accepts: `true`, `false`, `1`, `0`, `yes`, `no` |

### Server Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ABK_SSL` | `true` | Enable/disable SSL/HTTPS. Set to `true` to run with SSL, `false` for HTTP. Accepts: `true`, `false`, `1`, `0`, `yes`, `no` |
| `ABK_HOSTNAME` | (required if SSL enabled) | Server hostname used for SSL certificate generation. Required if `ABK_SSL=true`. Example: `addressbook.company.com` |
| `ABK_PORT` | `5000` | Port number the Flask application will listen on. |

## Environment Variable Example

```bash
# Flask session encryption
export ABK_SECRET_KEY="your-very-secure-random-key-here"

# Admin credentials
export ABK_ADMIN_USER="admin"
export ABK_ADMIN_PASSWORD="secure_password_123"

# Phonebook data sources
export BC_PHONEBOOKS="https://api.businesscom.cz/phonebooks/main.xml"

# SSL/TLS configuration
export ABK_SSL="true"
export ABK_HOSTNAME="addressbook.example.com"
export ABK_PORT="5000"

# SSL verification (set to false for self-signed certificates)
export ABK_VERIFY_PHONEBOOK_SSL="true"
```

## Running the Application

### Development

```bash
python abk/start.py
```

The server will start on the configured hostname and port. If SSL is enabled, it will generate a self-signed certificate on first run.

### Docker

A Dockerfile and docker-compose.yml are provided for containerized deployment:

```bash
docker-compose up
```

## Database

The application uses SQLite to store:
- **Contact customizations**: Color codes, personal notes, hidden status per contact
- **Global settings**: Homepage announcement text, type, and enabled status

Database file: `phonebook.db` (created automatically on first run)

## API Endpoints

### Public API

- `GET /` - Public directory page with all non-hidden contacts
- `GET /api/search?q=<query>` - Search contacts (public results)

### Admin API

All admin endpoints require authentication.

- `GET /admin` - Admin panel page
- `GET /api/admin/search?q=<query>` - Search contacts (including hidden)
- `POST /api/admin/save_bulk` - Save multiple contact customizations
- `POST /api/admin/reset` - Reset a contact to defaults
- `POST /api/admin/announcement` - Update homepage announcement settings

### Authentication

- `GET /login` - Login page
- `POST /login` - Submit login credentials
- `GET /logout` - Logout

## Project Structure

```
abk/
├── abk.py              # Main Flask application
├── start.py            # Application startup script with SSL handling
├── requirements.txt    # Python dependencies
├── templates/
│   ├── index.html      # Public directory page
│   ├── admin.html      # Admin control panel
│   └── login.html      # Login page
└── phonebook.db        # SQLite database (created on first run)
```
