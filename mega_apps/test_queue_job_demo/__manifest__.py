{
    "name": "Test Queue Job Demo",
    "summary": "Local demo module to test delayed queue_job execution",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "author": "Mega",
    "depends": ["base", "queue_job"],
    "data": [
        "security/ir.model.access.csv",
        "data/queue_job_data.xml",
        "views/test_queue_job_demo_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
