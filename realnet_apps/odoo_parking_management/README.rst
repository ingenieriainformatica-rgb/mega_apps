.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
    :target: https://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

Parking Management
==================
This module is developed for managing vehicle parking and providing parking 
tickets for any type of customers across multiple sites.

**New Features in v18.0.1.3.0:**

**Multi-Site Management**
- **15 Parking Sites**: Pre-configured sites across 3 cities (Medellín, Cúcuta, Bogotá)
- **Site-based Security**: Operators only see data from their assigned sites
- **Scalable Architecture**: Easy to add new sites and locations

**User Roles & Security**
- **Site Operators**: Restricted access to their assigned parking sites only
- **Parking Administrators**: Full access to all sites and configuration
- **Record Rules**: Automatic filtering ensures data isolation between sites
- **User Assignment**: Flexible assignment of users to multiple sites

**Integrated Accounting**
- **Site-based Analytics**: Revenue tracking per parking site
- **Automatic Distribution**: Invoices include analytic account distribution
- **Standard Payment Flow**: Compatible with Odoo's standard payment registration
- **Financial Reporting**: Site-based income reports without breaking accounting

**Backward Compatibility**
- **Existing Data**: Automatic migration assigns default site to existing records
- **No Data Loss**: All existing parking entries remain functional
- **Account Integration**: Maintains existing invoice and payment workflows

Configuration
=============

**Initial Setup**
1. **Sites**: 15 sites are automatically created (5 per city)
2. **User Assignment**: Assign users to specific sites via Settings → Users
3. **Analytic Accounts**: Optionally configure analytic accounts per site for detailed reporting

**User Configuration**
1. Go to Settings → Users & Companies → Users
2. Edit a user and go to "Parking Sites" tab
3. Select "Allowed Parking Sites" and set "Default Parking Site"
4. Assign appropriate group: "Site Operator" or "Parking Administrator"

**Site Management**
- **Admin Access**: Only Parking Administrators can create/modify sites
- **Operator Access**: Site Operators see only their assigned sites
- **Data Isolation**: All parking data (entries, slots, locations) filtered by site

Security Model
==============

**Access Control**
- **Site Operators**: Can only CRUD records for their assigned sites
- **Parking Admins**: Full access to all sites and configuration
- **Accounting**: Standard accounting users maintain full visibility (no restrictions)

**Record Rules**
- Parking entries, slots, and locations are filtered by user's allowed sites
- No global restrictions on accounting models to preserve standard workflows
- Automatic site assignment on record creation

**Data Validation**
- Users cannot create records for unauthorized sites
- Default site assignment when site_id is not specified
- Validation ensures assigned sites match user permissions

Multi-City Operations
====================

**Medellín Sites**
- El Poblado, Centro, Laureles, Envigado, Sabaneta

**Cúcuta Sites**  
- Centro, Los Caobos, La Atalaya, Terminal, Plaza Bolívar

**Bogotá Sites**
- Zona Rosa, Centro, Chapinero, Suba, Usaquén

**Analytics & Reporting**
- Revenue tracking per site through analytic accounts
- City-level and site-level reporting
- Integration with standard Odoo financial reports

Migration & Upgrade
==================

**From Previous Versions**
1. Automatic site assignment to existing parking entries
2. Default site creation if none exist
3. Backward compatibility maintained for all existing workflows

**Data Migration**
- Existing entries assigned to first available site
- Manual reassignment wizard available for administrators
- No interruption to ongoing operations

Company
-------
* `Realnet <https://www.realnet.com.co/>`__
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

Credits
-------
* Developers:   (V18.0.1.3) Site-based Security Implementation,
                (V18.0.1.1) Customer Type Consolidation,
                (V18) Fathima Mazlin AM,
                (V17) Vishnu kp,
Contact : desarrollo@realnet.com.co

License
-------
* Lesser General Public License, Version 3 (LGPL v3).
(https://www.gnu.org/licenses/lgpl-3.0-standalone.html)

Bug Tracker
-----------
Bugs are tracked on GitHub Issues. In case of trouble, please check there if your issue has already been reported.

Maintainer
==========
.. image:: https://www.realnet.com.co/web/image/website/1/logo/Realnet?unique=4df1d84
   :target: https://www.realnet.com.co

This module is maintained by Realnet.

For support and more information, please visit `Our Website <https://www.realnet.com.co/>`__

Further information
===================
HTML Description: `<static/description/index.html>`__
