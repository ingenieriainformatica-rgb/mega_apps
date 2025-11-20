{
  'name': 'Mega - Validate Resolution Dian',
  'summary': 'Show alert Validate Resolution Dian.',
  'version': '1.0',
  'author': 'Jorge Alberto Quiroz Sierra',
  "website": "https://mega.realnet.com.co/",
  "sequence": -112,
  "category": "MegaTecnicentro/ValidateDian",
  'depends': ['account'],
  'data': [
      'security/alert_dian_security.xml',
      'views/account_journal_views.xml',
      'data/alert_dian_cron.xml',
  ],
  "application": True,
  "installable": True,
  "license": "LGPL-3",
}
