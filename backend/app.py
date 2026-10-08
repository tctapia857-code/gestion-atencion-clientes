import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory


def create_app(database=None):
    app = Flask(__name__)
    db_path = database or os.environ.get('DATABASE_PATH', str(Path(__file__).parent / 'instance' / 'atencion.sqlite3'))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect():
        db = sqlite3.connect(db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    with connect() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','serving','done')),
                desk_id INTEGER CHECK(desk_id BETWEEN 1 AND 4),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                called_at TEXT,
                completed_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_per_desk ON tickets(desk_id) WHERE status='serving';
        ''')

    def fail(message, code):
        return jsonify(error=message), code

    @app.get('/api/state')
    def state():
        with connect() as db:
            db.execute('BEGIN')
            waiting = [dict(r) for r in db.execute("SELECT * FROM tickets WHERE status='waiting' ORDER BY id")]
            active = {r['desk_id']: dict(r) for r in db.execute("SELECT * FROM tickets WHERE status='serving'")}
            done = db.execute("SELECT COUNT(*) FROM tickets WHERE status='done'").fetchone()[0]
            recent = [dict(r) for r in db.execute("SELECT * FROM tickets WHERE status='done' ORDER BY completed_at DESC, id DESC LIMIT 8")]
        return jsonify(waiting=waiting, desks=[{'id': i, 'ticket': active.get(i)} for i in range(1, 5)], completed=done, recent=recent)

    @app.post('/api/tickets')
    def new_ticket():
        body = request.get_json(silent=True)
        name = body.get('name') if isinstance(body, dict) else None
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            return fail('Escribe un nombre de entre 1 y 80 caracteres.', 400)
        with connect() as db:
            cursor = db.execute('INSERT INTO tickets(name) VALUES (?)', (name.strip(),))
            ticket = dict(db.execute('SELECT * FROM tickets WHERE id=?', (cursor.lastrowid,)).fetchone())
        return jsonify(ticket), 201

    @app.post('/api/desks/<int:desk_id>/call')
    def call(desk_id):
        if desk_id not in range(1, 5):
            return fail('La mesa no existe.', 404)
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM tickets WHERE desk_id=? AND status='serving'", (desk_id,)).fetchone():
                return fail('Finaliza la atención actual antes de llamar otro turno.', 409)
            ticket = db.execute("SELECT id FROM tickets WHERE status='waiting' ORDER BY id LIMIT 1").fetchone()
            if not ticket:
                return fail('No hay clientes en espera.', 409)
            db.execute("UPDATE tickets SET status='serving', desk_id=?, called_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (desk_id, ticket['id']))
        return jsonify(message='Turno llamado.', ticket_id=ticket['id'])

    @app.post('/api/desks/<int:desk_id>/complete')
    def complete(desk_id):
        if desk_id not in range(1, 5):
            return fail('La mesa no existe.', 404)
        body = request.get_json(silent=True)
        ticket_id = body.get('ticket_id') if isinstance(body, dict) else None
        if type(ticket_id) is not int:
            return fail('Indica el turno que deseas finalizar.', 400)
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            result = db.execute("UPDATE tickets SET status='done', completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE desk_id=? AND id=? AND status='serving'", (desk_id, ticket_id))
            if result.rowcount == 0:
                return fail('El turno cambió. Actualiza la pantalla e inténtalo de nuevo.', 409)
        return jsonify(message='Atención finalizada. Mesa disponible.')

    @app.get('/')
    @app.get('/<path:filename>')
    def frontend(filename='index.html'):
        if filename == 'api' or filename.startswith('api/'):
            return fail('Ruta no encontrada.', 404)
        dist = Path(__file__).parent.parent / 'frontend' / 'dist' / 'frontend' / 'browser'
        if not (dist / 'index.html').exists():
            return fail('Compila el frontend con npm run build o usa el servidor Angular.', 503)
        if (dist / filename).is_file():
            return send_from_directory(dist, filename)
        return send_from_directory(dist, 'index.html')

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000)
