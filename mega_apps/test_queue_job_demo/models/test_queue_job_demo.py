import logging
from datetime import timedelta

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class TestQueueJobDemo(models.Model):
    _name = "test.queue.job.demo"
    _description = "Test Queue Job Demo"
    _order = "requested_at desc, id desc"

    name = fields.Char(required=True, default="Demo queue_job 10s")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft",
        required=True,
    )
    requested_at = fields.Datetime(readonly=True)
    eta_at = fields.Datetime(readonly=True)
    executed_at = fields.Datetime(readonly=True)
    result_message = fields.Text(readonly=True)
    job_uuid = fields.Char(readonly=True)

    def action_enqueue_demo_job(self):
        self.ensure_one()
        now = fields.Datetime.now()
        eta = now + timedelta(seconds=10)

        job = self.with_delay(
            eta=eta,
            channel="root.whatsapp_debounce",
            description=_("Test Queue Job Demo: %s") % self.display_name,
        )._execute_demo_job()

        job_uuid = getattr(job, "uuid", False)
        self.write(
            {
                "state": "queued",
                "requested_at": now,
                "eta_at": eta,
                "executed_at": False,
                "result_message": False,
                "job_uuid": job_uuid,
            }
        )

        _logger.info(
            "Test Queue Job Demo enqueued: record_id=%s job_uuid=%s eta=%s",
            self.id,
            job_uuid,
            eta,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Job encolado"),
                "message": _("El job se ejecutara en aproximadamente 10 segundos."),
                "type": "success",
                "sticky": False,
            },
        }

    def _execute_demo_job(self):
        for record in self:
            executed_at = fields.Datetime.now()
            record.write(
                {
                    "state": "done",
                    "executed_at": executed_at,
                    "result_message": "Job ejecutado correctamente por queue_job",
                }
            )
            _logger.info(
                "Test Queue Job Demo executed: record_id=%s job_uuid=%s eta=%s executed_at=%s",
                record.id,
                record.job_uuid,
                record.eta_at,
                executed_at,
            )
        return True
