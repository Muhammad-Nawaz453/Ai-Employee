# Odoo Community Edition - Docker Setup

This directory contains the Docker Compose configuration for running Odoo Community Edition locally for the AI Employee Gold Tier integration.

## Quick Start

### 1. Start Odoo

```bash
# Start Odoo server
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f odoo
```

### 2. Access Odoo

- **Web Interface:** http://localhost:8069
- **Default Database:** postgres
- **Default Admin Password:** admin

### 3. Initial Setup

1. Open http://localhost:8069 in your browser
2. Create a new database with admin password: `admin`
3. Install required apps:
   - Accounting
   - Invoicing
   - Contacts
   - Sales

### 4. Configure for MCP Integration

After initial setup:

1. Go to Settings → Users & Companies → Users
2. Create or modify a user for API access (e.g., `api_user`)
3. Note the database name, username, and password for MCP configuration

## Services

| Service | Port | Description |
|---------|------|-------------|
| Odoo | 8069 | Web application and API |
| PostgreSQL | 5432 | Database server |
| PgAdmin | 5050 | Database management (optional) |

## Volumes

| Volume | Purpose |
|--------|---------|
| odoo-db-data | PostgreSQL data |
| odoo-data | Odoo filestore (attachments, etc.) |
| pgadmin-data | PgAdmin configuration |

## MCP Integration

The Odoo MCP Server connects to Odoo via XML-RPC API:

- **XML-RPC URL:** http://localhost:8069/xmlrpc/2/
- **Common endpoints:**
  - `/xmlrpc/2/common` - Authentication
  - `/xmlrpc/2/object` - Model operations

## Environment Variables

Create a `.env` file in the parent directory with:

```env
ODOO_URL=http://localhost:8069
ODOO_DB=your_database_name
ODOO_USERNAME=api_user
ODOO_PASSWORD=your_api_password
```

## Stopping Odoo

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

## Backup & Restore

### Backup

```bash
# Backup database
docker-compose exec odoo-db pg_dump -U odoo postgres > backup_$(date +%Y%m%d).sql

# Backup filestore
docker-compose exec odoo tar czf /tmp/odoo-backup.tar.gz /var/lib/odoo
docker cp odoo-server:/tmp/odoo-backup.tar.gz ./
```

### Restore

```bash
# Restore database
docker-compose exec -T odoo-db psql -U odoo postgres < backup_20260101.sql

# Restore filestore
docker cp odoo-backup.tar.gz odoo-server:/tmp/
docker-compose exec odoo tar xzf /tmp/odoo-backup.tar.gz -C /
```

## Troubleshooting

### Odoo won't start

```bash
# Check logs
docker-compose logs odoo

# Restart service
docker-compose restart odoo
```

### Database connection issues

```bash
# Check if PostgreSQL is running
docker-compose ps odoo-db

# Check PostgreSQL logs
docker-compose logs odoo-db
```

### Port conflicts

If port 8069 or 5432 is already in use, modify the ports in `docker-compose.yml`:

```yaml
ports:
  - "8070:8069"  # Change host port to 8070
```

## Production Considerations

For production deployment:

1. Use strong passwords
2. Enable HTTPS with reverse proxy (nginx/traefik)
3. Set up automated backups
4. Configure proper logging
5. Use Odoo Enterprise for advanced features
6. Set up monitoring and alerts

## References

- [Odoo Documentation](https://www.odoo.com/documentation)
- [Odoo External API](https://www.odoo.com/documentation/17.0/developer/reference/external_api.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
