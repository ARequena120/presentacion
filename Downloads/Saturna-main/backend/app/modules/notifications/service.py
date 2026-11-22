from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.text import title_name
from app.db.session import SessionLocal
from app.models import Notification, Package, Tenant
from app.modules.notifications import whatsapp
from app.modules.packages import service as pkgs
from app.modules.tenants import service as tenants


def send_arrival(db: Session, pkg: Package, tenant: Tenant, user_id: int | None = None) -> Notification:
    """Envía el aviso de llegada respetando el límite mensual del plan."""
    note = Notification(tenant_id=tenant.id, package_id=pkg.id, kind="aviso_llegada", status="queued")
    db.add(note)
    s = get_settings()
    if whatsapp.is_mock():
        note.status = "simulated"
        note.meta_message_id = None
        note.detail = "Sin credenciales de WhatsApp; envío simulado"
        pkgs.add_event(db, pkg.id, "AVISO_SIMULADO", note.detail, user_id)
        db.commit()
        return note
    if tenants.limit_reached(db, tenant, "notifications"):
        note.status, note.detail = "failed", "limite_plan"
        db.commit()
        return note
    res = whatsapp.send_template(
        pkg.buyer_phone,
        s.whatsapp_template_arrival,
        [title_name(pkg.buyer_name) or "Cliente", tenant.name, pkg.code, pkg.custody_deadline.strftime("%d/%m/%Y")],
    )
    real_sent = res.ok and bool(res.message_id) and not res.message_id.startswith("mock-")
    note.status = "sent" if real_sent else "failed"
    note.meta_message_id = res.message_id if real_sent else None
    note.detail = res.detail
    if real_sent:
        tenants.increment(db, tenant.id, "notifications")
        if pkg.state == "REGISTRADO":
            pkgs.change_state(db, pkg, "NOTIFICADO", user_id, "Aviso enviado por WhatsApp")
    else:
        pkgs.add_event(db, pkg.id, "AVISO_FALLIDO", res.detail, user_id)
    db.commit()
    return note


def send_arrival_task(package_id: int) -> None:
    """Tarea en segundo plano (BackgroundTasks). Para producción pesada: ARQ + Redis."""
    with SessionLocal() as db:
        pkg = db.get(Package, package_id)
        if pkg is None:
            return
        tenant = db.get(Tenant, pkg.tenant_id)
        send_arrival(db, pkg, tenant)
